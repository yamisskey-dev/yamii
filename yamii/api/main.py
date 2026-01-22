"""
Yamii API - メインアプリケーション
Zero-Knowledge アーキテクチャ対応 FastAPI アプリケーション
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..core.config import get_settings
from ..core.logging import YamiiLogger, get_logger
from .auth import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from .dependencies import get_ai_provider, get_storage
from .routes import (
    auth_router,
    commands_router,
    counseling_router,
    user_data_router,
    user_router,
)
from .schemas import APIInfoResponse, HealthResponse

# ログシステムを初期化
YamiiLogger.configure()
logger = get_logger("api.main")

# バージョン
API_VERSION = "3.0.0"


class APIVersionMiddleware(BaseHTTPMiddleware):
    """APIバージョンをレスポンスヘッダーに追加"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = API_VERSION
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル"""
    settings = get_settings()

    # 起動時
    logger.info(f"Yamii API v{API_VERSION} starting...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Rate limiting: {settings.security.rate_limit_enabled}")
    logger.info(f"API keys configured: {len(settings.security.api_keys)} key(s)")

    if not settings.security.api_keys:
        logger.warning("No API keys configured - running in development mode (no auth)")

    yield

    # 終了時
    logger.info("Yamii API shutting down...")


def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成"""
    application = FastAPI(
        title="Yamii API",
        description=(
            "Zero-Knowledge メンタルヘルスAI相談システム\n\n"
            "**特徴:**\n"
            "- Zero-Knowledge: サーバーは会話内容を保存・閲覧しない\n"
            "- クライアント側暗号化: カスタムプロンプトはユーザーのみ復号可能\n"
            "- ノーログ: 会話履歴はセッション中のみ保持\n"
            "- Misskey OAuth: Misskeyアカウントで認証\n"
        ),
        version=API_VERSION,
        lifespan=lifespan,
    )

    # ミドルウェア（実行順序: 下から上）
    # 1. CORS（フロントエンドからのアクセスを許可）
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # フロントエンドのデプロイ先に応じて設定
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    # 2. セキュリティヘッダー
    application.add_middleware(SecurityHeadersMiddleware)
    # 3. レート制限
    application.add_middleware(RateLimitMiddleware)
    # 4. リクエストログ
    application.add_middleware(RequestLoggingMiddleware)
    # 5. API バージョン
    application.add_middleware(APIVersionMiddleware)

    # ルーター登録
    application.include_router(auth_router)
    application.include_router(counseling_router)
    application.include_router(user_router)
    application.include_router(user_data_router)
    application.include_router(commands_router)

    # ルートエンドポイント
    @application.get("/", response_model=APIInfoResponse)
    async def root() -> APIInfoResponse:
        """API情報を取得"""
        return APIInfoResponse(
            service="Yamii - Zero-Knowledge メンタルヘルスAI相談API",
            version=API_VERSION,
            description="プライバシーファーストのAI相談APIサーバー",
            features=[
                "カウンセリング相談",
                "感情分析",
                "危機検出",
                "Zero-Knowledge暗号化",
                "ノーログ設計",
            ],
        )

    @application.get("/v1/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """ヘルスチェック"""
        components = {
            "storage": True,
            "ai_provider": True,
        }

        try:
            storage = get_storage()
            await storage.list_users()
        except Exception:
            components["storage"] = False

        try:
            ai = get_ai_provider()
            components["ai_provider"] = await ai.health_check()
        except Exception:
            components["ai_provider"] = False

        status = "healthy" if all(components.values()) else "degraded"

        return HealthResponse(
            status=status,
            timestamp=datetime.now(),
            version=API_VERSION,
            components=components,
        )

    return application


# デフォルトアプリケーションインスタンス
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
