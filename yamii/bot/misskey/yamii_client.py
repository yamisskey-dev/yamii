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
    custom_prompt_id: Optional[str] = None
    prompt_id: Optional[str] = None


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
            
    async def health_check(self) -> Dict[str, Any]:
        """yamiiサーバーのヘルスチェック"""
        try:
            url = f"{self.config.yamii_api_url}/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Health check failed: {response.status}")
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            raise
            
    async def send_counseling_request(self, request: YamiiRequest) -> YamiiResponse:
        """人生相談リクエストを送信"""
        try:
            url = f"{self.config.yamii_api_url}/counseling"
            
            # リクエストデータを構築
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
            
            # 任意パラメーターを追加
            if request.custom_prompt_id:
                request_data["custom_prompt_id"] = request.custom_prompt_id
            if request.prompt_id:
                request_data["prompt_id"] = request.prompt_id
                
            self.logger.info(f"Sending counseling request to {url}")
            
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
                else:
                    error_text = await response.text()
                    raise Exception(f"Counseling request failed: {response.status} - {error_text}")
                    
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            raise Exception(f"HTTP request failed: {e}")
        except Exception as e:
            self.logger.error(f"Counseling request failed: {e}")
            raise
            
    async def get_custom_prompt(self, user_id: str) -> Dict[str, Any]:
        """カスタムプロンプトを取得"""
        try:
            url = f"{self.config.yamii_api_url}/custom-prompts"
            params = {"user_id": user_id}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return {"has_custom_prompt": False, "prompt": None}
                else:
                    error_text = await response.text()
                    raise Exception(f"Get custom prompt failed: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Failed to get custom prompt: {e}")
            return {"has_custom_prompt": False, "prompt": None}
            
    async def create_custom_prompt(self, user_id: str, prompt_text: str) -> bool:
        """カスタムプロンプトを作成"""
        try:
            url = f"{self.config.yamii_api_url}/custom-prompts"
            params = {"user_id": user_id}
            data = {"prompt_text": prompt_text}
            
            async with self.session.post(url, params=params, json=data) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"Failed to create custom prompt: {e}")
            return False
            
    async def delete_custom_prompt(self, user_id: str) -> bool:
        """カスタムプロンプトを削除"""
        try:
            url = f"{self.config.yamii_api_url}/custom-prompts"
            params = {"user_id": user_id}
            
            async with self.session.delete(url, params=params) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"Failed to delete custom prompt: {e}")
            return False
            
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザープロファイルを取得"""
        try:
            url = f"{self.config.yamii_api_url}/profile"
            params = {"user_id": user_id}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                else:
                    error_text = await response.text()
                    raise Exception(f"Get profile failed: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            return None
            
    async def set_user_profile(self, user_id: str, profile_text: str) -> bool:
        """ユーザープロファイルを設定"""
        try:
            url = f"{self.config.yamii_api_url}/profile"
            params = {"user_id": user_id}
            data = {"profile_text": profile_text}
            
            async with self.session.post(url, params=params, json=data) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"Failed to set user profile: {e}")
            return False
            
    async def delete_user_profile(self, user_id: str) -> bool:
        """ユーザープロファイルを削除"""
        try:
            url = f"{self.config.yamii_api_url}/profile"
            params = {"user_id": user_id}
            
            async with self.session.delete(url, params=params) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.error(f"Failed to delete user profile: {e}")
            return False