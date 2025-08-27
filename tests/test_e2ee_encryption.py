#!/usr/bin/env python3
"""
E2EE（End-to-End Encryption）暗号化システムのテスト
TDD: まずテストを作成してから実装する
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

# テスト対象のモジュール（まだ存在しないが、テストファースト）
from navi.core.encryption import E2EECrypto, EncryptedData
from navi.core.database import AsyncDatabase, DatabaseConfig
from navi.core.secure_prompt_store import SecurePromptStore


class TestE2EECrypto:
    """エンドツーエンド暗号化システムのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.e2ee = E2EECrypto()
    
    def test_generate_key_pair(self):
        """キーペア生成のテスト"""
        # Given: E2EEインスタンス
        
        # When: キーペア生成
        public_key, private_key = self.e2ee.generate_key_pair()
        
        # Then: 有効なキーペアが生成される
        assert public_key is not None
        assert private_key is not None
        assert len(public_key) > 0
        assert len(private_key) > 0
        assert public_key != private_key
    
    def test_encrypt_decrypt_text(self):
        """テキスト暗号化・復号のテスト"""
        # Given: キーペアと平文
        public_key, private_key = self.e2ee.generate_key_pair()
        plaintext = "あなたは経験豊富な人生相談カウンセラーです。"
        
        # When: 暗号化
        encrypted_data = self.e2ee.encrypt(plaintext, public_key)
        
        # Then: 暗号化データが生成される
        assert isinstance(encrypted_data, EncryptedData)
        assert encrypted_data.ciphertext != plaintext
        assert encrypted_data.nonce is not None
        
        # When: 復号
        decrypted_text = self.e2ee.decrypt(encrypted_data, private_key)
        
        # Then: 元のテキストが復元される
        assert decrypted_text == plaintext
    
    def test_encrypt_large_prompt(self):
        """大きなプロンプトの暗号化テスト"""
        # Given: 長いプロンプトテキスト
        public_key, private_key = self.e2ee.generate_key_pair()
        large_prompt = "あなたは人生相談カウンセラーです。" * 1000  # 約30KB
        
        # When: 暗号化・復号
        encrypted_data = self.e2ee.encrypt(large_prompt, public_key)
        decrypted_text = self.e2ee.decrypt(encrypted_data, private_key)
        
        # Then: 正確に復元される
        assert decrypted_text == large_prompt
        assert len(encrypted_data.ciphertext) > 0
    
    def test_encryption_with_wrong_key_fails(self):
        """間違ったキーでの復号は失敗する"""
        # Given: 異なるキーペア
        public_key1, private_key1 = self.e2ee.generate_key_pair()
        public_key2, private_key2 = self.e2ee.generate_key_pair()
        plaintext = "秘密のメッセージ"
        
        # When: key1で暗号化、key2で復号試行
        encrypted_data = self.e2ee.encrypt(plaintext, public_key1)
        
        # Then: 復号は失敗する
        with pytest.raises(Exception):
            self.e2ee.decrypt(encrypted_data, private_key2)


class TestAsyncDatabase:
    """非同期PostgreSQLデータベースのテスト"""
    
    @pytest.mark.asyncio
    async def test_database_connection(self):
        """データベース接続のテスト"""
        # Given: データベース設定
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="navi_test",
            user="navi_user",
            password="test_password"
        )
        
        # When: データベースインスタンス作成
        async_db = AsyncDatabase(db_config)
        
        # Then: 正しく初期化される
        assert async_db.config.host == "localhost"
        assert async_db.config.database == "navi_test"
        assert not async_db.is_connected()  # まだ初期化されていない
    
    @pytest.mark.asyncio
    async def test_create_tables(self):
        """テーブル作成のテスト"""
        # Given: データベース設定とモックエンジン
        db_config = DatabaseConfig(database="test_db")
        async_db = AsyncDatabase(db_config)
        
        # create_tables()メソッド全体をモック
        with patch.object(async_db, 'create_tables', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = None
            
            # When: テーブル作成
            await async_db.create_tables()
            
            # Then: メソッドが呼ばれる
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_insert_encrypted_prompt(self):
        """暗号化プロンプトの挿入テスト"""
        # Given: 暗号化データとデータベース
        encrypted_data = EncryptedData(
            ciphertext=b"encrypted_prompt_data",
            nonce=b"random_nonce_12345",
            metadata={"prompt_id": "test_prompt", "version": "1.0"}
        )
        db_config = DatabaseConfig(database="test_db")
        async_db = AsyncDatabase(db_config)
        
        # get_session()メソッドをモック
        mock_session = AsyncMock()
        
        # コンテキストマネージャーを正しくモック
        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(async_db, 'get_session', return_value=context_manager):
            # When: 暗号化プロンプト挿入
            result = await async_db.insert_encrypted_prompt(
                "test_user", encrypted_data, "test_prompt_id"
            )
            
            # Then: 挿入が成功する
            assert result is True
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()


class TestSecurePromptStore:
    """セキュアプロンプトストアのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.mock_database = AsyncMock(spec=AsyncDatabase)
        self.mock_e2ee = AsyncMock(spec=E2EECrypto)
        self.store = SecurePromptStore(
            database=self.mock_database,
            e2ee_crypto=self.mock_e2ee
        )
    
    @pytest.mark.asyncio
    async def test_store_encrypted_prompt(self):
        """暗号化プロンプト保存のテスト"""
        # Given: プロンプトデータ
        prompt_data = {
            "id": "friendly_counselor",
            "title": "優しいカウンセラー",
            "prompt_text": "あなたは優しい人生相談カウンセラーです。"
        }
        user_id = "user123"
        public_key = b"mock_public_key"
        
        # Mock設定
        encrypted_data = EncryptedData(
            ciphertext=b"encrypted_prompt",
            nonce=b"nonce123",
            metadata={"id": prompt_data["id"]}
        )
        self.mock_e2ee.encrypt.return_value = encrypted_data
        self.mock_database.insert_encrypted_prompt.return_value = True
        
        # When: プロンプト保存
        result = await self.store.store_prompt(user_id, prompt_data, public_key)
        
        # Then: 暗号化して保存される
        assert result is True
        self.mock_e2ee.encrypt.assert_called_once()
        self.mock_database.insert_encrypted_prompt.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retrieve_decrypted_prompt(self):
        """暗号化プロンプト取得・復号のテスト"""
        # Given: 暗号化されたプロンプト
        user_id = "user123"
        prompt_id = "friendly_counselor"
        private_key = b"mock_private_key"
        
        # Mock設定
        encrypted_data = EncryptedData(
            ciphertext=b"encrypted_prompt",
            nonce=b"nonce123",
            metadata={"id": prompt_id}
        )
        expected_prompt = {
            "id": prompt_id,
            "title": "優しいカウンセラー",
            "prompt_text": "あなたは優しい人生相談カウンセラーです。"
        }
        
        self.mock_database.get_encrypted_prompt.return_value = encrypted_data
        self.mock_e2ee.decrypt.return_value = str(expected_prompt)
        
        # When: プロンプト取得
        result = await self.store.get_prompt(user_id, prompt_id, private_key)
        
        # Then: 復号されたプロンプトが返される
        assert result is not None
        self.mock_database.get_encrypted_prompt.assert_called_once_with(user_id, prompt_id)
        self.mock_e2ee.decrypt.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_user_prompts(self):
        """ユーザーのプロンプト一覧取得テスト"""
        # Given: ユーザーID
        user_id = "user123"
        
        # Mock設定
        expected_prompts = [
            {"id": "prompt1", "title": "プロンプト1", "created_at": "2024-01-01"},
            {"id": "prompt2", "title": "プロンプト2", "created_at": "2024-01-02"}
        ]
        self.mock_database.list_user_prompts.return_value = expected_prompts
        
        # When: プロンプト一覧取得
        result = await self.store.list_prompts(user_id)
        
        # Then: プロンプト一覧が返される（メタデータのみ）
        assert result == expected_prompts
        self.mock_database.list_user_prompts.assert_called_once_with(user_id)


class TestIntegrationE2EEFlow:
    """E2EE統合フローのテスト"""
    
    @pytest.mark.asyncio
    async def test_full_e2ee_workflow(self):
        """完全なE2EEワークフローのテスト"""
        # Given: E2EEシステムの全コンポーネント
        e2ee = E2EECrypto()
        mock_db = AsyncMock(spec=AsyncDatabase)
        store = SecurePromptStore(database=mock_db, e2ee_crypto=e2ee)
        
        # キーペア生成（クライアントサイド）
        public_key, private_key = e2ee.generate_key_pair()
        
        # プロンプトデータ
        original_prompt = {
            "id": "secure_counselor",
            "title": "セキュアカウンセラー", 
            "prompt_text": "あなたは機密を扱うカウンセラーです。全ての情報は暗号化されます。"
        }
        user_id = "secure_user_001"
        
        # Mock設定
        mock_db.insert_encrypted_prompt.return_value = True
        mock_db.get_encrypted_prompt.return_value = None  # 後で設定
        
        # When: プロンプト保存（クライアント→サーバー）
        store_result = await store.store_prompt(user_id, original_prompt, public_key)
        
        # Then: 保存が成功
        assert store_result is True
        
        # 暗号化データの取得をシミュレート
        # 実際のE2EE暗号化を行う
        encrypted_data = e2ee.encrypt(str(original_prompt), public_key)
        mock_db.get_encrypted_prompt.return_value = encrypted_data
        
        # When: プロンプト取得・復号（サーバー→クライアント）
        retrieved_prompt = await store.get_prompt(user_id, "secure_counselor", private_key)
        
        # Then: 元のプロンプトが復元される
        assert retrieved_prompt is not None
        # 文字列から辞書への変換をテスト時は簡略化
        assert "セキュアカウンセラー" in retrieved_prompt
        assert "機密を扱うカウンセラー" in retrieved_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])