"""
Yamii Domain Layer
コアビジネスロジックとドメインモデル
"""

from __future__ import annotations

from .models import (
    ConversationContext,
    DepthLevel,
    EmotionAnalysis,
    EmotionType,
    Message,
    PhaseTransition,
    RelationshipPhase,
    ToneLevel,
    TopicAffinity,
    UserState,
)

__all__ = [
    # 関係性
    "RelationshipPhase",
    "ToneLevel",
    "DepthLevel",
    "PhaseTransition",
    "TopicAffinity",
    # 会話（セッション中のみ、保存しない）
    "Message",
    "ConversationContext",
    # ユーザー
    "UserState",
    # 感情
    "EmotionType",
    "EmotionAnalysis",
]
