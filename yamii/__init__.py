"""
Yamii - Networked Artificial Virtual Intelligence
AI Chat Service
"""

__version__ = "0.1.0"

# 基本モジュール
from .memory import MemorySystem
from .user_profile import UserProfile, UserProfileManager

# 高度な機能
from .conversation_summary import (
    ConversationSummary,
    ConversationSummarizer,
    ConversationSummaryStore,
    SentimentType,
    UserMention,
    MentionType,
)
from .context_awareness import (
    ConversationContext,
    ContextAwareResponseGenerator,
    ContextAwareResponse,
    EmotionalState,
    ConversationPhase,
    TopicTransition,
)
from .user_learning import (
    EnhancedUserProfile,
    UserLearningManager,
    UserPreferences,
    UserLearningData,
    CommunicationStyle,
    ResponseLength,
    TechnicalLevel,
)
from .intelligent_search import (
    IntelligentSearchEngine,
    KnowledgeGraph,
    SearchResult,
    ParsedQuery,
)
from .analytics import (
    AnalyticsEngine,
    UserAnalytics,
    GlobalAnalytics,
    TopicAnalysis,
    SentimentAnalysis,
    Recommendation,
)
from .persona import (
    Persona,
    PersonaStore,
    PersonaAnalyzer,
    PersonaSourceType,
    PersonalityProfile,
    PersonalityTrait,
    SpeechPattern,
    BackgroundStory,
    ResponseBehavior,
    CommunicationTone,
    get_persona_store,
    get_persona_analyzer,
    get_persona_prompt,
    list_available_personas,
)

__all__ = [
    # Version
    "__version__",
    # 基本
    "MemorySystem",
    "UserProfile",
    "UserProfileManager",
    # 会話サマリー
    "ConversationSummary",
    "ConversationSummarizer",
    "ConversationSummaryStore",
    "SentimentType",
    "UserMention",
    "MentionType",
    # コンテキスト認識
    "ConversationContext",
    "ContextAwareResponseGenerator",
    "ContextAwareResponse",
    "EmotionalState",
    "ConversationPhase",
    "TopicTransition",
    # ユーザー学習
    "EnhancedUserProfile",
    "UserLearningManager",
    "UserPreferences",
    "UserLearningData",
    "CommunicationStyle",
    "ResponseLength",
    "TechnicalLevel",
    # インテリジェント検索
    "IntelligentSearchEngine",
    "KnowledgeGraph",
    "SearchResult",
    "ParsedQuery",
    # 分析
    "AnalyticsEngine",
    "UserAnalytics",
    "GlobalAnalytics",
    "TopicAnalysis",
    "SentimentAnalysis",
    "Recommendation",
    # ペルソナ（キャラクター設定）
    "Persona",
    "PersonaStore",
    "PersonaAnalyzer",
    "PersonaSourceType",
    "PersonalityProfile",
    "PersonalityTrait",
    "SpeechPattern",
    "BackgroundStory",
    "ResponseBehavior",
    "CommunicationTone",
    "get_persona_store",
    "get_persona_analyzer",
    "get_persona_prompt",
    "list_available_personas",
]