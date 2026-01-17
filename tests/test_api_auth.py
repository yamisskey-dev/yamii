"""
API 認証・レート制限のテスト
"""

from unittest.mock import MagicMock, patch

import pytest

from yamii.api.auth import (
    RateLimiter,
    SecurityHeadersMiddleware,
    verify_api_key,
)

# === RateLimiter テスト ===


class TestRateLimiter:
    """RateLimiter のテスト"""

    def test_allows_requests_under_limit(self):
        """制限以下のリクエストは許可される"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # モックリクエスト
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"

        for i in range(5):
            allowed, info = limiter.is_allowed(mock_request)
            assert allowed is True
            assert info["remaining"] == 4 - i

    def test_blocks_requests_over_limit(self):
        """制限を超えたリクエストはブロックされる"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"

        # 3回は許可
        for _ in range(3):
            allowed, _ = limiter.is_allowed(mock_request)
            assert allowed is True

        # 4回目はブロック
        allowed, info = limiter.is_allowed(mock_request)
        assert allowed is False
        assert info["remaining"] == 0

    def test_different_clients_have_separate_limits(self):
        """異なるクライアントは別々の制限を持つ"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        mock_request_1 = MagicMock()
        mock_request_1.headers = {}
        mock_request_1.client.host = "127.0.0.1"

        mock_request_2 = MagicMock()
        mock_request_2.headers = {}
        mock_request_2.client.host = "192.168.1.1"

        # クライアント1のリクエスト
        for _ in range(2):
            allowed, _ = limiter.is_allowed(mock_request_1)
            assert allowed is True

        # クライアント1は制限超過
        allowed, _ = limiter.is_allowed(mock_request_1)
        assert allowed is False

        # クライアント2はまだ許可
        allowed, _ = limiter.is_allowed(mock_request_2)
        assert allowed is True

    def test_api_key_based_identification(self):
        """API キーでクライアントを識別"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"

        # 同じIPでも異なるAPIキーなら別カウント
        allowed1, _ = limiter.is_allowed(mock_request, api_key="key1")
        allowed2, _ = limiter.is_allowed(mock_request, api_key="key1")
        allowed3, _ = limiter.is_allowed(mock_request, api_key="key1")

        assert allowed1 is True
        assert allowed2 is True
        assert allowed3 is False  # key1 は制限超過

        # 別のAPIキーは許可
        allowed4, _ = limiter.is_allowed(mock_request, api_key="key2")
        assert allowed4 is True

    def test_forwarded_for_header(self):
        """X-Forwarded-For ヘッダーの処理"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 198.51.100.1"}
        mock_request.client.host = "127.0.0.1"  # プロキシのIP

        # 実際のクライアントIPで識別
        allowed, _ = limiter.is_allowed(mock_request)
        assert allowed is True


# === API 認証テスト ===


class TestAPIKeyVerification:
    """API キー検証のテスト"""

    @pytest.mark.asyncio
    async def test_no_api_keys_configured(self):
        """API キーが設定されていない場合は開発モード"""
        with patch("yamii.api.auth.get_settings") as mock_settings:
            mock_settings.return_value.security.api_keys = []

            result = await verify_api_key(api_key=None)
            assert result == "development-mode"

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """有効な API キーは許可される"""
        with patch("yamii.api.auth.get_settings") as mock_settings:
            mock_settings.return_value.security.api_keys = [
                "valid-key-1",
                "valid-key-2",
            ]

            result = await verify_api_key(api_key="valid-key-1")
            assert result == "valid-key-1"

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """API キーがない場合は 401"""
        from fastapi import HTTPException

        with patch("yamii.api.auth.get_settings") as mock_settings:
            mock_settings.return_value.security.api_keys = ["valid-key"]
            mock_settings.return_value.security.api_key_header = "X-API-Key"

            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(api_key=None)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """無効な API キーは 403"""
        from fastapi import HTTPException

        with patch("yamii.api.auth.get_settings") as mock_settings:
            mock_settings.return_value.security.api_keys = ["valid-key"]

            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(api_key="invalid-key")

            assert exc_info.value.status_code == 403


# === 統合テスト ===


class TestMiddlewareIntegration:
    """ミドルウェア統合テスト"""

    @pytest.mark.asyncio
    async def test_security_headers_middleware(self):
        """セキュリティヘッダーが追加される（ASGIレベルテスト）"""
        from starlette.responses import Response

        # モックの call_next
        async def mock_call_next(request):
            return Response(content="OK", status_code=200)

        middleware = SecurityHeadersMiddleware(app=MagicMock())

        # モックリクエスト
        mock_request = MagicMock()
        mock_request.url.path = "/test"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"


# === 設定テスト ===


class TestSecuritySettings:
    """セキュリティ設定のテスト"""

    def test_api_keys_parsing(self, monkeypatch):
        """カンマ区切りの API キーがパースされる"""
        from yamii.core.config import SecuritySettings

        # 環境変数経由でテスト
        monkeypatch.setenv("YAMII_API_KEYS", "key1, key2, key3")
        settings = SecuritySettings()
        assert settings.api_keys == ["key1", "key2", "key3"]

    def test_single_api_key(self, monkeypatch):
        """単一の API キー"""
        from yamii.core.config import SecuritySettings

        monkeypatch.setenv("YAMII_API_KEYS", "single-key")
        settings = SecuritySettings()
        assert settings.api_keys == ["single-key"]

    def test_empty_api_keys(self):
        """空の API キー設定"""
        from yamii.core.config import SecuritySettings

        settings = SecuritySettings()
        assert settings.api_keys == []

    def test_rate_limit_enabled_by_default(self):
        """レート制限はデフォルトで有効"""
        from yamii.core.config import SecuritySettings

        settings = SecuritySettings()
        assert settings.rate_limit_enabled is True
