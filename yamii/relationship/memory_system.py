"""
関係性記憶システム（統合クラス）
対話を通じて相手に適応・成長し続けるシェイプシフター型AIパートナー
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import (
    RelationshipPhase,
    RelationshipState,
    Episode,
    AdaptiveProfile,
    UserRelationshipData,
)
from .episode_manager import EpisodeManager
from .phase_manager import PhaseManager
from .adaptive_profile import AdaptiveProfileManager
from .prompt_generator import RelationshipPromptGenerator


class RelationshipMemorySystem:
    """
    関係性記憶システム

    対話を通じてユーザーとの関係性を構築・記憶する統合システム。
    - ゼロ設定で開始
    - 対話から自然に学習
    - 関係性フェーズの管理
    - エピソード記憶
    - 適応プロファイル
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "relationship_data.json"
        self.data_dir.mkdir(exist_ok=True)

        # ユーザーデータ
        self._users: Dict[str, UserRelationshipData] = {}

        # 各マネージャー
        self.episode_manager = EpisodeManager()
        self.phase_manager = PhaseManager()
        self.profile_manager = AdaptiveProfileManager()
        self.prompt_generator = RelationshipPromptGenerator()

        # データ読み込み
        self._load_data()

    def _load_data(self) -> None:
        """データを読み込み"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, user_data in data.get("users", {}).items():
                        self._users[user_id] = UserRelationshipData.from_dict(user_data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"関係性データ読み込みエラー: {e}")

    def _save_data(self) -> None:
        """データを保存"""
        data = {
            "users": {uid: u.to_dict() for uid, u in self._users.items()},
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_or_create_user(self, user_id: str) -> UserRelationshipData:
        """ユーザーデータを取得（なければ作成）"""
        if user_id not in self._users:
            self._users[user_id] = UserRelationshipData(
                user_id=user_id,
                state=RelationshipState(user_id=user_id),
                profile=AdaptiveProfile(user_id=user_id),
                episodes=[],
            )
            self._save_data()
        return self._users[user_id]

    def process_interaction(
        self,
        user_id: str,
        message: str,
        topics: List[str],
        emotion: str,
        emotion_intensity: float,
        is_crisis: bool = False,
        user_shared_info: Optional[List[str]] = None,
    ) -> UserRelationshipData:
        """
        対話を処理して関係性を更新

        Args:
            user_id: ユーザーID
            message: ユーザーメッセージ
            topics: 検出されたトピック
            emotion: 感情
            emotion_intensity: 感情の強さ (0-10)
            is_crisis: 危機的状況か
            user_shared_info: ユーザーが共有した個人情報

        Returns:
            更新されたユーザーデータ
        """
        user_data = self.get_or_create_user(user_id)

        # 1. フェーズ更新
        old_phase = user_data.state.phase
        user_data.state = self.phase_manager.update_state(
            state=user_data.state,
            message=message,
            emotion_intensity=emotion_intensity / 10.0,
            has_personal_disclosure=bool(user_shared_info),
        )
        new_phase = user_data.state.phase

        # フェーズ遷移があればログ
        if old_phase != new_phase:
            self._log_phase_transition(user_data.state, old_phase, new_phase)

        # 2. プロファイル更新
        user_data.profile = self.profile_manager.update_from_interaction(
            profile=user_data.profile,
            message=message,
            topics=topics,
            emotion=emotion,
            emotion_intensity=emotion_intensity / 10.0,
        )

        # 3. エピソード生成（重要な会話のみ）
        episode = self.episode_manager.maybe_create_episode(
            user_id=user_id,
            message=message,
            topics=topics,
            emotion=emotion,
            emotion_intensity=emotion_intensity / 10.0,
            is_crisis=is_crisis,
            user_shared_info=user_shared_info or [],
            known_topics=set(user_data.state.known_topics),
        )

        if episode:
            user_data.episodes.append(episode)
            # エピソード数を制限（最新100件）
            if len(user_data.episodes) > 100:
                # 重要度の低いものを優先的に削除
                user_data.episodes.sort(key=lambda e: e.importance_score, reverse=True)
                user_data.episodes = user_data.episodes[:100]
                user_data.episodes.sort(key=lambda e: e.created_at)

        # 4. 既知のトピックを更新
        for topic in topics:
            if topic not in user_data.state.known_topics:
                user_data.state.known_topics.append(topic)

        # 5. 共有された情報を記録
        if user_shared_info:
            for info in user_shared_info:
                if info not in user_data.state.known_facts:
                    user_data.state.known_facts.append(info)

        self._save_data()
        return user_data

    def _log_phase_transition(
        self,
        state: RelationshipState,
        old_phase: RelationshipPhase,
        new_phase: RelationshipPhase,
    ) -> None:
        """フェーズ遷移を記録"""
        from .models import PhaseTransition

        transition = PhaseTransition(
            from_phase=old_phase,
            to_phase=new_phase,
            transitioned_at=datetime.now(),
            interaction_count=state.total_interactions,
            trigger="interaction_milestone",
        )
        state.phase_history.append(transition)

    def generate_system_prompt(self, user_id: str) -> str:
        """
        ユーザーに適応したシステムプロンプトを生成

        Args:
            user_id: ユーザーID

        Returns:
            システムプロンプト
        """
        user_data = self.get_or_create_user(user_id)

        # 関連エピソードを取得（最新5件）
        recent_episodes = sorted(
            user_data.episodes,
            key=lambda e: e.created_at,
            reverse=True,
        )[:5]

        return self.prompt_generator.generate(
            state=user_data.state,
            profile=user_data.profile,
            recent_episodes=recent_episodes,
        )

    def get_relationship_summary(self, user_id: str) -> Dict[str, Any]:
        """関係性のサマリーを取得"""
        user_data = self.get_or_create_user(user_id)

        return {
            "user_id": user_id,
            "phase": user_data.state.phase.value,
            "total_interactions": user_data.state.total_interactions,
            "trust_score": user_data.state.trust_score,
            "days_since_first": (
                datetime.now() - user_data.state.first_interaction
            ).days,
            "episode_count": len(user_data.episodes),
            "known_topics": user_data.state.known_topics[:10],
            "top_topics": self._get_top_topics(user_data.profile, 5),
            "confidence_score": user_data.profile.confidence_score,
        }

    def _get_top_topics(
        self, profile: AdaptiveProfile, n: int
    ) -> List[Dict[str, Any]]:
        """上位トピックを取得"""
        sorted_topics = sorted(
            profile.frequent_topics.values(),
            key=lambda t: t.affinity_score,
            reverse=True,
        )[:n]
        return [{"topic": t.topic, "score": t.affinity_score} for t in sorted_topics]

    def search_episodes(
        self, user_id: str, query: str, limit: int = 5
    ) -> List[Episode]:
        """エピソードを検索"""
        user_data = self.get_or_create_user(user_id)
        return self.episode_manager.search_episodes(
            episodes=user_data.episodes,
            query=query,
            limit=limit,
        )

    def reset_relationship(self, user_id: str) -> bool:
        """関係性をリセット（プライバシー対応）"""
        if user_id in self._users:
            self._users[user_id] = UserRelationshipData(
                user_id=user_id,
                state=RelationshipState(user_id=user_id),
                profile=AdaptiveProfile(user_id=user_id),
                episodes=[],
            )
            self._save_data()
            return True
        return False

    def export_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーデータをエクスポート（GDPR対応）"""
        if user_id not in self._users:
            return None
        return self._users[user_id].to_dict()

    def delete_user_data(self, user_id: str) -> bool:
        """ユーザーデータを削除（GDPR対応）"""
        if user_id in self._users:
            del self._users[user_id]
            self._save_data()
            return True
        return False


# グローバルインスタンス
_relationship_memory: Optional[RelationshipMemorySystem] = None


def get_relationship_memory(data_dir: str = "data") -> RelationshipMemorySystem:
    """グローバルな関係性記憶システムを取得"""
    global _relationship_memory
    if _relationship_memory is None:
        _relationship_memory = RelationshipMemorySystem(data_dir=data_dir)
    return _relationship_memory
