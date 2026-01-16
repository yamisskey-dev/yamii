"""
暗号化ストレージアダプターのテスト
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from yamii.adapters.storage.encrypted_file import EncryptedFileStorageAdapter
from yamii.domain.models.user import UserState
from yamii.domain.models.relationship import RelationshipPhase
from yamii.core.encryption import E2EECrypto


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
def storage(temp_dir, master_key):
    """暗号化ストレージアダプタ"""
    return EncryptedFileStorageAdapter(
        data_dir=temp_dir,
        key_file=f"{temp_dir}/test_master_key",
        master_key=master_key,
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

        # ファイルを直接読み込み
        data_file = Path(temp_dir) / "users.enc.json"
        with open(data_file, "r") as f:
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
    async def test_wrong_key_cannot_decrypt(self, storage, sample_user, temp_dir):
        """異なる鍵では復号できないことを確認"""
        await storage.save_user(sample_user)

        # 新しい鍵で別のストレージを作成
        crypto = E2EECrypto()
        wrong_key = crypto.generate_symmetric_key()
        wrong_storage = EncryptedFileStorageAdapter(
            data_dir=temp_dir,
            key_file=f"{temp_dir}/wrong_key",
            master_key=wrong_key,
        )

        # データファイルは存在するが、復号できないのでユーザーは空
        await wrong_storage._ensure_loaded()
        assert len(wrong_storage._users) == 0

    @pytest.mark.asyncio
    async def test_persistence_across_instances(self, temp_dir, master_key, sample_user):
        """インスタンス間でのデータ永続性"""
        # 最初のインスタンスで保存
        storage1 = EncryptedFileStorageAdapter(
            data_dir=temp_dir,
            key_file=f"{temp_dir}/master_key",
            master_key=master_key,
        )
        await storage1.save_user(sample_user)

        # 新しいインスタンスで読み込み
        storage2 = EncryptedFileStorageAdapter(
            data_dir=temp_dir,
            key_file=f"{temp_dir}/master_key",
            master_key=master_key,
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
