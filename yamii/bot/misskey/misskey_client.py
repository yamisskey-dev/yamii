"""
Misskey API Client
MisskeyのAPI通信を行うクライアント
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from datetime import datetime

from .config import YamiiMisskeyBotConfig


@dataclass
class MisskeyNote:
    """Misskeyノートの構造"""
    id: str
    text: Optional[str]
    user_id: str
    user_username: str
    user_name: Optional[str]
    created_at: datetime
    visibility: str
    mentions: List[str]
    is_reply: bool
    reply_id: Optional[str]
    visible_user_ids: Optional[List[str]] = None


@dataclass
class MisskeyUser:
    """Misskeyユーザーの構造"""
    id: str
    username: str
    name: Optional[str]


class MisskeyClient:
    """Misskeyクライアント"""
    
    def __init__(self, config: YamiiMisskeyBotConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.bot_user_id = None
        self.session = None
        
    async def __aenter__(self):
        """非同期コンテキストマネージャー開始"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
        )
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー終了"""
        if self.session:
            await self.session.close()
            
    async def initialize(self):
        """ボットの初期化"""
        try:
            # 自分のユーザー情報を取得
            user_info = await self.get_my_user_info()
            self.bot_user_id = user_info["id"]
            self.logger.info(f"Bot initialized: @{user_info['username']} ({user_info['name']})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise
            
    async def _api_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Misskey APIリクエストを送信"""
        if params is None:
            params = {}
            
        params["i"] = self.config.misskey_access_token
        
        url = f"{self.config.misskey_instance_url}/api/{endpoint}"
        
        try:
            async with self.session.post(url, json=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API request failed: {response.status} - {error_text}")
                    
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            raise Exception(f"HTTP request failed: {e}")
            
    async def get_my_user_info(self) -> Dict:
        """自分のユーザー情報を取得"""
        return await self._api_request("i")
        
    async def create_note(self, text: str, reply_id: Optional[str] = None, 
                         visibility: str = "home") -> Dict:
        """ノートを投稿"""
        params = {
            "text": text,
            "visibility": visibility
        }
        
        if reply_id:
            params["replyId"] = reply_id
            
        return await self._api_request("notes/create", params)
        
    async def get_mentions(self, limit: int = 10) -> List[MisskeyNote]:
        """メンション通知を取得"""
        params = {
            "limit": limit,
            "includeTypes": ["mention", "reply"]
        }
        
        notifications = await self._api_request("i/notifications", params)
        
        notes = []
        for notif in notifications:
            if notif["type"] in ["mention", "reply"] and "note" in notif:
                note_data = notif["note"]
                notes.append(self._parse_note(note_data))
                
        return notes
        
    async def get_timeline(self, limit: int = 10) -> List[MisskeyNote]:
        """ホームタイムラインを取得"""
        params = {"limit": limit}
        timeline = await self._api_request("notes/timeline", params)
        
        return [self._parse_note(note_data) for note_data in timeline]
        
    def _parse_note(self, note_data: Dict) -> MisskeyNote:
        """APIレスポンスからMisskeyNoteオブジェクトを作成"""
        mentions = []
        if note_data.get("text"):
            # @username の形式のメンションを抽出
            import re
            mentions = re.findall(r'@(\w+)', note_data["text"])
            
        return MisskeyNote(
            id=note_data["id"],
            text=note_data.get("text"),
            user_id=note_data["user"]["id"],
            user_username=note_data["user"]["username"],
            user_name=note_data["user"].get("name"),
            created_at=datetime.fromisoformat(note_data["createdAt"].replace("Z", "+00:00")),
            visibility=note_data["visibility"],
            mentions=mentions,
            is_reply=note_data.get("replyId") is not None,
            reply_id=note_data.get("replyId")
        )
        
    async def start_streaming(self, on_message_callback):
        import websockets
        import json
        
        # yuiと同じURL形式: /streaming?i=アクセストークン
        ws_url = f"{self.config.misskey_instance_url.replace('https://', 'wss://').replace('http://', 'ws://')}/streaming?i={self.config.misskey_access_token}"
        
        self.logger.info(f"Connecting to WebSocket: {ws_url[:50]}...")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                self.logger.info("WebSocket connection established")

                # mainとmessagingチャンネルのみ購読
                channels = [
                    {"channel": "main", "id": "main"},
                    {"channel": "messaging", "id": self.bot_user_id}
                ]
                for ch in channels:
                    connect_message = {
                        "type": "connect",
                        "body": ch
                    }
                    await websocket.send(json.dumps(connect_message))
                    self.logger.info(f"Sent channel connection request: {ch['channel']}")

                self.logger.info("Started streaming connection")

                async for message in websocket:
                    self.logger.debug(f"Raw WebSocket message: {message}")
                    try:
                        data = json.loads(message)
                        self.logger.debug(f"Received WebSocket message: {data.get('type', 'unknown')}")
                        await on_message_callback(data)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse websocket message: {e}")
                    except Exception as e:
                        self.logger.error(f"Error in message callback: {e}")

        except Exception as e:
            self.logger.error(f"Streaming connection failed: {e}")
            self.logger.error(f"WebSocket URL was: {ws_url[:80]}...")
            raise
            
    def is_mentioned(self, note: MisskeyNote) -> bool:
        """ボットがメンションされているかチェック"""
        if self.bot_user_id and note.user_id == self.bot_user_id:
            return False  # 自分の投稿には反応しない
            
        # @ユーザー名形式のメンションをチェック
        if note.text and f"@{self.config.bot_name}" in note.text.lower():
            return True
            
        return False
        
    def extract_message_from_note(self, note: MisskeyNote) -> str:
        """ノートからメッセージテキストを抽出（メンション部分を除去）"""
        if not note.text:
            return ""
            
        text = note.text
        
        # @ボット名を除去
        import re
        text = re.sub(rf'@{re.escape(self.config.bot_name)}\s*', '', text, flags=re.IGNORECASE)
        
        return text.strip()