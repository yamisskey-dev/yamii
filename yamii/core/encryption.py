#!/usr/bin/env python3
"""
E2EE（End-to-End Encryption）暗号化システム
PyNaClとcryptographyを活用したゼロナレッジアーキテクチャ
"""

import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import nacl.secret
import nacl.utils
from nacl.public import Box, PrivateKey, PublicKey

logger = logging.getLogger(__name__)


@dataclass
class EncryptedData:
    """暗号化されたデータの構造"""
    ciphertext: bytes
    nonce: bytes
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換（データベース保存用）"""
        return {
            'ciphertext': base64.b64encode(self.ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(self.nonce).decode('utf-8'),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'EncryptedData':
        """辞書から復元"""
        return cls(
            ciphertext=base64.b64decode(data['ciphertext']),
            nonce=base64.b64decode(data['nonce']),
            metadata=data['metadata']
        )


class E2EECrypto:
    """
    エンドツーエンド暗号化システム

    特徴:
    - PyNaClによる高速なBox暗号化
    - クライアントサイドでのキーペア生成
    - サーバーは暗号化されたデータのみ保存（ゼロナレッジ）
    - 前方秘匿性対応
    """

    def __init__(self):
        self.logger = logger

    def generate_key_pair(self) -> tuple[bytes, bytes]:
        """
        Ed25519キーペアを生成（クライアントサイドで実行）

        Returns:
            Tuple[bytes, bytes]: (public_key, private_key)
        """
        try:
            # PyNaClを使用したキーペア生成
            private_key = PrivateKey.generate()
            public_key = private_key.public_key

            # バイト形式で返す
            return (
                public_key.encode(),  # 公開鍵 (32 bytes)
                private_key.encode()  # 秘密鍵 (32 bytes)
            )

        except Exception as e:
            self.logger.error(f"キーペア生成エラー: {e}")
            raise

    def encrypt(self, plaintext: str, public_key: bytes) -> EncryptedData:
        """
        テキストを公開鍵で暗号化

        Args:
            plaintext: 暗号化するテキスト
            public_key: 受信者の公開鍵

        Returns:
            EncryptedData: 暗号化されたデータ
        """
        try:
            # 公開鍵を復元
            recipient_public_key = PublicKey(public_key)

            # 送信者の一時キーペア生成（前方秘匿性）
            sender_private_key = PrivateKey.generate()

            # BoxでE2EE暗号化
            box = Box(sender_private_key, recipient_public_key)

            # プレインテキストをUTF-8でエンコード
            plaintext_bytes = plaintext.encode('utf-8')

            # 暗号化（nonceは自動生成される）
            encrypted = box.encrypt(plaintext_bytes)

            # 暗号化データから成分を分離
            nonce = encrypted.nonce
            ciphertext = encrypted.ciphertext

            # メタデータ
            metadata = {
                'sender_public_key': base64.b64encode(sender_private_key.public_key.encode()).decode('utf-8'),
                'algorithm': 'nacl.Box',
                'version': '1.0',
                'timestamp': str(int(os.urandom(4).hex(), 16))  # タイムスタンプ的な値
            }

            return EncryptedData(
                ciphertext=ciphertext,
                nonce=nonce,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"暗号化エラー: {e}")
            raise

    def decrypt(self, encrypted_data: EncryptedData, private_key: bytes) -> str:
        """
        暗号化データを秘密鍵で復号

        Args:
            encrypted_data: 暗号化されたデータ
            private_key: 受信者の秘密鍵

        Returns:
            str: 復号されたテキスト
        """
        try:
            # 秘密鍵を復元
            recipient_private_key = PrivateKey(private_key)

            # 送信者の公開鍵を取得
            sender_public_key_bytes = base64.b64decode(
                encrypted_data.metadata['sender_public_key']
            )
            sender_public_key = PublicKey(sender_public_key_bytes)

            # Boxで復号
            box = Box(recipient_private_key, sender_public_key)

            # 暗号化データを復元
            from nacl.utils import EncryptedMessage
            # PyNaClのEncryptedMessageは nonce + ciphertext の順序
            encrypted_message = EncryptedMessage(
                encrypted_data.nonce + encrypted_data.ciphertext
            )

            # 復号
            decrypted_bytes = box.decrypt(encrypted_message)

            # UTF-8でデコード
            return decrypted_bytes.decode('utf-8')

        except Exception as e:
            self.logger.error(f"復号エラー: {e}")
            raise

    def generate_symmetric_key(self) -> bytes:
        """
        対称鍵を生成（大きなデータ用）

        Returns:
            bytes: 32バイトの対称鍵
        """
        return nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)

    def encrypt_large_data(self, data: str, symmetric_key: bytes) -> EncryptedData:
        """
        大きなデータを対称鍵で暗号化

        Args:
            data: 暗号化するデータ
            symmetric_key: 対称鍵

        Returns:
            EncryptedData: 暗号化されたデータ
        """
        try:
            # SecretBoxで高速対称暗号化
            secret_box = nacl.secret.SecretBox(symmetric_key)

            # データをUTF-8でエンコード
            data_bytes = data.encode('utf-8')

            # 暗号化
            encrypted = secret_box.encrypt(data_bytes)

            metadata = {
                'algorithm': 'nacl.SecretBox',
                'version': '1.0',
                'size': len(data_bytes)
            }

            return EncryptedData(
                ciphertext=encrypted.ciphertext,
                nonce=encrypted.nonce,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"対称暗号化エラー: {e}")
            raise

    def decrypt_large_data(self, encrypted_data: EncryptedData, symmetric_key: bytes) -> str:
        """
        対称鍵で暗号化されたデータを復号

        Args:
            encrypted_data: 暗号化されたデータ
            symmetric_key: 対称鍵

        Returns:
            str: 復号されたデータ
        """
        try:
            # SecretBoxで復号
            secret_box = nacl.secret.SecretBox(symmetric_key)

            # EncryptedMessageを復元
            from nacl.utils import EncryptedMessage
            # PyNaClのEncryptedMessageは nonce + ciphertext の順序
            encrypted_message = EncryptedMessage(
                encrypted_data.nonce + encrypted_data.ciphertext
            )

            # 復号
            decrypted_bytes = secret_box.decrypt(encrypted_message)

            return decrypted_bytes.decode('utf-8')

        except Exception as e:
            self.logger.error(f"対称復号エラー: {e}")
            raise

    def key_to_base64(self, key: bytes) -> str:
        """キーをBase64文字列に変換"""
        return base64.b64encode(key).decode('utf-8')

    def key_from_base64(self, key_str: str) -> bytes:
        """Base64文字列からキーを復元"""
        return base64.b64decode(key_str)


class KeyManager:
    """
    クライアントサイドキー管理システム
    """

    def __init__(self, storage_path: str = ".yamii_keys"):
        self.storage_path = storage_path
        self.e2ee = E2EECrypto()

    def generate_and_save_keys(self, user_id: str) -> tuple[str, str]:
        """
        新しいキーペアを生成して保存

        Args:
            user_id: ユーザーID

        Returns:
            Tuple[str, str]: (public_key_b64, private_key_b64)
        """
        try:
            # キーペア生成
            public_key, private_key = self.e2ee.generate_key_pair()

            # Base64エンコード
            public_key_b64 = self.e2ee.key_to_base64(public_key)
            private_key_b64 = self.e2ee.key_to_base64(private_key)

            # ローカル保存（実際の実装では安全な場所に保存）
            key_data = {
                'user_id': user_id,
                'public_key': public_key_b64,
                'private_key': private_key_b64,
                'created_at': str(int(os.urandom(4).hex(), 16))
            }

            os.makedirs(self.storage_path, exist_ok=True)
            key_file = os.path.join(self.storage_path, f"{user_id}.json")

            with open(key_file, 'w') as f:
                json.dump(key_data, f)

            logger.info(f"キーペアを生成・保存: {user_id}")

            return public_key_b64, private_key_b64

        except Exception as e:
            logger.error(f"キー生成・保存エラー: {e}")
            raise

    def load_keys(self, user_id: str) -> tuple[str, str] | None:
        """
        保存されたキーペアを読み込み

        Args:
            user_id: ユーザーID

        Returns:
            Optional[Tuple[str, str]]: (public_key_b64, private_key_b64) or None
        """
        try:
            key_file = os.path.join(self.storage_path, f"{user_id}.json")

            if not os.path.exists(key_file):
                return None

            with open(key_file) as f:
                key_data = json.load(f)

            return key_data['public_key'], key_data['private_key']

        except Exception as e:
            logger.error(f"キー読み込みエラー: {e}")
            return None


# グローバルインスタンス
_global_e2ee: E2EECrypto | None = None
_global_key_manager: KeyManager | None = None


def get_e2ee_crypto() -> E2EECrypto:
    """グローバルE2EE暗号化インスタンスを取得"""
    global _global_e2ee

    if _global_e2ee is None:
        _global_e2ee = E2EECrypto()

    return _global_e2ee


def get_key_manager() -> KeyManager:
    """グローバルキーマネージャーインスタンスを取得"""
    global _global_key_manager

    if _global_key_manager is None:
        _global_key_manager = KeyManager()

    return _global_key_manager
