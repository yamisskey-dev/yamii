"""
Yamii API - メインアプリケーション
簡素化されたFastAPI アプリケーション
"""

import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .routes import counseling_router, user_router, outreach_router, commands_router
from .schemas import HealthResponse, APIInfoResponse
from .dependencies import get_storage, get_ai_provider


# バージョン
API_VERSION = "2.0.0"


class APIVersionMiddleware(BaseHTTPMiddleware):
    """APIバージョンをレスポンスヘッダーに追加"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = API_VERSION
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル"""
    # 起動時
    print(f"Yamii API v{API_VERSION} starting...")
    yield
    # 終了時
    print("Yamii API shutting down...")


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

    # ミドルウェア
    application.add_middleware(APIVersionMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

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
