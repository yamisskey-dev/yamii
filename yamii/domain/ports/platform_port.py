"""
プラットフォームアダプターポート
各プラットフォーム（Misskey, Discord等）への接続を抽象化
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass
class PlatformMessage:
    """プラットフォームからのメッセージ"""
    id: str
    user_id: str
    content: str
    user_name: str | None = None
    platform: str = "unknown"
    raw_data: dict | None = None


@dataclass
class PlatformResponse:
    """プラットフォームへの応答"""
    content: str
    reply_to_id: str | None = None
    visibility: str = "public"


class IPlatformAdapter(ABC):
    """
    プラットフォームアダプターインターフェース

    各プラットフォーム（Misskey, Discord, Slack等）への
    接続を抽象化。薄いアダプター層として実装。
    """

    @abstractmethod
    async def connect(self) -> None:
        """プラットフォームに接続"""

    @abstractmethod
    async def disconnect(self) -> None:
        """プラットフォームから切断"""

    @abstractmethod
    async def send_message(
        self,
        user_id: str,
        message: str,
        reply_to: str | None = None,
    ) -> bool:
        """
        メッセージを送信

        Args:
            user_id: 送信先ユーザーID
            message: メッセージ内容
            reply_to: リプライ先メッセージID（オプション）

        Returns:
            bool: 送信成功したか
        """

    @abstractmethod
    async def start_listening(
        self,
        message_handler: Callable[[PlatformMessage], Awaitable[str | None]],
    ) -> None:
        """
        メッセージ受信を開始

        Args:
            message_handler: メッセージ受信時のコールバック
                            戻り値は応答メッセージ（Noneなら応答なし）
        """

    @abstractmethod
    async def stop_listening(self) -> None:
        """メッセージ受信を停止"""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """
        プラットフォーム名

        Returns:
            str: "misskey", "discord", "slack" 等
        """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        接続中かどうか

        Returns:
            bool: 接続中か
        """
