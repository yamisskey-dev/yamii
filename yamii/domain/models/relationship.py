"""
関係性モデル
ユーザーとの関係性フェーズ、トーン設定等を定義
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class RelationshipPhase(Enum):
    """
    関係性フェーズ
    対話回数に応じて段階的に深まる関係性
    """
    STRANGER = "stranger"           # 初対面 (0-5回)
    ACQUAINTANCE = "acquaintance"   # 顔見知り (6-20回)
    FAMILIAR = "familiar"           # 親しい関係 (21-50回)
    TRUSTED = "trusted"             # 信頼関係 (51回以上)


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


# フェーズごとの対応指示
PHASE_INSTRUCTIONS = {
    RelationshipPhase.STRANGER: """
初対面の相談者です。丁寧で礼儀正しい対応を心がけてください。
- 敬語を使用する
- 基本的な情報収集を行う
- プライバシーに配慮した質問をする
- 信頼関係の構築を最優先
""",
    RelationshipPhase.ACQUAINTANCE: """
顔見知りの関係です。少しずつ距離を縮めていきましょう。
- やや柔らかい言葉遣いも可
- 以前の会話を参照してもよい
- 適度な自己開示も効果的
""",
    RelationshipPhase.FAMILIAR: """
親しい関係が築けています。自然な会話を心がけてください。
- カジュアルな言葉遣いも適切
- 過去の経験を踏まえた助言が可能
- 冗談や軽い雑談も効果的
""",
    RelationshipPhase.TRUSTED: """
深い信頼関係があります。真剣で深い対話が可能です。
- 本音での対話を心がける
- 厳しい助言も必要に応じて
- 長期的な視点での支援
- 相手の成長を見守る姿勢
""",
}


def get_phase_instruction(phase: RelationshipPhase) -> str:
    """フェーズに応じた対応指示を取得"""
    return PHASE_INSTRUCTIONS.get(phase, PHASE_INSTRUCTIONS[RelationshipPhase.STRANGER])
