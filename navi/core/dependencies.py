"""
依存性注入コンテナ
クリーンアーキテクチャに基づいた依存関係管理
"""

import os
from typing import Optional, Dict, Any
from functools import lru_cache

from ..user_profile import UserProfileManager
from ..user_settings import UserSettingsManager
from ..memory import MemorySystem
from .prompt_store import PromptStore, get_prompt_store


class DependencyContainer:
    """依存性注入コンテナ"""
    
    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self):
        """依存関係を初期化"""
        if self._initialized:
            return
        
        # データ層
        self._instances['memory_system'] = MemorySystem()
        self._instances['user_profile_manager'] = UserProfileManager()
        self._instances['settings_manager'] = UserSettingsManager()
        self._instances['prompt_store'] = PromptStore()
        
        # ビジネス層は遅延初期化（API keyが必要なため）
        
        self._initialized = True
    
    def get_memory_system(self) -> MemorySystem:
        """メモリシステムを取得"""
        if not self._initialized:
            self.initialize()
        return self._instances['memory_system']
    
    def get_user_profile_manager(self) -> UserProfileManager:
        """ユーザープロファイル管理を取得"""
        if not self._initialized:
            self.initialize()
        return self._instances['user_profile_manager']
    
    def get_settings_manager(self) -> UserSettingsManager:
        """設定管理を取得"""
        if not self._initialized:
            self.initialize()
        return self._instances['settings_manager']
    
    def get_prompt_store(self) -> PromptStore:
        """プロンプトストアを取得"""
        if not self._initialized:
            self.initialize()
        return self._instances['prompt_store']
    
    def get_counseling_service(self):
        """カウンセリングサービスを取得（遅延初期化）"""
        if 'counseling_service' not in self._instances:
            from ..services.counseling_service import CounselingService
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not configured")
            
            # 依存関係を注入してサービスを作成
            self._instances['counseling_service'] = CounselingService(
                api_key=api_key,
                memory_system=self.get_memory_system(),
                user_profile_manager=self.get_user_profile_manager(),
                settings_manager=self.get_settings_manager(),
                prompt_store=self.get_prompt_store()
            )
        
        return self._instances['counseling_service']


# グローバルコンテナインスタンス
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """グローバル依存性注入コンテナを取得"""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


# FastAPI用の依存性注入関数群
def get_memory_system() -> MemorySystem:
    """FastAPI依存性注入: メモリシステム"""
    return get_container().get_memory_system()


def get_user_profile_manager() -> UserProfileManager:
    """FastAPI依存性注入: ユーザープロファイル管理"""
    return get_container().get_user_profile_manager()


def get_settings_manager() -> UserSettingsManager:
    """FastAPI依存性注入: 設定管理"""
    return get_container().get_settings_manager()


def get_prompt_store() -> PromptStore:
    """FastAPI依存性注入: プロンプトストア"""
    return get_container().get_prompt_store()


def get_counseling_service():
    """FastAPI依存性注入: カウンセリングサービス"""
    return get_container().get_counseling_service()