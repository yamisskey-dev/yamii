"""
エピソード記憶マネージャー
重要な会話をエピソードとして記憶・検索
"""

import uuid
from datetime import datetime
from typing import List, Optional, Set

from .models import Episode, EpisodeType


class EpisodeManager:
    """
    エピソード記憶マネージャー

    重要な会話を「エピソード」として長期記憶に保存し、
    必要に応じて検索・参照する。
    """

    # 個人情報開示を示すキーワード
    DISCLOSURE_KEYWORDS = [
        "私は", "実は", "初めて話す", "秘密", "本当は",
        "誰にも言ってない", "打ち明ける", "正直に言うと",
    ]

    # 危機的状況を示すキーワード
    CRISIS_KEYWORDS = [
        "死にたい", "消えたい", "自殺", "生きる意味",
        "限界", "自分を傷つけ", "もう無理",
    ]

    # 洞察・気づきを示すキーワード
    INSIGHT_KEYWORDS = [
        "気づいた", "わかった", "そうか", "なるほど",
        "目から鱗", "ハッとした", "腑に落ちた",
    ]

    def __init__(self):
        pass

    def maybe_create_episode(
        self,
        user_id: str,
        message: str,
        topics: List[str],
        emotion: str,
        emotion_intensity: float,
        is_crisis: bool,
        user_shared_info: List[str],
        known_topics: Set[str],
    ) -> Optional[Episode]:
        """
        重要な会話からエピソードを生成（条件を満たす場合のみ）

        Args:
            user_id: ユーザーID
            message: ユーザーメッセージ
            topics: 検出されたトピック
            emotion: 感情
            emotion_intensity: 感情の強さ (0.0-1.0)
            is_crisis: 危機的状況か
            user_shared_info: ユーザーが共有した個人情報
            known_topics: 既知のトピック

        Returns:
            生成されたエピソード（条件を満たさない場合はNone）
        """
        # 重要度を計算
        importance = self._calculate_importance(
            message=message,
            emotion_intensity=emotion_intensity,
            is_crisis=is_crisis,
            user_shared_info=user_shared_info,
            topics=topics,
            known_topics=known_topics,
        )

        # 重要度が閾値未満ならエピソード化しない
        if importance < 0.4:
            return None

        # エピソードタイプを判定
        episode_type = self._determine_episode_type(
            message=message,
            is_crisis=is_crisis,
            user_shared_info=user_shared_info,
        )

        # サマリーを生成
        summary = self._generate_summary(
            message=message,
            topics=topics,
            emotion=emotion,
            episode_type=episode_type,
        )

        # キーワードを抽出
        keywords = self._extract_keywords(message, topics)

        return Episode(
            id=f"ep_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            created_at=datetime.now(),
            summary=summary,
            user_shared=user_shared_info,
            emotional_context=emotion,
            topics=topics,
            importance_score=importance,
            emotional_intensity=emotion_intensity,
            episode_type=episode_type,
            keywords=keywords,
        )

    def _calculate_importance(
        self,
        message: str,
        emotion_intensity: float,
        is_crisis: bool,
        user_shared_info: List[str],
        topics: List[str],
        known_topics: Set[str],
    ) -> float:
        """エピソードの重要度を計算"""
        score = 0.0

        # 感情の強さ（最大0.3）
        score += emotion_intensity * 0.3

        # 危機的状況は最重要（+0.5）
        if is_crisis:
            score += 0.5

        # 個人情報の開示（+0.2）
        if user_shared_info:
            score += 0.2

        # 開示キーワードの検出（+0.1）
        if any(kw in message for kw in self.DISCLOSURE_KEYWORDS):
            score += 0.1

        # 洞察キーワードの検出（+0.15）
        if any(kw in message for kw in self.INSIGHT_KEYWORDS):
            score += 0.15

        # 初めて話すトピック（1トピックあたり+0.1、最大0.2）
        new_topics = [t for t in topics if t not in known_topics]
        score += min(len(new_topics) * 0.1, 0.2)

        # メッセージの長さ（長いほど重要な可能性、最大0.1）
        if len(message) > 200:
            score += 0.1
        elif len(message) > 100:
            score += 0.05

        return min(1.0, score)

    def _determine_episode_type(
        self,
        message: str,
        is_crisis: bool,
        user_shared_info: List[str],
    ) -> EpisodeType:
        """エピソードタイプを判定"""
        if is_crisis:
            return EpisodeType.CRISIS

        if any(kw in message for kw in self.CRISIS_KEYWORDS):
            return EpisodeType.CRISIS

        if user_shared_info or any(kw in message for kw in self.DISCLOSURE_KEYWORDS):
            return EpisodeType.DISCLOSURE

        if any(kw in message for kw in self.INSIGHT_KEYWORDS):
            return EpisodeType.INSIGHT

        return EpisodeType.GENERAL

    def _generate_summary(
        self,
        message: str,
        topics: List[str],
        emotion: str,
        episode_type: EpisodeType,
    ) -> str:
        """エピソードのサマリーを生成"""
        type_prefix = {
            EpisodeType.CRISIS: "【危機対応】",
            EpisodeType.DISCLOSURE: "【個人情報共有】",
            EpisodeType.INSIGHT: "【気づき】",
            EpisodeType.MILESTONE: "【マイルストーン】",
            EpisodeType.GENERAL: "",
        }

        prefix = type_prefix.get(episode_type, "")

        # トピック情報
        topics_text = f"話題: {', '.join(topics)}" if topics else ""

        # 感情情報
        emotion_text = f"感情: {emotion}"

        # メッセージの要約（最初の100文字）
        msg_summary = message[:100] + "..." if len(message) > 100 else message

        parts = [p for p in [prefix, topics_text, emotion_text, msg_summary] if p]
        return " / ".join(parts)

    def _extract_keywords(
        self, message: str, topics: List[str]
    ) -> List[str]:
        """検索用キーワードを抽出"""
        keywords = list(topics)

        # 重要そうな2文字以上の単語を抽出（簡易版）
        import re
        matches = re.findall(r"[一-龯]{2,}", message)
        for match in matches:
            if match not in keywords and len(keywords) < 15:
                keywords.append(match)

        return keywords

    def search_episodes(
        self,
        episodes: List[Episode],
        query: str,
        limit: int = 5,
    ) -> List[Episode]:
        """
        エピソードを検索

        Args:
            episodes: 検索対象のエピソードリスト
            query: 検索クエリ
            limit: 最大件数

        Returns:
            マッチしたエピソード
        """
        results: List[tuple[Episode, float]] = []
        query_lower = query.lower()

        for episode in episodes:
            score = 0.0

            # トピックマッチ
            for topic in episode.topics:
                if query_lower in topic.lower():
                    score += 3.0

            # キーワードマッチ
            for keyword in episode.keywords:
                if query_lower in keyword.lower():
                    score += 2.0

            # サマリーマッチ
            if query_lower in episode.summary.lower():
                score += 1.0

            # 共有情報マッチ
            for shared in episode.user_shared:
                if query_lower in shared.lower():
                    score += 2.5

            if score > 0:
                # 重要度も考慮
                score *= (0.5 + episode.importance_score * 0.5)
                results.append((episode, score))

        # スコア順にソート
        results.sort(key=lambda x: x[1], reverse=True)

        return [r[0] for r in results[:limit]]

    def get_important_episodes(
        self,
        episodes: List[Episode],
        min_importance: float = 0.6,
        limit: int = 10,
    ) -> List[Episode]:
        """重要なエピソードを取得"""
        filtered = [e for e in episodes if e.importance_score >= min_importance]
        filtered.sort(key=lambda e: e.importance_score, reverse=True)
        return filtered[:limit]

    def get_recent_episodes(
        self,
        episodes: List[Episode],
        limit: int = 5,
    ) -> List[Episode]:
        """最近のエピソードを取得"""
        sorted_eps = sorted(episodes, key=lambda e: e.created_at, reverse=True)
        return sorted_eps[:limit]

    def get_episodes_by_topic(
        self,
        episodes: List[Episode],
        topic: str,
        limit: int = 5,
    ) -> List[Episode]:
        """トピックでエピソードをフィルタ"""
        topic_lower = topic.lower()
        filtered = [
            e for e in episodes
            if any(topic_lower in t.lower() for t in e.topics)
        ]
        filtered.sort(key=lambda e: e.created_at, reverse=True)
        return filtered[:limit]
