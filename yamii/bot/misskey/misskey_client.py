"""
Misskey API Client
MisskeyのAPI通信を行うクライアント
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import aiohttp

from .config import YamiiMisskeyBotConfig


@dataclass
class MisskeyNote:
    """Misskeyノートの構造"""

    id: str
    text: str | None
    user_id: str
    user_username: str
    user_name: str | None
    created_at: datetime
    visibility: str
    mentions: list[str]
    is_reply: bool
    reply_id: str | None
    visible_user_ids: list[str] | None = None


@dataclass
class MisskeyUser:
    """Misskeyユーザーの構造"""

    id: str
    username: str
    name: str | None


@dataclass
class MisskeyChatMessage:
    """Misskeyチャットメッセージの構造"""

    id: str
    text: str | None
    user_id: str
    user_username: str
    user_name: str | None
    created_at: datetime
    is_read: bool
    file_id: str | None = None


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
            self.logger.info(
                f"Bot initialized: @{user_info['username']} ({user_info['name']})"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise

    async def _api_request(self, endpoint: str, params: dict = None) -> dict:
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
                    raise Exception(
                        f"API request failed: {response.status} - {error_text}"
                    )

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            raise Exception(f"HTTP request failed: {e}")

    async def get_my_user_info(self) -> dict:
        """自分のユーザー情報を取得"""
        return await self._api_request("i")

    async def create_note(
        self, text: str, reply_id: str | None = None, visibility: str = "home"
    ) -> dict:
        """ノートを投稿"""
        params = {"text": text, "visibility": visibility}

        if reply_id:
            params["replyId"] = reply_id

        return await self._api_request("notes/create", params)

    async def get_mentions(self, limit: int = 10) -> list[MisskeyNote]:
        """メンション通知を取得"""
        params = {"limit": limit, "includeTypes": ["mention", "reply"]}

        notifications = await self._api_request("i/notifications", params)

        notes = []
        for notif in notifications:
            if notif["type"] in ["mention", "reply"] and "note" in notif:
                note_data = notif["note"]
                notes.append(self._parse_note(note_data))

        return notes

    async def get_timeline(self, limit: int = 10) -> list[MisskeyNote]:
        """ホームタイムラインを取得"""
        params = {"limit": limit}
        timeline = await self._api_request("notes/timeline", params)

        return [self._parse_note(note_data) for note_data in timeline]

    async def send_chat_message(self, user_id: str, text: str) -> dict:
        """チャットメッセージを送信"""
        params = {"toUserId": user_id, "text": text}
        return await self._api_request("chat/messages/create-to-user", params)

    async def read_chat_message(self, message_id: str) -> dict:
        """チャットメッセージを既読にする"""
        params = {"messageId": message_id}
        return await self._api_request("chat/messages/read", params)

    def _parse_chat_message(self, data: dict) -> MisskeyChatMessage:
        """APIレスポンスからMisskeyChatMessageオブジェクトを作成"""
        return MisskeyChatMessage(
            id=data["id"],
            text=data.get("text"),
            user_id=data["fromUserId"],
            user_username=data.get("fromUser", {}).get("username", "unknown"),
            user_name=data.get("fromUser", {}).get("name"),
            created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
            is_read=data.get("isRead", False),
            file_id=data.get("fileId"),
        )

    def _parse_note(self, note_data: dict) -> MisskeyNote:
        """APIレスポンスからMisskeyNoteオブジェクトを作成"""
        mentions = []
        if note_data.get("text"):
            # @username の形式のメンションを抽出
            import re

            mentions = re.findall(r"@(\w+)", note_data["text"])

        return MisskeyNote(
            id=note_data["id"],
            text=note_data.get("text"),
            user_id=note_data["user"]["id"],
            user_username=note_data["user"]["username"],
            user_name=note_data["user"].get("name"),
            created_at=datetime.fromisoformat(
                note_data["createdAt"].replace("Z", "+00:00")
            ),
            visibility=note_data["visibility"],
            mentions=mentions,
            is_reply=note_data.get("replyId") is not None,
            reply_id=note_data.get("replyId"),
        )

    async def start_streaming(self, on_message_callback):
        import json

        import websockets

        # yuiと同じURL形式: /streaming?i=アクセストークン
        ws_url = f"{self.config.misskey_instance_url.replace('https://', 'wss://').replace('http://', 'ws://')}/streaming?i={self.config.misskey_access_token}"

        self.logger.info(f"Connecting to WebSocket: {ws_url[:50]}...")

        try:
            async with websockets.connect(ws_url) as websocket:
                self.logger.info("WebSocket connection established")

                # main（通知）、homeTimeline（タイムライン）、messaging（DM）を購読
                channels = [
                    {"channel": "main", "id": "main"},
                    {"channel": "homeTimeline", "id": "homeTimeline"},
                    {"channel": "messaging", "id": self.bot_user_id},
                ]
                for ch in channels:
                    connect_message = {"type": "connect", "body": ch}
                    await websocket.send(json.dumps(connect_message))
                    self.logger.info(
                        f"Sent channel connection request: {ch['channel']}"
                    )

                self.logger.info("Started streaming connection")

                async for message in websocket:
                    self.logger.debug(f"Raw WebSocket message: {message}")
                    try:
                        data = json.loads(message)
                        self.logger.debug(
                            f"Received WebSocket message: {data.get('type', 'unknown')}"
                        )
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

    def is_direct_message(self, note: MisskeyNote) -> bool:
        """ダイレクトメッセージ（指定あり投稿）かチェック"""
        # visibility=specifiedでボットが宛先に含まれている場合
        if note.visibility == "specified":
            if note.visible_user_ids and self.bot_user_id in note.visible_user_ids:
                return True
        return False

    def is_reply_to_bot(self, note: MisskeyNote) -> bool:
        """ボットの投稿へのリプライかチェック"""
        return note.is_reply and note.reply_id is not None

    def extract_message_from_note(self, note: MisskeyNote) -> str:
        """ノートからメッセージテキストを抽出（メンション部分を除去）"""
        if not note.text:
            return ""

        text = note.text

        # @ボット名を除去
        import re

        text = re.sub(
            rf"@{re.escape(self.config.bot_name)}\s*", "", text, flags=re.IGNORECASE
        )

        return text.strip()
