"""
Domain Models
統合されたドメインモデル
"""

from .relationship import (
    RelationshipPhase,
    ToneLevel,
    DepthLevel,
    PhaseTransition,
    TopicAffinity,
)
from .conversation import (
    EpisodeType,
    Episode,
    Message,
    ConversationContext,
)
from .user import (
    UserState,
    ProactiveSettings,
)
from .emotion import (
    EmotionType,
    EmotionAnalysis,
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
