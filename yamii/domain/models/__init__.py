"""
Domain Models
統合されたドメインモデル
"""

from .conversation import (
    ConversationContext,
    Message,
)
from .emotion import (
    EmotionAnalysis,
    EmotionType,
)
from .relationship import (
    DepthLevel,
    PhaseTransition,
    RelationshipPhase,
    ToneLevel,
    TopicAffinity,
)
from .user import (
    UserState,
)

__all__ = [
    # 関係性
    "RelationshipPhase",
    "ToneLevel",
    "DepthLevel",
    "PhaseTransition",
    "TopicAffinity",
    # 会話（セッション中のみ使用、保存しない）
    "Message",
    "ConversationContext",
    # ユーザー
    "UserState",
    # 感情
    "EmotionType",
    "EmotionAnalysis",
]
