"""
Yamii - メンタルヘルス特化AI相談システム

あなたがいる場所に寄り添い、成長を見守り、必要な時に先に声をかける。

ChatGPT/Claude/Gemini WebUIやAwarefy/Ubieが提供できない独自価値:
1. プロアクティブケア: ユーザーが連絡しなくても、パターン検出でBotから先にチェックイン
2. 継続的関係性構築: STRANGER→TRUSTEDフェーズで深い信頼関係を構築
3. プライバシーファースト: E2EE完全対応でデータは暗号化
"""

__version__ = "2.0.0"

# ===== Domain Models =====
from .domain.models import (
    ConversationContext,
    DepthLevel,
    EmotionAnalysis,
    # 感情
    EmotionType,
    Episode,
    # 会話
    EpisodeType,
    Message,
    PhaseTransition,
    ProactiveSettings,
    # 関係性
    RelationshipPhase,
    ToneLevel,
    TopicAffinity,
    # ユーザー
    UserState,
)

# ===== Ports (Interfaces) =====
from .domain.ports import (
    IAIProvider,
    IPlatformAdapter,
    IStorage,
)

# ===== Domain Services =====
from .domain.services import (
    CounselingService,
    EmotionService,
    ProactiveOutreachService,
)


# ===== Adapters (lazy import) =====
# アダプターは依存関係が多いため遅延インポート
def get_openai_adapter():
    from .adapters.ai.openai import OpenAIAdapter
    return OpenAIAdapter

def get_file_storage_adapter():
    from .adapters.storage.file import FileStorageAdapter
    return FileStorageAdapter

# ===== API (lazy import) =====
def get_app():
    from .api import app
    return app

def create_app():
    from .api import create_app as _create_app
    return _create_app()

__all__ = [
    # Version
    "__version__",
    # Domain Models - 関係性
    "RelationshipPhase",
    "ToneLevel",
    "DepthLevel",
    "PhaseTransition",
    "TopicAffinity",
    # Domain Models - 会話
    "EpisodeType",
    "Episode",
    "Message",
    "ConversationContext",
    # Domain Models - ユーザー
    "UserState",
    "ProactiveSettings",
    # Domain Models - 感情
    "EmotionType",
    "EmotionAnalysis",
    # Domain Services
    "EmotionService",
    "CounselingService",
    "ProactiveOutreachService",
    # Ports
    "IStorage",
    "IAIProvider",
    "IPlatformAdapter",
    # Adapters (lazy)
    "get_openai_adapter",
    "get_file_storage_adapter",
    # API (lazy)
    "get_app",
    "create_app",
]
