"""
Yamii - Zero-Knowledge メンタルヘルスAI相談システム

プライバシーファーストのAI相談サービス:
- Zero-Knowledge: サーバーは会話内容を保存・閲覧しない
- クライアント側暗号化: ユーザーデータはユーザーのみ復号可能
- ノーログ: 会話履歴はセッション中のみ保持
"""

from pathlib import Path
import tomllib

_pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
with _pyproject.open("rb") as _f:
    __version__: str = tomllib.load(_f)["project"]["version"]

# ===== Domain Models =====
from .domain.models import (
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
)


# ===== Adapters (lazy import) =====
# アダプターは依存関係が多いため遅延インポート
def get_openai_adapter():
    from .adapters.ai.openai import OpenAIAdapter

    return OpenAIAdapter


def get_file_storage_adapter():
    from .adapters.storage.file import FileStorageAdapter

    return FileStorageAdapter


def get_encrypted_blob_storage():
    from .adapters.storage.encrypted_blob_file import EncryptedBlobFileAdapter

    return EncryptedBlobFileAdapter


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
    # Domain Models - 会話（セッション中のみ）
    "Message",
    "ConversationContext",
    # Domain Models - ユーザー
    "UserState",
    # Domain Models - 感情
    "EmotionType",
    "EmotionAnalysis",
    # Domain Services
    "EmotionService",
    "CounselingService",
    # Ports
    "IStorage",
    "IAIProvider",
    "IPlatformAdapter",
    # Adapters (lazy)
    "get_openai_adapter",
    "get_file_storage_adapter",
    "get_encrypted_blob_storage",
    # API (lazy)
    "get_app",
    "create_app",
]
