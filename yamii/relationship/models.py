"""
関係性記憶システムのデータモデル
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class RelationshipPhase(Enum):
    """関係性フェーズ"""
    STRANGER = "stranger"           # 初対面 (0-5回)
    ACQUAINTANCE = "acquaintance"   # 顔見知り (6-20回)
    FAMILIAR = "familiar"           # 親しい関係 (21-50回)
    TRUSTED = "trusted"             # 信頼関係 (51回以上)


class EpisodeType(Enum):
    """エピソードタイプ"""
    GENERAL = "general"             # 一般的な会話
    DISCLOSURE = "disclosure"       # 個人情報の開示
    CRISIS = "crisis"               # 危機的状況
    MILESTONE = "milestone"         # 関係性のマイルストーン
    INSIGHT = "insight"             # 気づき・洞察


class ToneLevel(Enum):
    """応答トーン"""
    WARM = "warm"                   # 温かみのある
    PROFESSIONAL = "professional"   # 専門的
    CASUAL = "casual"               # カジュアル
    BALANCED = "balanced"           # バランス型


class DepthLevel(Enum):
    """応答の深さ"""
    SHALLOW = "shallow"             # 浅い（短い応答）
    MEDIUM = "medium"               # 中程度
    DEEP = "deep"                   # 深い（詳細な応答）


@dataclass
class PhaseTransition:
    """フェーズ遷移記録"""
    from_phase: RelationshipPhase
    to_phase: RelationshipPhase
    transitioned_at: datetime
    interaction_count: int
    trigger: str  # 遷移のきっかけ

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_phase": self.from_phase.value,
            "to_phase": self.to_phase.value,
            "transitioned_at": self.transitioned_at.isoformat(),
            "interaction_count": self.interaction_count,
            "trigger": self.trigger,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhaseTransition":
        return cls(
            from_phase=RelationshipPhase(data["from_phase"]),
            to_phase=RelationshipPhase(data["to_phase"]),
            transitioned_at=datetime.fromisoformat(data["transitioned_at"]),
            interaction_count=data["interaction_count"],
            trigger=data["trigger"],
        )


@dataclass
class RelationshipState:
    """関係性状態"""
    user_id: str
    phase: RelationshipPhase = RelationshipPhase.STRANGER

    # 基本統計
    total_interactions: int = 0
    first_interaction: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)

    # 関係性指標 (0.0-1.0)
    trust_score: float = 0.0          # 信頼度
    openness_score: float = 0.0       # ユーザーの開示度
    rapport_score: float = 0.0        # 親密度

    # 成長履歴
    phase_history: List[PhaseTransition] = field(default_factory=list)

    # 知っている情報
    known_facts: List[str] = field(default_factory=list)  # 「〇〇さんは東京在住」等
    known_topics: List[str] = field(default_factory=list)  # 話したことのあるトピック

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "phase": self.phase.value,
            "total_interactions": self.total_interactions,
            "first_interaction": self.first_interaction.isoformat(),
            "last_interaction": self.last_interaction.isoformat(),
            "trust_score": self.trust_score,
            "openness_score": self.openness_score,
            "rapport_score": self.rapport_score,
            "phase_history": [p.to_dict() for p in self.phase_history],
            "known_facts": self.known_facts,
            "known_topics": self.known_topics,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipState":
        return cls(
            user_id=data["user_id"],
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
                PhaseTransition.from_dict(p)
                for p in data.get("phase_history", [])
            ],
            known_facts=data.get("known_facts", []),
            known_topics=data.get("known_topics", []),
        )


@dataclass
class Episode:
    """エピソード記憶"""
    id: str
    user_id: str
    created_at: datetime

    # コンテンツ
    summary: str                              # 会話の要約
    user_shared: List[str] = field(default_factory=list)  # ユーザーが共有した情報
    emotional_context: str = ""               # 感情的文脈
    topics: List[str] = field(default_factory=list)

    # メタデータ
    importance_score: float = 0.5             # 重要度 (0.0-1.0)
    emotional_intensity: float = 0.5          # 感情の強さ (0.0-1.0)
    episode_type: EpisodeType = EpisodeType.GENERAL

    # 検索用
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "summary": self.summary,
            "user_shared": self.user_shared,
            "emotional_context": self.emotional_context,
            "topics": self.topics,
            "importance_score": self.importance_score,
            "emotional_intensity": self.emotional_intensity,
            "episode_type": self.episode_type.value,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            summary=data.get("summary", ""),
            user_shared=data.get("user_shared", []),
            emotional_context=data.get("emotional_context", ""),
            topics=data.get("topics", []),
            importance_score=data.get("importance_score", 0.5),
            emotional_intensity=data.get("emotional_intensity", 0.5),
            episode_type=EpisodeType(data.get("episode_type", "general")),
            keywords=data.get("keywords", []),
        )


@dataclass
class TopicAffinity:
    """トピック関心度"""
    topic: str
    affinity_score: float = 0.0       # 関心度 (0.0-1.0)
    mention_count: int = 0
    last_mentioned: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "affinity_score": self.affinity_score,
            "mention_count": self.mention_count,
            "last_mentioned": self.last_mentioned.isoformat() if self.last_mentioned else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TopicAffinity":
        return cls(
            topic=data["topic"],
            affinity_score=data.get("affinity_score", 0.0),
            mention_count=data.get("mention_count", 0),
            last_mentioned=datetime.fromisoformat(data["last_mentioned"])
            if data.get("last_mentioned")
            else None,
        )


@dataclass
class AdaptiveProfile:
    """適応プロファイル"""
    user_id: str

    # コミュニケーションスタイル
    preferred_tone: ToneLevel = ToneLevel.BALANCED
    preferred_depth: DepthLevel = DepthLevel.MEDIUM

    # 学習されたパターン
    frequent_topics: Dict[str, TopicAffinity] = field(default_factory=dict)
    emotional_patterns: Dict[str, int] = field(default_factory=dict)

    # 好み (0.0-1.0)
    likes_questions: float = 0.5      # 質問を好むか
    likes_advice: float = 0.5         # アドバイスを好むか
    likes_empathy: float = 0.7        # 共感を重視するか
    likes_detail: float = 0.5         # 詳細な説明を好むか

    # 学習状態
    confidence_score: float = 0.0     # 学習の確信度 (0.0-1.0)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "preferred_tone": self.preferred_tone.value,
            "preferred_depth": self.preferred_depth.value,
            "frequent_topics": {
                k: v.to_dict() for k, v in self.frequent_topics.items()
            },
            "emotional_patterns": self.emotional_patterns,
            "likes_questions": self.likes_questions,
            "likes_advice": self.likes_advice,
            "likes_empathy": self.likes_empathy,
            "likes_detail": self.likes_detail,
            "confidence_score": self.confidence_score,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdaptiveProfile":
        return cls(
            user_id=data["user_id"],
            preferred_tone=ToneLevel(data.get("preferred_tone", "balanced")),
            preferred_depth=DepthLevel(data.get("preferred_depth", "medium")),
            frequent_topics={
                k: TopicAffinity.from_dict(v)
                for k, v in data.get("frequent_topics", {}).items()
            },
            emotional_patterns=data.get("emotional_patterns", {}),
            likes_questions=data.get("likes_questions", 0.5),
            likes_advice=data.get("likes_advice", 0.5),
            likes_empathy=data.get("likes_empathy", 0.7),
            likes_detail=data.get("likes_detail", 0.5),
            confidence_score=data.get("confidence_score", 0.0),
            last_updated=datetime.fromisoformat(
                data.get("last_updated", datetime.now().isoformat())
            ),
        )


@dataclass
class UserRelationshipData:
    """ユーザーの関係性データ（全データの集約）"""
    user_id: str
    state: RelationshipState
    profile: AdaptiveProfile
    episodes: List[Episode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "state": self.state.to_dict(),
            "profile": self.profile.to_dict(),
            "episodes": [e.to_dict() for e in self.episodes],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserRelationshipData":
        user_id = data["user_id"]
        return cls(
            user_id=user_id,
            state=RelationshipState.from_dict(data.get("state", {"user_id": user_id})),
            profile=AdaptiveProfile.from_dict(
                data.get("profile", {"user_id": user_id})
            ),
            episodes=[Episode.from_dict(e) for e in data.get("episodes", [])],
        )
