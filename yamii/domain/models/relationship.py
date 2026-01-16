"""
関係性モデル
ユーザーとの関係性フェーズ、トーン設定等を定義
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class RelationshipPhase(Enum):
    """
    関係性フェーズ
    対話回数に応じて段階的に深まる関係性
    """

    STRANGER = "stranger"  # 初対面 (0-5回)
    ACQUAINTANCE = "acquaintance"  # 顔見知り (6-20回)
    FAMILIAR = "familiar"  # 親しい関係 (21-50回)
    TRUSTED = "trusted"  # 信頼関係 (51回以上)


class ToneLevel(Enum):
    """応答トーン"""

    WARM = "warm"  # 温かみのある
    PROFESSIONAL = "professional"  # 専門的
    CASUAL = "casual"  # カジュアル
    BALANCED = "balanced"  # バランス型


class DepthLevel(Enum):
    """応答の深さ"""

    SHALLOW = "shallow"  # 浅い（短い応答）
    MEDIUM = "medium"  # 中程度
    DEEP = "deep"  # 深い（詳細な応答）


@dataclass
class PhaseTransition:
    """フェーズ遷移記録"""

    from_phase: RelationshipPhase
    to_phase: RelationshipPhase
    transitioned_at: datetime
    interaction_count: int
    trigger: str  # 遷移のきっかけ

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_phase": self.from_phase.value,
            "to_phase": self.to_phase.value,
            "transitioned_at": self.transitioned_at.isoformat(),
            "interaction_count": self.interaction_count,
            "trigger": self.trigger,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PhaseTransition":
        return cls(
            from_phase=RelationshipPhase(data["from_phase"]),
            to_phase=RelationshipPhase(data["to_phase"]),
            transitioned_at=datetime.fromisoformat(data["transitioned_at"]),
            interaction_count=data["interaction_count"],
            trigger=data["trigger"],
        )


@dataclass
class TopicAffinity:
    """トピック関心度"""

    topic: str
    affinity_score: float = 0.0  # 関心度 (0.0-1.0)
    mention_count: int = 0
    last_mentioned: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "affinity_score": self.affinity_score,
            "mention_count": self.mention_count,
            "last_mentioned": self.last_mentioned.isoformat()
            if self.last_mentioned
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopicAffinity":
        return cls(
            topic=data["topic"],
            affinity_score=data.get("affinity_score", 0.0),
            mention_count=data.get("mention_count", 0),
            last_mentioned=datetime.fromisoformat(data["last_mentioned"])
            if data.get("last_mentioned")
            else None,
        )
