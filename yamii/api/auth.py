"""
API 認証・認可

- API キー認証
- レート制限
- セキュリティミドルウェア
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..core.config import get_settings

# === API キー認証 ===

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """
    API キーを検証

    設定された API キーと一致するか確認。
    API キーが設定されていない場合は認証をスキップ（開発用）。

    Returns:
        有効な API キー

    Raises:
        HTTPException: 認証失敗時
    """
    settings = get_settings()

    # API キーが設定されていない場合は認証をスキップ
    if not settings.security.api_keys:
        return "development-mode"

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthorized",
                "message": "API キーが必要です",
                "header": settings.security.api_key_header,
            },
        )

    if api_key not in settings.security.api_keys:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": "無効な API キーです",
            },
        )

    return api_key


# === レート制限 ===


class RateLimiter:
    """
    インメモリレート制限

    スライディングウィンドウ方式でリクエスト数を制限。
    本番環境では Redis ベースの実装を推奨。
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_id(self, request: Request, api_key: str | None = None) -> str:
        """クライアント識別子を取得"""
        # API キーがあればそれを使用、なければ IP アドレス
        if api_key and api_key != "development-mode":
            return f"key:{api_key}"

        # X-Forwarded-For ヘッダーを確認（プロキシ経由の場合）
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        # クライアント IP
        client = request.client
        if client:
            return f"ip:{client.host}"

        return "unknown"

    def _cleanup_old_requests(self, client_id: str, current_time: float) -> None:
        """古いリクエスト記録を削除"""
        cutoff = current_time - self.window_seconds
        self._requests[client_id] = [t for t in self._requests[client_id] if t > cutoff]

    def is_allowed(
        self, request: Request, api_key: str | None = None
    ) -> tuple[bool, dict]:
        """
        リクエストが許可されるか確認

        Returns:
            (allowed, info) - 許可されるかと、レート制限情報
        """
        current_time = time.time()
        client_id = self._get_client_id(request, api_key)

        # メモリ保護: エントリ数が上限を超えたら古いものをパージ
        if len(self._requests) > 10000:
            cutoff = current_time - self.window_seconds
            self._requests = defaultdict(list, {
                k: [t for t in v if t > cutoff]
                for k, v in self._requests.items()
                if any(t > cutoff for t in v)
            })

        self._cleanup_old_requests(client_id, current_time)

        request_count = len(self._requests[client_id])
        remaining = max(0, self.max_requests - request_count)

        info = {
            "limit": self.max_requests,
            "remaining": remaining,
            "reset": int(current_time + self.window_seconds),
            "window": self.window_seconds,
        }

        if request_count >= self.max_requests:
            return False, info

        # リクエストを記録
        self._requests[client_id].append(current_time)
        info["remaining"] = remaining - 1

        return True, info


# グローバルレートリミッターインスタンス
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """レートリミッターを取得"""
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        _rate_limiter = RateLimiter(
            max_requests=settings.security.rate_limit_requests,
            window_seconds=settings.security.rate_limit_window,
        )
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    レート制限ミドルウェア

    全リクエストに対してレート制限を適用。
    制限を超えた場合は 429 Too Many Requests を返す。
    """

    # レート制限を適用しないパス
    EXEMPT_PATHS = {"/", "/v1/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: Callable):
        settings = get_settings()

        # レート制限が無効な場合はスキップ
        if not settings.security.rate_limit_enabled:
            return await call_next(request)

        # 除外パスはスキップ
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # API キーを取得（認証ミドルウェアより先に実行される可能性があるため）
        api_key = request.headers.get(settings.security.api_key_header)

        rate_limiter = get_rate_limiter()
        allowed, info = rate_limiter.is_allowed(request, api_key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "too_many_requests",
                    "message": "リクエスト制限を超えました。しばらく待ってからお試しください。",
                    "retry_after": info["window"],
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["window"]),
                },
            )

        response = await call_next(request)

        # レート制限情報をヘッダーに追加
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response


# === セキュリティヘッダーミドルウェア ===


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    セキュリティヘッダーを追加

    OWASP 推奨のセキュリティヘッダーを設定。
    """

    # Swagger UI / ReDoc が使用する CDN
    DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # セキュリティヘッダー
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CSP: ドキュメントページは CDN を許可、それ以外は厳格に
        if request.url.path in self.DOCS_PATHS:
            # Swagger UI / ReDoc 用の緩和された CSP
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net;"
            )
        else:
            # API エンドポイント用の厳格な CSP
            response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


# === リクエストログミドルウェア ===


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    リクエスト/レスポンスログミドルウェア

    全リクエストの開始・終了をログに記録。
    構造化ログで出力し、後の分析に役立てる。
    """

    # ログを出力しないパス（ヘルスチェック等）
    SKIP_LOGGING_PATHS = {"/v1/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: Callable):
        from ..core.logging import get_logger

        # ログをスキップするパス
        if request.url.path in self.SKIP_LOGGING_PATHS:
            return await call_next(request)

        logger = get_logger("api.request")

        # リクエスト開始時刻
        start_time = time.time()

        # リクエスト情報（プライバシーファースト: IPアドレス・User-Agentは記録しない）
        request_id = request.headers.get(
            "X-Request-ID", f"req_{int(start_time * 1000)}"
        )

        # リクエストログ
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "event_type": "request_start",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        # リクエスト処理
        try:
            response = await call_next(request)
        except Exception as e:
            # エラー時のログ
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "event_type": "request_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        # レスポンス完了ログ
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Response: {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "event_type": "request_complete",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        # レスポンスにリクエストIDを追加
        response.headers["X-Request-ID"] = request_id

        return response
