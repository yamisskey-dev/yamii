"""
ユーザーデータAPI (/v1/user-data/*) のテスト
Zero-Knowledge 暗号化Blobストレージ
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yamii.api.routes.auth import _sessions
from yamii.api.routes.user_data import (
    _blob_storage,
    get_blob_storage,
    router,
)
from yamii.adapters.storage.encrypted_blob_file import EncryptedBlobFileAdapter


@pytest.fixture
def temp_blob_dir():
    """テスト用の一時Blobディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_blob_storage(temp_blob_dir):
    """テスト用のBlobストレージ"""
    return EncryptedBlobFileAdapter(data_dir=temp_blob_dir)


@pytest.fixture
def authenticated_client(mock_blob_storage):
    """認証済みのテストクライアント"""
    app = FastAPI()
    app.include_router(router)

    # モックのBlobストレージを注入
    app.dependency_overrides[get_blob_storage] = lambda: mock_blob_storage

    # 認証済みセッションを作成
    token = "test-auth-token"
    _sessions[token] = {
        "user_id": "testuser@misskey.io",
        "username": "testuser",
        "instance_url": "https://misskey.io",
        "expires_at": datetime.now() + timedelta(days=30),
    }

    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {token}"

    yield client, mock_blob_storage

    # クリーンアップ
    _sessions.clear()


@pytest.fixture
def unauthenticated_client(mock_blob_storage):
    """未認証のテストクライアント"""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_blob_storage] = lambda: mock_blob_storage

    return TestClient(app)


class TestSaveBlob:
    """Blob保存エンドポイントのテスト"""

    def test_save_blob_success(self, authenticated_client):
        """Blobの保存が成功する"""
        client, storage = authenticated_client

        response = client.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "base64encodedencrypteddata==",
                "nonce": "base64encodednonce==",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_save_blob_no_auth(self, unauthenticated_client):
        """認証なしでBlobを保存しようとするとエラー"""
        response = unauthenticated_client.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "test",
                "nonce": "test",
            },
        )

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    def test_save_blob_update_existing(self, authenticated_client):
        """既存のBlobを更新できる"""
        client, storage = authenticated_client

        # 最初の保存
        response1 = client.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "first_data",
                "nonce": "first_nonce",
            },
        )
        assert response1.status_code == 200

        # 2回目の保存（更新）
        response2 = client.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "updated_data",
                "nonce": "updated_nonce",
            },
        )
        assert response2.status_code == 200

        # 確認
        get_response = client.get("/v1/user-data/blob")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["encrypted_data"] == "updated_data"
        assert data["nonce"] == "updated_nonce"


class TestGetBlob:
    """Blob取得エンドポイントのテスト"""

    def test_get_blob_not_exists(self, authenticated_client):
        """存在しないBlobを取得するとnull"""
        client, storage = authenticated_client

        response = client.get("/v1/user-data/blob")

        assert response.status_code == 200
        assert response.json() is None

    def test_get_blob_success(self, authenticated_client):
        """Blobの取得が成功する"""
        client, storage = authenticated_client

        # 先にBlobを保存
        client.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "test_encrypted_data",
                "nonce": "test_nonce",
            },
        )

        # 取得
        response = client.get("/v1/user-data/blob")

        assert response.status_code == 200
        data = response.json()
        assert data["encrypted_data"] == "test_encrypted_data"
        assert data["nonce"] == "test_nonce"
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_blob_no_auth(self, unauthenticated_client):
        """認証なしでBlobを取得しようとするとエラー"""
        response = unauthenticated_client.get("/v1/user-data/blob")

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]


class TestDeleteBlob:
    """Blob削除エンドポイントのテスト"""

    def test_delete_blob_success(self, authenticated_client):
        """Blobの削除が成功する"""
        client, storage = authenticated_client

        # 先にBlobを保存
        client.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "to_be_deleted",
                "nonce": "nonce",
            },
        )

        # 削除
        response = client.delete("/v1/user-data/blob")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["deleted"] is True

        # 確認
        get_response = client.get("/v1/user-data/blob")
        assert get_response.json() is None

    def test_delete_blob_not_exists(self, authenticated_client):
        """存在しないBlobを削除してもエラーにならない"""
        client, storage = authenticated_client

        response = client.delete("/v1/user-data/blob")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["deleted"] is False

    def test_delete_blob_no_auth(self, unauthenticated_client):
        """認証なしでBlobを削除しようとするとエラー"""
        response = unauthenticated_client.delete("/v1/user-data/blob")

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]


class TestBlobExists:
    """Blob存在確認エンドポイントのテスト"""

    def test_blob_exists_true(self, authenticated_client):
        """Blobが存在する場合はTrue"""
        client, storage = authenticated_client

        # 先にBlobを保存
        client.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "test",
                "nonce": "nonce",
            },
        )

        response = client.get("/v1/user-data/exists")

        assert response.status_code == 200
        assert response.json()["exists"] is True

    def test_blob_exists_false(self, authenticated_client):
        """Blobが存在しない場合はFalse"""
        client, storage = authenticated_client

        response = client.get("/v1/user-data/exists")

        assert response.status_code == 200
        assert response.json()["exists"] is False

    def test_blob_exists_no_auth(self, unauthenticated_client):
        """認証なしで存在確認しようとするとエラー"""
        response = unauthenticated_client.get("/v1/user-data/exists")

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]


class TestBlobIsolation:
    """ユーザー間のBlobが分離されていることのテスト"""

    def test_different_users_have_separate_blobs(self, mock_blob_storage):
        """異なるユーザーは別々のBlobを持つ"""
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_blob_storage] = lambda: mock_blob_storage

        # ユーザー1
        token1 = "user1-token"
        _sessions[token1] = {
            "user_id": "user1@misskey.io",
            "username": "user1",
            "instance_url": "https://misskey.io",
            "expires_at": datetime.now() + timedelta(days=30),
        }

        # ユーザー2
        token2 = "user2-token"
        _sessions[token2] = {
            "user_id": "user2@misskey.io",
            "username": "user2",
            "instance_url": "https://misskey.io",
            "expires_at": datetime.now() + timedelta(days=30),
        }

        client1 = TestClient(app)
        client1.headers["Authorization"] = f"Bearer {token1}"

        client2 = TestClient(app)
        client2.headers["Authorization"] = f"Bearer {token2}"

        # ユーザー1がBlobを保存
        client1.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "user1_secret_data",
                "nonce": "user1_nonce",
            },
        )

        # ユーザー2がBlobを保存
        client2.put(
            "/v1/user-data/blob",
            json={
                "encrypted_data": "user2_secret_data",
                "nonce": "user2_nonce",
            },
        )

        # 各ユーザーが自分のデータのみ取得できることを確認
        response1 = client1.get("/v1/user-data/blob")
        assert response1.json()["encrypted_data"] == "user1_secret_data"

        response2 = client2.get("/v1/user-data/blob")
        assert response2.json()["encrypted_data"] == "user2_secret_data"

        # ユーザー1がBlobを削除しても、ユーザー2のBlobは残る
        client1.delete("/v1/user-data/blob")

        response1_after = client1.get("/v1/user-data/blob")
        assert response1_after.json() is None

        response2_after = client2.get("/v1/user-data/blob")
        assert response2_after.json()["encrypted_data"] == "user2_secret_data"

        # クリーンアップ
        _sessions.clear()
