"""
ファイルストレージアダプター
JSONファイルベースのデータ永続化
"""

import json
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ...domain.ports.storage_port import IStorage
from ...domain.models.user import UserState


class FileStorageAdapter(IStorage):
    """
    ファイルストレージアダプター

    JSONファイルを使用したシンプルな永続化実装。
    開発・小規模運用向け。
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "users.json"
        self.data_dir.mkdir(exist_ok=True)

        # メモリキャッシュ
        self._users: dict[str, UserState] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        """データが読み込まれていることを保証"""
        if not self._loaded:
            async with self._lock:
                if not self._loaded:
                    await self._load_data()
                    self._loaded = True

    async def _load_data(self) -> None:
        """ファイルからデータを読み込み"""
        if not self.data_file.exists():
            self._users = {}
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for user_id, user_data in data.get("users", {}).items():
                    self._users[user_id] = UserState.from_dict(user_data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"データ読み込みエラー: {e}")
            self._users = {}

    async def _save_data(self) -> None:
        """ファイルにデータを保存"""
        data = {
            "users": {uid: u.to_dict() for uid, u in self._users.items()},
            "updated_at": datetime.now().isoformat(),
        }

        async with self._lock:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    async def save_user(self, user: UserState) -> None:
        """ユーザー状態を保存"""
        await self._ensure_loaded()
        user.updated_at = datetime.now()
        self._users[user.user_id] = user
        await self._save_data()

    async def load_user(self, user_id: str) -> Optional[UserState]:
        """ユーザー状態を読み込み"""
        await self._ensure_loaded()
        return self._users.get(user_id)

    async def delete_user(self, user_id: str) -> bool:
        """ユーザーデータを削除"""
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
