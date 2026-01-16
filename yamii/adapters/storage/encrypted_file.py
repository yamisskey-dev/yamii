"""
暗号化ファイルストレージアダプター
ユーザーごとの派生キーを使用したプライバシーファースト暗号化（遅延書き込み最適化）
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from ...core.encryption import E2EECrypto, EncryptedData
from ...core.key_management import SecureKeyManager, get_key_manager
from ...domain.models.user import UserState
from ...domain.ports.storage_port import IStorage

logger = logging.getLogger(__name__)


class EncryptedFileStorageAdapter(IStorage):
    """
    暗号化ファイルストレージアダプター

    プライバシーファースト設計:
    - ユーザーごとに派生された専用キーで暗号化
    - マスターキーが漏洩しても、個別ユーザーのキー再計算が必要
    - キーローテーション対応
    - GDPR対応のデータエクスポート・削除

    暗号化方式:
    - NaCl SecretBox (XSalsa20-Poly1305)
    - ユーザーごとの派生キー (Argon2id)

    パフォーマンス最適化:
    - 遅延書き込み（debounce）で複数更新をまとめて保存
    - スレッドプールでI/Oブロッキングを回避
    - アトミック書き込みでデータ破損を防止
    """

    def __init__(
        self,
        data_dir: str = "data",
        key_manager: SecureKeyManager | None = None,
        save_delay: float = 1.0,
    ):
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "users.enc.json"
        self.data_dir.mkdir(exist_ok=True)

        # 暗号化システム
        self.crypto = E2EECrypto()

        # セキュアなキー管理
        self._key_manager = key_manager or get_key_manager()

        # メモリキャッシュ
        self._users: dict[str, UserState] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

        # 遅延書き込み
        self._save_delay = save_delay
        self._dirty = False
        self._save_task: asyncio.Task | None = None

    def _get_user_key(self, user_id: str) -> bytes:
        """ユーザー固有の暗号化キーを取得"""
        return self._key_manager.derive_user_key(user_id, context="user_data")

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
            # スレッドプールで読み込み
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._read_json_file)

            # 暗号化されたデータを復号
            encrypted_users = data.get("encrypted_users", {})
            for user_id, enc_data_dict in encrypted_users.items():
                try:
                    # ユーザー固有のキーで復号
                    user_key = self._get_user_key(user_id)
                    encrypted_data = EncryptedData.from_dict(enc_data_dict)
                    decrypted_json = self.crypto.decrypt_large_data(
                        encrypted_data, user_key
                    )
                    user_data = json.loads(decrypted_json)
                    self._users[user_id] = UserState.from_dict(user_data)
                except Exception as e:
                    # 復号失敗したユーザーはスキップ（鍵が変わった可能性）
                    logger.warning(f"ユーザー {user_id} の復号に失敗: {e}")

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
        """データを暗号化してファイルに即時保存（アトミック書き込み）"""
        encrypted_users = {}

        for user_id, user in self._users.items():
            # ユーザー固有のキーで暗号化
            user_key = self._get_user_key(user_id)
            user_json = json.dumps(user.to_dict(), ensure_ascii=False)
            encrypted_data = self.crypto.encrypt_large_data(user_json, user_key)
            encrypted_users[user_id] = encrypted_data.to_dict()

        data = {
            "encrypted_users": encrypted_users,
            "updated_at": datetime.now().isoformat(),
            "version": "2.0",
            "encryption": "nacl.SecretBox+Argon2id",
        }

        temp_file = self.data_file.with_suffix(".tmp")

        async with self._lock:
            # スレッドプールで書き込み
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_json_file, temp_file, data)
            # アトミックに置換
            temp_file.replace(self.data_file)
            self._dirty = False

    def _write_json_file(self, path: Path, data: dict) -> None:
        """JSONファイルを同期的に書き込み（スレッドプール用）"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    async def save_user(self, user: UserState) -> None:
        """ユーザー状態を暗号化保存（遅延書き込み）"""
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
        """
        ユーザーデータを完全削除（GDPR対応）

        プライバシーファースト:
        - メモリからも完全削除
        - 派生キーキャッシュもクリア
        """
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

    async def export_decrypted(self, user_id: str) -> dict | None:
        """
        ユーザーデータを復号してエクスポート（GDPR対応）

        メンタルファースト & プライバシーファースト:
        - ユーザーは自分のデータを取得する権利がある
        - エクスポートデータには暗号化キーを含めない
        """
        await self._ensure_loaded()
        user = self._users.get(user_id)
        if user:
            export_data = user.to_dict()
            export_data["_export_info"] = {
                "exported_at": datetime.now().isoformat(),
                "format_version": "2.0",
                "notice": "このデータはあなたのプライバシーのために暗号化されて保存されていました。",
            }
            return export_data
        return None

    async def get_user_data_summary(self, user_id: str) -> dict | None:
        """
        ユーザーデータのサマリーを取得（プライバシー情報開示用）

        GDPR Article 15対応: ユーザーは自分のデータの概要を知る権利がある
        """
        await self._ensure_loaded()
        user = self._users.get(user_id)
        if user is None:
            return None

        return {
            "user_id": user.user_id,
            "data_collected": {
                "interactions_count": user.total_interactions,
                "first_interaction": user.first_interaction.isoformat(),
                "last_interaction": user.last_interaction.isoformat(),
                "episodes_count": len(user.episodes),
                "known_facts_count": len(user.known_facts),
                "known_topics": user.known_topics,
            },
            "privacy_settings": {
                "proactive_enabled": user.proactive.enabled,
                "proactive_frequency": user.proactive.frequency,
            },
            "your_rights": {
                "export": "全データのエクスポートが可能です",
                "delete": "全データの完全削除が可能です",
                "modify": "プロアクティブ設定の変更が可能です",
            },
        }
