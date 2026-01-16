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
        self._message_handler: (
            Callable[[PlatformMessage], Awaitable[str | None]] | None
        ) = None

    @property
    def is_connected(self) -> bool:
        """接続中かどうか"""
        return self._connected

    def _set_connected(self, connected: bool) -> None:
        """接続状態を設定"""
        self._connected = connected
