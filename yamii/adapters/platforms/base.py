"""
プラットフォームアダプター基底クラス
共通機能を提供
"""

from abc import ABC
from collections.abc import Awaitable, Callable

from ...domain.ports.platform_port import IPlatformAdapter, PlatformMessage


class BasePlatformAdapter(IPlatformAdapter, ABC):
    """
    プラットフォームアダプター基底クラス

    共通のユーティリティメソッドを提供。
    各プラットフォーム固有の実装はサブクラスで行う。
    """

    def __init__(self):
        self._connected = False
        self._message_handler: Callable[[PlatformMessage], Awaitable[str | None]] | None = None

    @property
    def is_connected(self) -> bool:
        """接続中かどうか"""
        return self._connected

    def _set_connected(self, connected: bool) -> None:
        """接続状態を設定"""
        self._connected = connected

    def _extract_user_mention(self, content: str, bot_username: str) -> str:
        """
        メンションを除去してメッセージ本文を抽出

        Args:
            content: 元のメッセージ
            bot_username: ボットのユーザー名

        Returns:
            str: メンション除去後のメッセージ
        """
        # @username を除去
        import re
        pattern = rf"@{re.escape(bot_username)}\s*"
        return re.sub(pattern, "", content).strip()

    def _truncate_response(self, response: str, max_length: int = 500) -> str:
        """
        応答を指定文字数で切り詰め

        Args:
            response: 元の応答
            max_length: 最大文字数

        Returns:
            str: 切り詰め後の応答
        """
        if len(response) <= max_length:
            return response
        return response[:max_length - 3] + "..."

    def _format_error_response(self, error: Exception) -> str:
        """
        エラー時の応答を生成

        Args:
            error: 発生したエラー

        Returns:
            str: エラー応答メッセージ
        """
        return (
            "申し訳ありません。今少し調子が悪いようです。"
            "時間を置いてもう一度お試しいただくか、"
            "信頼できる方に直接相談することをお勧めします。"
        )
