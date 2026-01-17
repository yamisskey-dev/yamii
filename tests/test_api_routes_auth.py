"""
認証API (/v1/auth/*) のテスト
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yamii.api.routes.auth import (
    _pending_auth,
    _sessions,
    router,
)


class TestAuthStart:
    """認証開始エンドポイントのテスト"""

    def test_start_auth_success(self):
        """認証開始が成功する"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch("yamii.api.routes.auth.get_settings") as mock_settings:
            mock_settings.return_value.api_host = "https://yamii.example.com"

            response = client.post(
                "/v1/auth/start",
                json={"instance_url": "https://misskey.io"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "session_id" in data
            assert "misskey.io/miauth/" in data["auth_url"]
            assert data["session_id"] in _pending_auth

    def test_start_auth_trailing_slash(self):
        """URLの末尾スラッシュが正規化される"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch("yamii.api.routes.auth.get_settings") as mock_settings:
            mock_settings.return_value.api_host = "https://yamii.example.com"

            response = client.post(
                "/v1/auth/start",
                json={"instance_url": "https://misskey.io/"},
            )

            assert response.status_code == 200
            data = response.json()
            # 末尾スラッシュが削除されている
            assert "misskey.io//miauth" not in data["auth_url"]


class TestAuthCallback:
    """認証コールバックエンドポイントのテスト"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """テスト前後にグローバル状態をクリア"""
        _pending_auth.clear()
        _sessions.clear()
        yield
        _pending_auth.clear()
        _sessions.clear()

    @pytest.mark.asyncio
    async def test_callback_invalid_session(self):
        """無効なセッションIDはエラー"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/v1/auth/callback",
            json={
                "session_id": "invalid-session",
                "token": "some-token",
            },
        )

        assert response.status_code == 400
        assert "Invalid or expired session" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_success(self):
        """認証コールバックが成功する"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # 保留中の認証を設定
        session_id = "test-session-id"
        _pending_auth[session_id] = {
            "instance_url": "https://misskey.io",
            "created_at": datetime.now(),
        }

        # MiAuth APIをモック
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "user": {
                "id": "user123",
                "username": "testuser",
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.post(
                "/v1/auth/callback",
                json={
                    "session_id": session_id,
                    "token": "miauth-token",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["user_id"] == "testuser@misskey.io"
            assert data["username"] == "testuser"
            assert data["instance_url"] == "https://misskey.io"

    @pytest.mark.asyncio
    async def test_callback_miauth_failed(self):
        """MiAuth検証失敗時はエラー"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        session_id = "test-session-id"
        _pending_auth[session_id] = {
            "instance_url": "https://misskey.io",
            "created_at": datetime.now(),
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            response = client.post(
                "/v1/auth/callback",
                json={
                    "session_id": session_id,
                    "token": "miauth-token",
                },
            )

            assert response.status_code == 400
            assert "Authentication failed" in response.json()["detail"]


class TestSession:
    """セッション管理エンドポイントのテスト"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """テスト前後にグローバル状態をクリア"""
        _sessions.clear()
        yield
        _sessions.clear()

    def test_get_session_no_auth(self):
        """認証なしでセッション取得はエラー"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/v1/auth/session")

        assert response.status_code == 401
        assert "Missing or invalid token" in response.json()["detail"]

    def test_get_session_invalid_token(self):
        """無効なトークンでセッション取得はエラー"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get(
            "/v1/auth/session",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
        assert "Invalid or expired session" in response.json()["detail"]

    def test_get_session_success(self):
        """有効なセッションを取得"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # セッションを作成
        token = "valid-test-token"
        expires_at = datetime.now() + timedelta(days=30)
        _sessions[token] = {
            "user_id": "testuser@misskey.io",
            "username": "testuser",
            "instance_url": "https://misskey.io",
            "expires_at": expires_at,
        }

        response = client.get(
            "/v1/auth/session",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "testuser@misskey.io"
        assert data["username"] == "testuser"
        assert data["instance_url"] == "https://misskey.io"

    def test_get_session_expired(self):
        """期限切れセッションはエラー"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        token = "expired-token"
        _sessions[token] = {
            "user_id": "testuser@misskey.io",
            "username": "testuser",
            "instance_url": "https://misskey.io",
            "expires_at": datetime.now() - timedelta(days=1),  # 期限切れ
        }

        response = client.get(
            "/v1/auth/session",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401
        assert "Session expired" in response.json()["detail"]
        # セッションが削除されている
        assert token not in _sessions


class TestLogout:
    """ログアウトエンドポイントのテスト"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """テスト前後にグローバル状態をクリア"""
        _sessions.clear()
        yield
        _sessions.clear()

    def test_logout_success(self):
        """ログアウト成功"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        token = "session-to-logout"
        _sessions[token] = {
            "user_id": "testuser@misskey.io",
            "username": "testuser",
            "instance_url": "https://misskey.io",
            "expires_at": datetime.now() + timedelta(days=30),
        }

        response = client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        # セッションが削除されている
        assert token not in _sessions

    def test_logout_without_auth(self):
        """認証なしでもログアウトは成功（空操作）"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post("/v1/auth/logout")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_logout_invalid_token(self):
        """無効なトークンでもログアウトは成功（空操作）"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/v1/auth/logout",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
