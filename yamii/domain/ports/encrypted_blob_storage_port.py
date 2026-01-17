"""
暗号化Blobストレージポート
Zero-Knowledge アーキテクチャ用

サーバーはクライアントから受け取った暗号化Blobをそのまま保存する。
復号はクライアント側でのみ行われ、サーバーは内容を知ることができない。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EncryptedBlob:
    """
    暗号化されたデータBlob

    クライアント側で暗号化されたデータ。
    サーバーはこれをそのまま保存し、内容を解釈しない。
    """

    user_id: str
    data: str  # Base64エンコードされた暗号文
    nonce: str  # Base64エンコードされたnonce
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "data": self.data,
            "nonce": self.nonce,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EncryptedBlob":
        return cls(
            user_id=data["user_id"],
            data=data["data"],
            nonce=data["nonce"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


class IEncryptedBlobStorage(ABC):
    """
    Zero-Knowledge 暗号化Blobストレージインターフェース

    サーバーは暗号化されたBlobを保存するだけで、
    内容を復号したり解釈したりしない。
    """

    @abstractmethod
    async def save_blob(self, user_id: str, encrypted_data: str, nonce: str) -> None:
        """
        暗号化されたBlobを保存

        Args:
            user_id: ユーザーID
            encrypted_data: Base64エンコードされた暗号文
            nonce: Base64エンコードされたnonce
        """

    @abstractmethod
    async def load_blob(self, user_id: str) -> EncryptedBlob | None:
        """
        暗号化されたBlobを読み込み

        Args:
            user_id: ユーザーID

        Returns:
            EncryptedBlob | None: 暗号化されたBlob（存在しない場合None）
        """

    @abstractmethod
    async def delete_blob(self, user_id: str) -> bool:
        """
        Blobを削除

        Args:
            user_id: ユーザーID

        Returns:
            bool: 削除成功したか
        """

    @abstractmethod
    async def blob_exists(self, user_id: str) -> bool:
        """
        Blobが存在するかチェック

        Args:
            user_id: ユーザーID

        Returns:
            bool: 存在するか
        """
