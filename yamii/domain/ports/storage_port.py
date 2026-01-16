"""
ストレージポート
ユーザーデータ永続化のインターフェース
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models.user import UserState


class IStorage(ABC):
    """
    ストレージインターフェース

    ユーザーデータの永続化を抽象化。
    実装はファイル、PostgreSQL、Redis等で切り替え可能。
    """

    @abstractmethod
    async def save_user(self, user: UserState) -> None:
        """
        ユーザー状態を保存

        Args:
            user: 保存するユーザー状態
        """
        pass

    @abstractmethod
    async def load_user(self, user_id: str) -> Optional[UserState]:
        """
        ユーザー状態を読み込み

        Args:
            user_id: ユーザーID

        Returns:
            Optional[UserState]: ユーザー状態（存在しない場合None）
        """
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """
        ユーザーデータを削除

        Args:
            user_id: ユーザーID

        Returns:
            bool: 削除成功したか
        """
        pass

    @abstractmethod
    async def list_users(self) -> List[str]:
        """
        全ユーザーIDのリストを取得

        Returns:
            List[str]: ユーザーIDリスト
        """
        pass

    @abstractmethod
    async def user_exists(self, user_id: str) -> bool:
        """
        ユーザーが存在するかチェック

        Args:
            user_id: ユーザーID

        Returns:
            bool: 存在するか
        """
        pass

    async def get_or_create_user(self, user_id: str) -> UserState:
        """
        ユーザーを取得または作成

        Args:
            user_id: ユーザーID

        Returns:
            UserState: ユーザー状態
        """
        user = await self.load_user(user_id)
        if user is None:
            user = UserState(user_id=user_id)
            await self.save_user(user)
        return user

    async def export_user_data(self, user_id: str) -> Optional[dict]:
        """
        ユーザーデータをエクスポート（GDPR対応）

        Args:
            user_id: ユーザーID

        Returns:
            Optional[dict]: エクスポートされたデータ
        """
        user = await self.load_user(user_id)
        if user:
            return user.to_dict()
        return None
