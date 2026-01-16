"""
Yamii API - メインアプリケーション
簡素化されたFastAPI アプリケーション
"""

import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .routes import counseling_router, user_router, outreach_router, commands_router
from .schemas import HealthResponse, APIInfoResponse
from .dependencies import get_storage, get_ai_provider
from .auth import RateLimitMiddleware, SecurityHeadersMiddleware, RequestLoggingMiddleware
from ..core.config import get_settings
from ..core.logging import YamiiLogger, get_logger

# ログシステムを初期化
YamiiLogger.configure()
logger = get_logger("api.main")

# バージョン
API_VERSION = "2.0.0"


class APIVersionMiddleware(BaseHTTPMiddleware):
    """APIバージョンをレスポンスヘッダーに追加"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = API_VERSION
        return response


async def run_misskey_bot() -> None:
    """Misskey Botを起動"""
    from ..bot.misskey.yamii_bot import YamiiMisskeyBot
    from ..bot.misskey.config import YamiiMisskeyBotConfig

    settings = get_settings()

    config = YamiiMisskeyBotConfig(
        misskey_instance_url=settings.misskey.instance_url,
        misskey_access_token=settings.misskey.access_token,
        misskey_bot_user_id=settings.misskey.bot_user_id,
    )

    logger.info(f"Misskey Bot starting: {settings.misskey.instance_url}")
    bot = YamiiMisskeyBot(config)
    await bot.start()


# グローバルBot タスク参照
_bot_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル"""
    global _bot_task
    settings = get_settings()

    # 起動時
    logger.info(f"Yamii API v{API_VERSION} starting...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Encryption enabled: {settings.security.encryption_enabled}")
    logger.info(f"Rate limiting: {settings.security.rate_limit_enabled}")
    logger.info(f"API keys configured: {len(settings.security.api_keys)} key(s)")

    if not settings.security.api_keys:
        logger.warning("No API keys configured - running in development mode (no auth)")

    # Misskey Botを起動（設定があれば）
    if settings.misskey.is_configured:
        logger.info("Misskey Bot: 起動中...")
        _bot_task = asyncio.create_task(run_misskey_bot())
    else:
        logger.info("Misskey Bot: 設定なし（スキップ）")

    yield

    # 終了時
    if _bot_task and not _bot_task.done():
        logger.info("Misskey Bot: 停止中...")
        _bot_task.cancel()
        try:
            await _bot_task
        except asyncio.CancelledError:
            pass

    logger.info("Yamii API shutting down...")


def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成"""
    application = FastAPI(
        title="Yamii API",
        description=(
            "メンタルヘルス特化AI相談システム\n\n"
            "**特徴:**\n"
            "- プロアクティブケア: ユーザーに先にチェックイン\n"
            "- 継続的関係性構築: STRANGER→TRUSTEDフェーズ\n"
            "- プライバシーファースト: E2EE対応\n"
        ),
        version=API_VERSION,
        lifespan=lifespan,
    )

    # ミドルウェア（実行順序: 下から上）
    # 1. CORS（内部 API なのでローカルホストのみ許可）
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
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
    application.include_router(counseling_router)
    application.include_router(user_router)
    application.include_router(outreach_router)
    application.include_router(commands_router)

    # ルートエンドポイント
    @application.get("/", response_model=APIInfoResponse)
    async def root() -> APIInfoResponse:
        """API情報を取得"""
        return APIInfoResponse(
            service="Yamii - メンタルヘルスAI相談API",
            version=API_VERSION,
            description="プロアクティブケアを提供するBot APIサーバー",
            features=[
                "カウンセリング相談",
                "感情分析",
                "危機検出",
                "関係性フェーズ管理",
                "プロアクティブチェックイン",
                "GDPR対応データ管理",
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
