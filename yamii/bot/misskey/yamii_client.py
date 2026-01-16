"""
Yamii API Client
yamiiサーバーとの通信を行うクライアント
"""

import aiohttp
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from datetime import datetime

from .config import YamiiMisskeyBotConfig


@dataclass
class YamiiResponse:
    """yamiiサーバーからの応答"""
    response: str
    session_id: str
    timestamp: datetime
    emotion_analysis: Dict[str, Any]
    advice_type: str
    follow_up_questions: List[str]
    is_crisis: bool


@dataclass
class YamiiRequest:
    """yamiiサーバーへのリクエスト"""
    message: str
    user_id: str
    user_name: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class YamiiClient:
    """Yamii APIクライアント"""

    def __init__(self, config: YamiiMisskeyBotConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None

    async def __aenter__(self):
        """非同期コンテキストマネージャー開始"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー終了"""
        if self.session:
            await self.session.close()

    async def close(self):
        """セッションを閉じる"""
        if self.session:
            await self.session.close()

    async def health_check(self) -> Dict[str, Any]:
        """yamiiサーバーのヘルスチェック"""
        url = f"{self.config.yamii_api_url}/v1/health"
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            raise Exception(f"Health check failed: {response.status}")

    async def send_counseling_request(self, request: YamiiRequest) -> YamiiResponse:
        """カウンセリングリクエストを送信"""
        url = f"{self.config.yamii_api_url}/v1/counseling"

        request_data = {
            "message": request.message,
            "user_id": request.user_id,
            "user_name": request.user_name,
            "session_id": request.session_id,
            "context": request.context or {
                "platform": "misskey",
                "bot_name": self.config.bot_name
            }
        }

        self.logger.debug(f"Sending request to {url}")

        async with self.session.post(url, json=request_data) as response:
            if response.status == 200:
                data = await response.json()
                return YamiiResponse(
                    response=data["response"],
                    session_id=data["session_id"],
                    timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
                    emotion_analysis=data["emotion_analysis"],
                    advice_type=data["advice_type"],
                    follow_up_questions=data["follow_up_questions"],
                    is_crisis=data["is_crisis"]
                )
            error_text = await response.text()
            raise Exception(f"Counseling failed: {response.status} - {error_text}")
