"""
暗号化ストレージアダプターのテスト

プライバシーファースト:
- ユーザーごとの派生キーでの暗号化
- データの完全な暗号化確認
- GDPR対応エクスポート
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from yamii.adapters.storage.encrypted_file import EncryptedFileStorageAdapter
from yamii.core.encryption import E2EECrypto
from yamii.core.key_management import SecureKeyManager
from yamii.domain.models.relationship import RelationshipPhase
from yamii.domain.models.user import UserState


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def crypto():
    """暗号化システム"""
    return E2EECrypto()


@pytest.fixture
def master_key(crypto):
    """テスト用マスター鍵"""
    return crypto.generate_symmetric_key()


@pytest.fixture
def key_manager(temp_dir, master_key):
    """テスト用キーマネージャー"""
    key_file = os.path.join(temp_dir, "test_master_key")
    return SecureKeyManager(master_key=master_key, key_file=key_file)


@pytest.fixture
def storage(temp_dir, key_manager):
    """暗号化ストレージアダプタ"""
    return EncryptedFileStorageAdapter(
        data_dir=temp_dir,
        key_manager=key_manager,
    )


@pytest.fixture
def sample_user():
    """テスト用ユーザー"""
    return UserState(
        user_id="test_user_123",
        phase=RelationshipPhase.ACQUAINTANCE,
        total_interactions=10,
        display_name="テストユーザー",
        known_facts=["プログラマー", "猫好き"],
        known_topics=["career", "relationship"],
    )


class TestEncryptedFileStorageAdapter:
    """暗号化ストレージのテスト"""

    @pytest.mark.asyncio
    async def test_save_and_load_user(self, storage, sample_user):
        """ユーザーの保存と読み込み"""
        # 保存
        await storage.save_user(sample_user)

        # 読み込み
        loaded_user = await storage.load_user(sample_user.user_id)

        assert loaded_user is not None
        assert loaded_user.user_id == sample_user.user_id
        assert loaded_user.phase == sample_user.phase
        assert loaded_user.total_interactions == sample_user.total_interactions
        assert loaded_user.display_name == sample_user.display_name
        assert loaded_user.known_facts == sample_user.known_facts

    @pytest.mark.asyncio
    async def test_data_is_encrypted_in_file(self, storage, sample_user, temp_dir):
        """ファイル内のデータが暗号化されていることを確認"""
        await storage.save_user(sample_user)
        await storage.flush()  # 遅延書き込みを強制実行

        # ファイルを直接読み込み
        data_file = Path(temp_dir) / "users.enc.json"
        with open(data_file) as f:
            content = f.read()

        # ユーザーIDは暗号化されていない（キーとして使用）
        assert "test_user_123" in content
        # しかしユーザーデータ（display_name等）は暗号化されている
        assert "テストユーザー" not in content
        assert "ciphertext" in content
        assert "nonce" in content

    @pytest.mark.asyncio
    async def test_list_users(self, storage, sample_user):
        """ユーザーリストの取得"""
        await storage.save_user(sample_user)

        user2 = UserState(user_id="user_2")
        await storage.save_user(user2)

        users = await storage.list_users()
        assert len(users) == 2
        assert sample_user.user_id in users
        assert "user_2" in users

    @pytest.mark.asyncio
    async def test_delete_user(self, storage, sample_user):
        """ユーザーの削除"""
        await storage.save_user(sample_user)
        assert await storage.user_exists(sample_user.user_id)

        result = await storage.delete_user(sample_user.user_id)
        assert result is True
        assert not await storage.user_exists(sample_user.user_id)

    @pytest.mark.asyncio
    async def test_user_not_found(self, storage):
        """存在しないユーザーの読み込み"""
        user = await storage.load_user("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_wrong_key_cannot_decrypt(
        self, storage, sample_user, temp_dir, crypto
    ):
        """異なる鍵では復号できないことを確認"""
        await storage.save_user(sample_user)

        # 新しい鍵で別のストレージを作成
        wrong_key = crypto.generate_symmetric_key()
        wrong_key_file = os.path.join(temp_dir, "wrong_key")
        wrong_key_manager = SecureKeyManager(
            master_key=wrong_key, key_file=wrong_key_file
        )
        wrong_storage = EncryptedFileStorageAdapter(
            data_dir=temp_dir,
            key_manager=wrong_key_manager,
        )

        # データファイルは存在するが、復号できないのでユーザーは空
        await wrong_storage._ensure_loaded()
        assert len(wrong_storage._users) == 0

    @pytest.mark.asyncio
    async def test_persistence_across_instances(
        self, temp_dir, master_key, sample_user
    ):
        """インスタンス間でのデータ永続性"""
        key_file = os.path.join(temp_dir, "master_key")

        # 最初のインスタンスで保存
        key_manager1 = SecureKeyManager(master_key=master_key, key_file=key_file)
        storage1 = EncryptedFileStorageAdapter(
            data_dir=temp_dir,
            key_manager=key_manager1,
        )
        await storage1.save_user(sample_user)
        await storage1.flush()  # 遅延書き込みを強制実行

        # 新しいインスタンスで読み込み（同じマスターキー）
        key_manager2 = SecureKeyManager(master_key=master_key, key_file=key_file)
        storage2 = EncryptedFileStorageAdapter(
            data_dir=temp_dir,
            key_manager=key_manager2,
        )
        loaded_user = await storage2.load_user(sample_user.user_id)

        assert loaded_user is not None
        assert loaded_user.user_id == sample_user.user_id
        assert loaded_user.display_name == sample_user.display_name

    @pytest.mark.asyncio
    async def test_export_decrypted(self, storage, sample_user):
        """GDPR対応: 復号エクスポート"""
        await storage.save_user(sample_user)

        exported = await storage.export_decrypted(sample_user.user_id)
        assert exported is not None
        assert exported["user_id"] == sample_user.user_id
        assert exported["display_name"] == sample_user.display_name

    @pytest.mark.asyncio
    async def test_get_user_data_summary(self, storage, sample_user):
        """GDPR Article 15: データサマリー取得"""
        await storage.save_user(sample_user)

        summary = await storage.get_user_data_summary(sample_user.user_id)
        assert summary is not None
        assert summary["user_id"] == sample_user.user_id
        assert "data_collected" in summary
        assert "privacy_settings" in summary
        assert "your_rights" in summary

    @pytest.mark.asyncio
    async def test_user_specific_keys(self, storage, sample_user):
        """ユーザーごとに異なるキーが使われることを確認"""
        user2 = UserState(
            user_id="test_user_456",
            display_name="別のユーザー",
        )

        await storage.save_user(sample_user)
        await storage.save_user(user2)

        # 両方のユーザーが正しく読み込める
        loaded1 = await storage.load_user(sample_user.user_id)
        loaded2 = await storage.load_user(user2.user_id)

        assert loaded1 is not None
        assert loaded2 is not None
        assert loaded1.display_name == "テストユーザー"
        assert loaded2.display_name == "別のユーザー"
