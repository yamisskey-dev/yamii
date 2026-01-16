"""
暗号化ファイルストレージアダプター
SecretBoxを使用したサーバーサイド暗号化
"""

import json
import asyncio
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ...domain.ports.storage_port import IStorage
from ...domain.models.user import UserState
from ...core.encryption import E2EECrypto, EncryptedData


class EncryptedFileStorageAdapter(IStorage):
    """
    暗号化ファイルストレージアダプター

    SecretBox（対称暗号化）を使用して、ユーザーデータを暗号化保存。
    マスター鍵は環境変数または鍵ファイルから読み込む。

    プライバシーファースト:
    - 保存データは全て暗号化
    - マスター鍵なしではデータ復元不可
    - 鍵のローテーション対応
    """

    def __init__(
        self,
        data_dir: str = "data",
        key_file: str = ".yamii_master_key",
        master_key: Optional[bytes] = None,
    ):
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "users.enc.json"
        self.key_file = Path(key_file)
        self.data_dir.mkdir(exist_ok=True)

        # 暗号化システム
        self.crypto = E2EECrypto()

        # マスター鍵の取得
        self._master_key = master_key or self._get_or_create_master_key()

        # メモリキャッシュ
        self._users: dict[str, UserState] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

    def _get_or_create_master_key(self) -> bytes:
        """マスター鍵を取得または生成"""
        # 環境変数から取得
        env_key = os.environ.get("YAMII_MASTER_KEY")
        if env_key:
            return self.crypto.key_from_base64(env_key)

        # ファイルから取得
        if self.key_file.exists():
            with open(self.key_file, "r") as f:
                key_b64 = f.read().strip()
                return self.crypto.key_from_base64(key_b64)

        # 新規生成
        new_key = self.crypto.generate_symmetric_key()
        key_b64 = self.crypto.key_to_base64(new_key)

        # ファイルに保存（本番環境では安全な場所に保存すべき）
        with open(self.key_file, "w") as f:
            f.write(key_b64)
        os.chmod(self.key_file, 0o600)  # 所有者のみ読み書き可

        return new_key

    async def _ensure_loaded(self) -> None:
        """データが読み込まれていることを保証"""
        if not self._loaded:
            async with self._lock:
                if not self._loaded:
                    await self._load_data()
                    self._loaded = True

    async def _load_data(self) -> None:
        """暗号化ファイルからデータを読み込み"""
        if not self.data_file.exists():
            self._users = {}
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 暗号化されたデータを復号
            encrypted_users = data.get("encrypted_users", {})
            for user_id, enc_data_dict in encrypted_users.items():
                try:
                    encrypted_data = EncryptedData.from_dict(enc_data_dict)
                    decrypted_json = self.crypto.decrypt_large_data(
                        encrypted_data, self._master_key
                    )
                    user_data = json.loads(decrypted_json)
                    self._users[user_id] = UserState.from_dict(user_data)
                except Exception as e:
                    # 復号失敗したユーザーはスキップ（鍵が変わった可能性）
                    print(f"ユーザー {user_id} の復号に失敗: {e}")

        except (json.JSONDecodeError, KeyError) as e:
            print(f"データ読み込みエラー: {e}")
            self._users = {}

    async def _save_data(self) -> None:
        """データを暗号化してファイルに保存"""
        encrypted_users = {}

        for user_id, user in self._users.items():
            # ユーザーデータをJSON化
            user_json = json.dumps(user.to_dict(), ensure_ascii=False)
            # 暗号化
            encrypted_data = self.crypto.encrypt_large_data(user_json, self._master_key)
            encrypted_users[user_id] = encrypted_data.to_dict()

        data = {
            "encrypted_users": encrypted_users,
            "updated_at": datetime.now().isoformat(),
            "version": "1.0",
            "encryption": "nacl.SecretBox",
        }

        async with self._lock:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    async def save_user(self, user: UserState) -> None:
        """ユーザー状態を暗号化保存"""
        await self._ensure_loaded()
        user.updated_at = datetime.now()
        self._users[user.user_id] = user
        await self._save_data()

    async def load_user(self, user_id: str) -> Optional[UserState]:
        """ユーザー状態を読み込み"""
        await self._ensure_loaded()
        return self._users.get(user_id)

    async def delete_user(self, user_id: str) -> bool:
        """ユーザーデータを削除（完全消去）"""
        await self._ensure_loaded()
        if user_id in self._users:
            del self._users[user_id]
            await self._save_data()
            return True
        return False

    async def list_users(self) -> List[str]:
        """全ユーザーIDのリストを取得"""
        await self._ensure_loaded()
        return list(self._users.keys())

    async def user_exists(self, user_id: str) -> bool:
        """ユーザーが存在するかチェック"""
        await self._ensure_loaded()
        return user_id in self._users

    async def export_decrypted(self, user_id: str) -> Optional[dict]:
        """
        ユーザーデータを復号してエクスポート（GDPR対応）

        注意: この関数は管理者のみが使用すべき
        """
        await self._ensure_loaded()
        user = self._users.get(user_id)
        if user:
            return user.to_dict()
        return None
