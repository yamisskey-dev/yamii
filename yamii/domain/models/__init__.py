"""
Domain Models
統合されたドメインモデル
"""

from .conversation import (
    ConversationContext,
    Episode,
    EpisodeType,
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
    ProactiveSettings,
    UserState,
)

__all__ = [
    # 関係性
    "RelationshipPhase",
    "ToneLevel",
    "DepthLevel",
    "PhaseTransition",
    "TopicAffinity",
    # 会話
    "EpisodeType",
    "Episode",
    "Message",
    "ConversationContext",
    # ユーザー
    "UserState",
    "ProactiveSettings",
    # 感情
    "EmotionType",
    "EmotionAnalysis",
]
