"""
ファイルストレージアダプター
JSONファイルベースのデータ永続化（遅延書き込み最適化）
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from ...core.logging import get_logger
from ...domain.models.user import UserState
from ...domain.ports.storage_port import IStorage

logger = get_logger(__name__)


class FileStorageAdapter(IStorage):
    """
    ファイルストレージアダプター

    JSONファイルを使用したシンプルな永続化実装。
    遅延書き込み（debounce）で複数更新をまとめて保存。
    """

    def __init__(self, data_dir: str = "data", save_delay: float = 1.0):
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "users.json"
        self.data_dir.mkdir(exist_ok=True)

        # メモリキャッシュ
        self._users: dict[str, UserState] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

        # 遅延書き込み
        self._save_delay = save_delay
        self._dirty = False
        self._save_task: asyncio.Task | None = None

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
            # 大きなファイルはスレッドプールで処理
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, self._read_json_file)
            for user_id, user_data in data.get("users", {}).items():
                self._users[user_id] = UserState.from_dict(user_data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"データ読み込みエラー: {e}")
            self._users = {}

    def _read_json_file(self) -> dict:
        """JSONファイルを同期的に読み込み（スレッドプール用）"""
        with open(self.data_file, encoding="utf-8") as f:
            return json.load(f)

    async def _schedule_save(self) -> None:
        """遅延書き込みをスケジュール"""
        self._dirty = True

        # 既存のタスクがあればキャンセル
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass

        # 新しい遅延保存タスクを作成
        self._save_task = asyncio.create_task(self._delayed_save())

    async def _delayed_save(self) -> None:
        """遅延後に保存を実行"""
        await asyncio.sleep(self._save_delay)
        if self._dirty:
            await self._save_data_now()

    async def _save_data_now(self) -> None:
        """ファイルにデータを即時保存（アトミック書き込み）"""
        data = {
            "users": {uid: u.to_dict() for uid, u in self._users.items()},
            "updated_at": datetime.now().isoformat(),
        }

        temp_file = self.data_file.with_suffix(".tmp")

        async with self._lock:
            # スレッドプールで書き込み
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._write_json_file, temp_file, data)
            # アトミックに置換
            temp_file.replace(self.data_file)
            self._dirty = False

    def _write_json_file(self, path: Path, data: dict) -> None:
        """JSONファイルを同期的に書き込み（スレッドプール用）"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    async def save_user(self, user: UserState) -> None:
        """ユーザー状態を保存（遅延書き込み）"""
        await self._ensure_loaded()
        user.updated_at = datetime.now()
        self._users[user.user_id] = user
        await self._schedule_save()

    async def load_user(self, user_id: str) -> UserState | None:
        """ユーザー状態を読み込み"""
        await self._ensure_loaded()
        return self._users.get(user_id)

    async def load_users(self, user_ids: list[str]) -> dict[str, UserState]:
        """複数ユーザーを一括読み込み"""
        await self._ensure_loaded()
        return {uid: self._users[uid] for uid in user_ids if uid in self._users}

    async def delete_user(self, user_id: str) -> bool:
        """ユーザーデータを削除"""
        await self._ensure_loaded()
        if user_id in self._users:
            del self._users[user_id]
            await self._schedule_save()
            return True
        return False

    async def list_users(self) -> list[str]:
        """全ユーザーIDのリストを取得"""
        await self._ensure_loaded()
        return list(self._users.keys())

    async def user_exists(self, user_id: str) -> bool:
        """ユーザーが存在するかチェック"""
        await self._ensure_loaded()
        return user_id in self._users

    async def flush(self) -> None:
        """保留中の書き込みを強制実行"""
        if self._dirty:
            if self._save_task and not self._save_task.done():
                self._save_task.cancel()
            await self._save_data_now()
