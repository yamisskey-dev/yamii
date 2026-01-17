"""
API Dependencies
依存性注入の設定
"""

from __future__ import annotations

from ..adapters.ai.openai import OpenAIAdapterWithFallback
from ..adapters.storage.file import FileStorageAdapter
from ..core.config import get_settings
from ..domain.ports.ai_port import IAIProvider
from ..domain.ports.storage_port import IStorage
from ..domain.services.counseling import CounselingService
from ..domain.services.emotion import EmotionService

# === シングルトンインスタンス ===

_storage: IStorage | None = None
_ai_provider: IAIProvider | None = None
_emotion_service: EmotionService | None = None
_counseling_service: CounselingService | None = None


# === 依存性取得関数 ===


def get_storage() -> IStorage:
    """ストレージを取得

    注意: Zero-Knowledge設計では、このストレージは主にセッション管理等に使用。
    ユーザーデータはEncryptedBlobFileAdapterで暗号化Blobとして保存される。
    """
    global _storage
    if _storage is None:
        settings = get_settings()
        _storage = FileStorageAdapter(data_dir=settings.data_dir)
    return _storage


def get_ai_provider() -> IAIProvider:
    """AIプロバイダーを取得（OpenAI GPT-4.1）"""
    global _ai_provider
    if _ai_provider is None:
        settings = get_settings()
        if not settings.ai.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        _ai_provider = OpenAIAdapterWithFallback(
            api_key=settings.ai.openai_api_key,
            model=settings.ai.openai_model,
        )
    return _ai_provider


def get_emotion_service() -> EmotionService:
    """感情分析サービスを取得"""
    global _emotion_service
    if _emotion_service is None:
        _emotion_service = EmotionService()
    return _emotion_service


def get_counseling_service() -> CounselingService:
    """カウンセリングサービスを取得"""
    global _counseling_service
    if _counseling_service is None:
        _counseling_service = CounselingService(
            ai_provider=get_ai_provider(),
            storage=get_storage(),
            emotion_service=get_emotion_service(),
        )
    return _counseling_service


# === テスト用リセット関数 ===


def reset_dependencies() -> None:
    """依存性をリセット（テスト用）"""
    global \
        _storage, \
        _ai_provider, \
        _emotion_service, \
        _counseling_service
    _storage = None
    _ai_provider = None
    _emotion_service = None
    _counseling_service = None


def set_storage(storage: IStorage) -> None:
    """ストレージを設定（テスト用）"""
    global _storage
    _storage = storage


def set_ai_provider(ai_provider: IAIProvider) -> None:
    """AIプロバイダーを設定（テスト用）"""
    global _ai_provider
    _ai_provider = ai_provider
