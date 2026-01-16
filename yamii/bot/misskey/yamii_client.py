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
    # Bot向け整形済みレスポンス（危機対応情報を含む）
    formatted_response: Optional[str] = None
    crisis_resources: Optional[List[str]] = None


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
                    is_crisis=data["is_crisis"],
                    formatted_response=data.get("formatted_response"),
                    crisis_resources=data.get("crisis_resources"),
                )
            error_text = await response.text()
            raise Exception(f"Counseling failed: {response.status} - {error_text}")

    async def get_outreach_analysis(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーのアウトリーチ分析を取得"""
        url = f"{self.config.yamii_api_url}/v1/users/{user_id}/outreach/analyze"

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            self.logger.error(f"Outreach analysis failed: {e}")
            return None

    async def get_all_users_needing_outreach(self) -> List[Dict[str, Any]]:
        """アウトリーチが必要な全ユーザーを取得"""
        url = f"{self.config.yamii_api_url}/v1/outreach/pending"

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("users", [])
                return []
        except Exception as e:
            self.logger.error(f"Get pending outreach failed: {e}")
            return []
