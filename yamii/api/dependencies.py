"""
API Dependencies
依存性注入の設定
"""

import os
from functools import lru_cache
from typing import Optional

from ..domain.ports.storage_port import IStorage
from ..domain.ports.ai_port import IAIProvider
from ..domain.services.emotion import EmotionService
from ..domain.services.counseling import CounselingService
from ..domain.services.outreach import ProactiveOutreachService
from ..adapters.storage.file import FileStorageAdapter
from ..adapters.ai.gemini import GeminiAdapterWithFallback


# === 設定 ===

@lru_cache()
def get_api_key() -> str:
    """Gemini API キーを取得"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    return api_key


@lru_cache()
def get_data_dir() -> str:
    """データディレクトリを取得"""
    return os.getenv("YAMII_DATA_DIR", "data")


# === シングルトンインスタンス ===

_storage: Optional[IStorage] = None
_ai_provider: Optional[IAIProvider] = None
_emotion_service: Optional[EmotionService] = None
_counseling_service: Optional[CounselingService] = None
_outreach_service: Optional[ProactiveOutreachService] = None


# === 依存性取得関数 ===

def get_storage() -> IStorage:
    """ストレージを取得"""
    global _storage
    if _storage is None:
        _storage = FileStorageAdapter(data_dir=get_data_dir())
    return _storage


def get_ai_provider() -> IAIProvider:
    """AIプロバイダーを取得"""
    global _ai_provider
    if _ai_provider is None:
        _ai_provider = GeminiAdapterWithFallback(
            api_key=get_api_key(),
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
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


def get_outreach_service() -> ProactiveOutreachService:
    """プロアクティブアウトリーチサービスを取得"""
    global _outreach_service
    if _outreach_service is None:
        _outreach_service = ProactiveOutreachService(
            storage=get_storage(),
            emotion_service=get_emotion_service(),
        )
    return _outreach_service


# === テスト用リセット関数 ===

def reset_dependencies() -> None:
    """依存性をリセット（テスト用）"""
    global _storage, _ai_provider, _emotion_service, _counseling_service, _outreach_service
    _storage = None
    _ai_provider = None
    _emotion_service = None
    _counseling_service = None
    _outreach_service = None


def set_storage(storage: IStorage) -> None:
    """ストレージを設定（テスト用）"""
    global _storage
    _storage = storage


def set_ai_provider(ai_provider: IAIProvider) -> None:
    """AIプロバイダーを設定（テスト用）"""
    global _ai_provider
    _ai_provider = ai_provider
