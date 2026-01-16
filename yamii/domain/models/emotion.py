"""
感情モデル
統合された感情分類と分析結果
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EmotionType(Enum):
    """
    感情タイプ
    統一された感情分類（複数システムから統合）
    """

    HAPPINESS = "happiness"  # 喜び・幸福感
    SADNESS = "sadness"  # 悲しみ・落胆
    ANXIETY = "anxiety"  # 不安・心配
    ANGER = "anger"  # 怒り・イライラ
    LONELINESS = "loneliness"  # 孤独感・寂しさ
    DEPRESSION = "depression"  # うつ・絶望感（危機指標）
    STRESS = "stress"  # ストレス・疲労
    CONFUSION = "confusion"  # 混乱・迷い
    HOPE = "hope"  # 希望・前向きさ
    NEUTRAL = "neutral"  # 中性・平常


@dataclass
class EmotionAnalysis:
    """
    感情分析結果
    単一の分析結果構造（複数システムから統合）
    """

    primary_emotion: EmotionType
    intensity: float  # 0.0-1.0（正規化）
    stability: float  # 0.0-1.0（感情の安定性）
    is_crisis: bool
    all_emotions: dict[str, float]
    confidence: float  # 0.0-1.0

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "primary_emotion": self.primary_emotion.value,
            "intensity": self.intensity,
            "stability": self.stability,
            "is_crisis": self.is_crisis,
            "all_emotions": self.all_emotions,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmotionAnalysis":
        """辞書から生成"""
        return cls(
            primary_emotion=EmotionType(data.get("primary_emotion", "neutral")),
            intensity=data.get("intensity", 0.5),
            stability=data.get("stability", 0.5),
            is_crisis=data.get("is_crisis", False),
            all_emotions=data.get("all_emotions", {}),
            confidence=data.get("confidence", 0.0),
        )

    @classmethod
    def neutral(cls) -> "EmotionAnalysis":
        """中性の分析結果を生成"""
        return cls(
            primary_emotion=EmotionType.NEUTRAL,
            intensity=0.0,
            stability=1.0,
            is_crisis=False,
            all_emotions={},
            confidence=1.0,
        )


# 危機指標となる感情
CRISIS_EMOTIONS = {EmotionType.DEPRESSION}

# ネガティブ感情
NEGATIVE_EMOTIONS = {
    EmotionType.SADNESS,
    EmotionType.ANXIETY,
    EmotionType.ANGER,
    EmotionType.LONELINESS,
    EmotionType.DEPRESSION,
    EmotionType.STRESS,
}

# ポジティブ感情
POSITIVE_EMOTIONS = {
    EmotionType.HAPPINESS,
    EmotionType.HOPE,
}
