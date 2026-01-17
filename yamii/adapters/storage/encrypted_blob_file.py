"""
暗号化Blobファイルストレージアダプター
Zero-Knowledge アーキテクチャ用

クライアントから受け取った暗号化Blobをそのままファイルに保存する。
サーバーは内容を復号せず、暗号文として保存するのみ。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ...core.logging import get_logger
from ...domain.ports.encrypted_blob_storage_port import (
    EncryptedBlob,
    IEncryptedBlobStorage,
)

logger = get_logger(__name__)


class EncryptedBlobFileAdapter(IEncryptedBlobStorage):
    """
    Zero-Knowledge 暗号化Blobファイルストレージ

    クライアント側で暗号化されたデータをそのままJSONファイルとして保存。
    サーバーは暗号文を保存するのみで、復号は行わない。
    """

    def __init__(self, data_dir: str = "data/blobs"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"EncryptedBlobFileAdapter initialized: {self.data_dir}")

    def _get_blob_path(self, user_id: str) -> Path:
        """ユーザーのBlobファイルパスを取得"""
        # ユーザーIDをファイル名として安全に使用
        safe_id = user_id.replace("/", "_").replace("\\", "_")
        return self.data_dir / f"{safe_id}.blob.json"

    async def save_blob(self, user_id: str, encrypted_data: str, nonce: str) -> None:
        """暗号化されたBlobを保存"""
        blob_path = self._get_blob_path(user_id)
        now = datetime.now()

        # 既存のBlobがあれば作成日時を保持
        existing = await self.load_blob(user_id)
        created_at = existing.created_at if existing else now

        blob = EncryptedBlob(
            user_id=user_id,
            data=encrypted_data,
            nonce=nonce,
            created_at=created_at,
            updated_at=now,
        )

        blob_path.write_text(json.dumps(blob.to_dict(), ensure_ascii=False, indent=2))
        logger.debug(f"Saved encrypted blob for user: {user_id}")

    async def load_blob(self, user_id: str) -> EncryptedBlob | None:
        """暗号化されたBlobを読み込み"""
        blob_path = self._get_blob_path(user_id)

        if not blob_path.exists():
            return None

        try:
            data = json.loads(blob_path.read_text())
            return EncryptedBlob.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load blob for user {user_id}: {e}")
            return None

    async def delete_blob(self, user_id: str) -> bool:
        """Blobを削除"""
        blob_path = self._get_blob_path(user_id)

        if blob_path.exists():
            blob_path.unlink()
            logger.info(f"Deleted blob for user: {user_id}")
            return True

        return False

    async def blob_exists(self, user_id: str) -> bool:
        """Blobが存在するかチェック"""
        return self._get_blob_path(user_id).exists()
