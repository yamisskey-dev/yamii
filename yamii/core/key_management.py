"""
プライバシーファースト: セキュアなキー管理システム

- ユーザーごとの暗号化キー派生
- マスターキーからユーザーキーを安全に導出
- キーローテーション対応
"""

import os
import base64
import hashlib
import hmac
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import nacl.secret
import nacl.utils
from nacl.pwhash import argon2id


@dataclass
class DerivedKey:
    """派生されたユーザーキー"""
    user_id: str
    key: bytes
    key_id: str  # キー識別子（ローテーション用）
    created_at: datetime


class SecureKeyManager:
    """
    セキュアなキー管理

    プライバシーファースト原則:
    - マスターキーからユーザーごとの暗号化キーを派生
    - Argon2idによるメモリハード関数でブルートフォース耐性
    - キーは絶対にログ出力しない
    - メモリからのキー消去を可能な限り実行
    """

    # Argon2idパラメータ（セキュリティ重視）
    OPSLIMIT = argon2id.OPSLIMIT_MODERATE
    MEMLIMIT = argon2id.MEMLIMIT_MODERATE

    def __init__(
        self,
        master_key: Optional[bytes] = None,
        key_file: str = ".yamii_master_key",
    ):
        self._key_file = Path(key_file)
        self._master_key = master_key or self._load_or_create_master_key()
        self._derived_keys: dict[str, DerivedKey] = {}

    def _load_or_create_master_key(self) -> bytes:
        """マスターキーを読み込みまたは生成（安全な方法で）"""
        # 環境変数から取得（推奨: Secrets Manager経由で注入）
        env_key = os.environ.get("YAMII_MASTER_KEY")
        if env_key:
            return base64.b64decode(env_key)

        # ファイルから取得
        if self._key_file.exists():
            # パーミッション確認
            mode = self._key_file.stat().st_mode & 0o777
            if mode != 0o600:
                raise PermissionError(
                    f"マスターキーファイルのパーミッションが危険です: {oct(mode)}。0o600にしてください。"
                )
            with open(self._key_file, "r") as f:
                return base64.b64decode(f.read().strip())

        # 新規生成（32バイト = 256ビット）
        new_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)

        # 安全なファイル書き込み（umaskを一時的に変更）
        old_umask = os.umask(0o077)
        try:
            with open(self._key_file, "w") as f:
                f.write(base64.b64encode(new_key).decode("utf-8"))
            os.chmod(self._key_file, 0o600)
        finally:
            os.umask(old_umask)

        return new_key

    def derive_user_key(self, user_id: str, context: str = "user_data") -> bytes:
        """
        ユーザーIDから専用の暗号化キーを派生

        Args:
            user_id: ユーザーID
            context: キーの用途（異なる用途に異なるキーを派生）

        Returns:
            32バイトの派生キー
        """
        cache_key = f"{user_id}:{context}"

        if cache_key in self._derived_keys:
            return self._derived_keys[cache_key].key

        # ユーザーID + コンテキスト から salt を生成
        salt_input = f"yamii:{user_id}:{context}".encode("utf-8")
        salt = hashlib.sha256(salt_input).digest()[:16]  # 16バイト salt

        # Argon2idでキー派生
        derived = argon2id.kdf(
            size=nacl.secret.SecretBox.KEY_SIZE,
            password=self._master_key,
            salt=salt,
            opslimit=self.OPSLIMIT,
            memlimit=self.MEMLIMIT,
        )

        # キーIDを生成（ローテーション追跡用）
        key_id = hashlib.sha256(derived).hexdigest()[:16]

        self._derived_keys[cache_key] = DerivedKey(
            user_id=user_id,
            key=derived,
            key_id=key_id,
            created_at=datetime.now(),
        )

        return derived

    def derive_conversation_key(self, user_id: str, session_id: str) -> bytes:
        """
        会話ごとの暗号化キーを派生（前方秘匿性）

        各セッションで異なるキーを使用することで、
        一つのキーが漏洩しても他のセッションは保護される。
        """
        return self.derive_user_key(user_id, context=f"session:{session_id}")

    def clear_cached_keys(self) -> None:
        """キャッシュされたキーをクリア（メモリ保護）"""
        # Python ではメモリの完全消去は保証されないが、参照を削除
        self._derived_keys.clear()

    def rotate_master_key(self, new_key: bytes) -> Tuple[bytes, bytes]:
        """
        マスターキーをローテーション

        Returns:
            (old_key, new_key) - データ再暗号化に使用
        """
        old_key = self._master_key
        self._master_key = new_key
        self._derived_keys.clear()  # 派生キーキャッシュをクリア

        # 新しいキーをファイルに保存
        old_umask = os.umask(0o077)
        try:
            with open(self._key_file, "w") as f:
                f.write(base64.b64encode(new_key).decode("utf-8"))
            os.chmod(self._key_file, 0o600)
        finally:
            os.umask(old_umask)

        return old_key, new_key

    def generate_export_key(self, user_id: str) -> Tuple[bytes, str]:
        """
        GDPR対応: データエクスポート用の一時キーを生成

        Returns:
            (key, key_b64) - ユーザーに渡すためのキー
        """
        export_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        key_b64 = base64.b64encode(export_key).decode("utf-8")
        return export_key, key_b64


# グローバルインスタンス（遅延初期化）
_key_manager: Optional[SecureKeyManager] = None


def get_key_manager() -> SecureKeyManager:
    """グローバルキーマネージャーを取得"""
    global _key_manager
    if _key_manager is None:
        _key_manager = SecureKeyManager()
    return _key_manager
