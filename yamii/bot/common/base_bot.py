"""
Base Bot Framework
プラットフォーム非依存のボット基盤クラス
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from .session_manager import SessionManager
from .command_parser import CommandParser
from .message_handler import MessageHandler
from .yamii_api_client import YamiiAPIClient


@dataclass
class BaseBotConfig:
    """ボット基底設定クラス"""
    
    # Yamii API設定
    yamii_api_url: str = "http://localhost:8000"
    yamii_api_timeout: int = 30
    
    # ボット基本設定
    bot_name: str = "yamii"
    bot_username: str = "yamii"
    
    # セッション設定
    session_timeout: int = 3600  # 1時間
    
    # ログ設定
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # 機能設定
    enable_dm: bool = True
    enable_mentions: bool = True
    enable_timeline: bool = False
    enable_global_timeline: bool = False
    
    # 危機対応設定
    crisis_hotlines: list = None
    
    def __post_init__(self):
        """設定の後処理"""
        if self.crisis_hotlines is None:
            self.crisis_hotlines = [
                "いのちの電話: 0570-783-556",
                "こころの健康相談統一ダイヤル: 0570-064-556"
            ]


class BaseBot(ABC):
    """プラットフォーム非依存のボット基底クラス"""
    
    def __init__(self, config: BaseBotConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 共通コンポーネント初期化
        self.session_manager = SessionManager(config.session_timeout)
        self.command_parser = CommandParser()
        self.message_handler = MessageHandler(config)
        self.yamii_client = YamiiAPIClient(config)
        
        # プラットフォーム固有の処理済みメッセージ管理
        self.processed_messages: Set[str] = set()
        
    async def start(self):
        """ボット開始（共通処理）"""
        self.logger.info(f"Starting {self.__class__.__name__}...")
        
        # Yamii API健全性チェック
        try:
            async with self.yamii_client:
                health = await self.yamii_client.health_check()
                self.logger.info(f"Yamii server status: {health.get('status')}")
                
                # プラットフォーム固有の開始処理
                await self.platform_start()
                
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            raise
    
    @abstractmethod
    async def platform_start(self):
        """プラットフォーム固有の開始処理（サブクラスで実装）"""
        pass
    
    @abstractmethod
    async def send_message(self, recipient_id: str, text: str, **kwargs):
        """メッセージ送信（プラットフォーム固有、サブクラスで実装）"""
        pass
    
    @abstractmethod
    async def send_reply(self, original_message_id: str, text: str, **kwargs):
        """返信送信（プラットフォーム固有、サブクラスで実装）"""
        pass
    
    async def handle_message(self, message_data: Dict[str, Any]) -> bool:
        """共通メッセージ処理"""
        try:
            # メッセージ重複チェック
            message_id = message_data.get("id")
            if message_id and message_id in self.processed_messages:
                return False
                
            if message_id:
                self.processed_messages.add(message_id)
                self._cleanup_processed_messages()
            
            # 共通メッセージ処理
            return await self.message_handler.process_message(
                message_data, self.yamii_client, self.session_manager, self
            )
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return False
    
    def _cleanup_processed_messages(self):
        """処理済みメッセージのクリーンアップ"""
        if len(self.processed_messages) > 1000:
            self.processed_messages = set(list(self.processed_messages)[-500:])
    
    async def stop(self):
        """ボット停止（共通処理）"""
        self.logger.info(f"Stopping {self.__class__.__name__}...")
        
        # セッション管理のクリーンアップ
        self.session_manager.cleanup_expired_sessions()
        
        # プラットフォーム固有の停止処理
        await self.platform_stop()
    
    @abstractmethod
    async def platform_stop(self):
        """プラットフォーム固有の停止処理（サブクラスで実装）"""
        pass


def setup_logging(config: BaseBotConfig):
    """共通ログ設定"""
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=config.log_file
    )