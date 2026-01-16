"""
ユーザーモデル
統合されたユーザー状態（RelationshipState + AdaptiveProfile + UserProfile）
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .conversation import Episode
from .relationship import (
    DepthLevel,
    PhaseTransition,
    RelationshipPhase,
    ToneLevel,
    TopicAffinity,
)


@dataclass
class ProactiveSettings:
    """
    プロアクティブケア設定
    Bot APIならではの機能 - ユーザーに先にチェックインする設定
    """

    enabled: bool = False
    frequency: str = "weekly"  # "daily", "weekly", "never"
    preferred_time: str | None = None  # "09:00" 形式
    last_outreach: datetime | None = None
    next_scheduled: datetime | None = None

    # チェックイン種類の設定
    absence_check_enabled: bool = True  # 不在時チェックイン
    absence_threshold_days: int = 3
    sentiment_check_enabled: bool = True  # センチメント悪化時チェックイン
    follow_up_enabled: bool = True  # フォローアップチェックイン

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "frequency": self.frequency,
            "preferred_time": self.preferred_time,
            "last_outreach": self.last_outreach.isoformat()
            if self.last_outreach
            else None,
            "next_scheduled": self.next_scheduled.isoformat()
            if self.next_scheduled
            else None,
            "absence_check_enabled": self.absence_check_enabled,
            "absence_threshold_days": self.absence_threshold_days,
            "sentiment_check_enabled": self.sentiment_check_enabled,
            "follow_up_enabled": self.follow_up_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProactiveSettings":
        return cls(
            enabled=data.get("enabled", False),
            frequency=data.get("frequency", "weekly"),
            preferred_time=data.get("preferred_time"),
            last_outreach=datetime.fromisoformat(data["last_outreach"])
            if data.get("last_outreach")
            else None,
            next_scheduled=datetime.fromisoformat(data["next_scheduled"])
            if data.get("next_scheduled")
            else None,
            absence_check_enabled=data.get("absence_check_enabled", True),
            absence_threshold_days=data.get("absence_threshold_days", 3),
            sentiment_check_enabled=data.get("sentiment_check_enabled", True),
            follow_up_enabled=data.get("follow_up_enabled", True),
        )


@dataclass
class UserState:
    """
    統合ユーザー状態
    RelationshipState + AdaptiveProfile + UserProfile + ProactiveSettings を統合

    これが単一の真実の源泉 (Single Source of Truth)
    """

    user_id: str

    # === 関係性フェーズ（RelationshipStateから） ===
    phase: RelationshipPhase = RelationshipPhase.STRANGER
    total_interactions: int = 0
    first_interaction: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)

    # 関係性指標 (0.0-1.0)
    trust_score: float = 0.0  # 信頼度
    openness_score: float = 0.0  # ユーザーの開示度
    rapport_score: float = 0.0  # 親密度

    # フェーズ履歴
    phase_history: list[PhaseTransition] = field(default_factory=list)

    # === 学習された好み（AdaptiveProfileから） ===
    preferred_tone: ToneLevel = ToneLevel.BALANCED
    preferred_depth: DepthLevel = DepthLevel.MEDIUM

    # トピック関心度
    topic_affinities: dict[str, TopicAffinity] = field(default_factory=dict)

    # 感情パターン（過去の感情の統計）
    emotional_patterns: dict[str, int] = field(default_factory=dict)

    # 好み設定 (0.0-1.0)
    likes_questions: float = 0.5  # 質問を好むか
    likes_advice: float = 0.5  # アドバイスを好むか
    likes_empathy: float = 0.7  # 共感を重視するか
    likes_detail: float = 0.5  # 詳細な説明を好むか

    # 学習状態
    confidence_score: float = 0.0  # 学習の確信度 (0.0-1.0)

    # === 明示的プロファイル（UserProfileから） ===
    explicit_profile: str | None = None  # ユーザーが設定した自由形式プロファイル
    display_name: str | None = None

    # === 既知情報 ===
    known_facts: list[str] = field(default_factory=list)  # 「〇〇さんは東京在住」等
    known_topics: list[str] = field(default_factory=list)  # 話したことのあるトピック

    # === エピソード（長期記憶） ===
    episodes: list[Episode] = field(default_factory=list)

    # === プロアクティブケア設定 ===
    proactive: ProactiveSettings = field(default_factory=ProactiveSettings)

    # === メタデータ ===
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_interaction(self) -> None:
        """インタラクションを記録"""
        self.total_interactions += 1
        self.last_interaction = datetime.now()
        self.updated_at = datetime.now()

    def add_episode(self, episode: Episode) -> None:
        """エピソードを追加（最大100件保持）"""
        self.episodes.append(episode)
        if len(self.episodes) > 100:
            # 重要度の低いものを優先的に削除
            self.episodes.sort(key=lambda e: e.importance_score, reverse=True)
            self.episodes = self.episodes[:100]
            self.episodes.sort(key=lambda e: e.created_at)

    def add_known_fact(self, fact: str) -> None:
        """既知の事実を追加"""
        if fact not in self.known_facts:
            self.known_facts.append(fact)

    def add_known_topic(self, topic: str) -> None:
        """話したトピックを追加"""
        if topic not in self.known_topics:
            self.known_topics.append(topic)

    def update_topic_affinity(self, topic: str, score_delta: float = 0.1) -> None:
        """トピック関心度を更新"""
        if topic not in self.topic_affinities:
            self.topic_affinities[topic] = TopicAffinity(topic=topic)

        affinity = self.topic_affinities[topic]
        affinity.mention_count += 1
        affinity.last_mentioned = datetime.now()
        affinity.affinity_score = min(1.0, affinity.affinity_score + score_delta)

    def update_emotional_pattern(self, emotion: str) -> None:
        """感情パターンを更新"""
        self.emotional_patterns[emotion] = self.emotional_patterns.get(emotion, 0) + 1

    def get_top_topics(self, n: int = 5) -> list[TopicAffinity]:
        """上位トピックを取得"""
        sorted_topics = sorted(
            self.topic_affinities.values(),
            key=lambda t: t.affinity_score,
            reverse=True,
        )
        return sorted_topics[:n]

    def get_recent_episodes(self, n: int = 5) -> list[Episode]:
        """最近のエピソードを取得"""
        sorted_episodes = sorted(
            self.episodes,
            key=lambda e: e.created_at,
            reverse=True,
        )
        return sorted_episodes[:n]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            # 関係性
            "phase": self.phase.value,
            "total_interactions": self.total_interactions,
            "first_interaction": self.first_interaction.isoformat(),
            "last_interaction": self.last_interaction.isoformat(),
            "trust_score": self.trust_score,
            "openness_score": self.openness_score,
            "rapport_score": self.rapport_score,
            "phase_history": [p.to_dict() for p in self.phase_history],
            # 学習された好み
            "preferred_tone": self.preferred_tone.value,
            "preferred_depth": self.preferred_depth.value,
            "topic_affinities": {
                k: v.to_dict() for k, v in self.topic_affinities.items()
            },
            "emotional_patterns": self.emotional_patterns,
            "likes_questions": self.likes_questions,
            "likes_advice": self.likes_advice,
            "likes_empathy": self.likes_empathy,
            "likes_detail": self.likes_detail,
            "confidence_score": self.confidence_score,
            # 明示的プロファイル
            "explicit_profile": self.explicit_profile,
            "display_name": self.display_name,
            # 既知情報
            "known_facts": self.known_facts,
            "known_topics": self.known_topics,
            # エピソード
            "episodes": [e.to_dict() for e in self.episodes],
            # プロアクティブ
            "proactive": self.proactive.to_dict(),
            # メタデータ
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserState":
        return cls(
            user_id=data["user_id"],
            # 関係性
            phase=RelationshipPhase(data.get("phase", "stranger")),
            total_interactions=data.get("total_interactions", 0),
            first_interaction=datetime.fromisoformat(
                data.get("first_interaction", datetime.now().isoformat())
            ),
            last_interaction=datetime.fromisoformat(
                data.get("last_interaction", datetime.now().isoformat())
            ),
            trust_score=data.get("trust_score", 0.0),
            openness_score=data.get("openness_score", 0.0),
            rapport_score=data.get("rapport_score", 0.0),
            phase_history=[
                PhaseTransition.from_dict(p) for p in data.get("phase_history", [])
            ],
            # 学習された好み
            preferred_tone=ToneLevel(data.get("preferred_tone", "balanced")),
            preferred_depth=DepthLevel(data.get("preferred_depth", "medium")),
            topic_affinities={
                k: TopicAffinity.from_dict(v)
                for k, v in data.get("topic_affinities", {}).items()
            },
            emotional_patterns=data.get("emotional_patterns", {}),
            likes_questions=data.get("likes_questions", 0.5),
            likes_advice=data.get("likes_advice", 0.5),
            likes_empathy=data.get("likes_empathy", 0.7),
            likes_detail=data.get("likes_detail", 0.5),
            confidence_score=data.get("confidence_score", 0.0),
            # 明示的プロファイル
            explicit_profile=data.get("explicit_profile"),
            display_name=data.get("display_name"),
            # 既知情報
            known_facts=data.get("known_facts", []),
            known_topics=data.get("known_topics", []),
            # エピソード
            episodes=[Episode.from_dict(e) for e in data.get("episodes", [])],
            # プロアクティブ
            proactive=ProactiveSettings.from_dict(data.get("proactive", {})),
            # メタデータ
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                data.get("updated_at", datetime.now().isoformat())
            ),
        )
