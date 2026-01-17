"""
認証API
Misskey OAuth認証エンドポイント
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...core.config import get_settings
from ...core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

# セッション管理（本番ではRedis等を使用すべき）
_pending_auth: dict[str, dict] = {}
_sessions: dict[str, dict] = {}


class AuthStartRequest(BaseModel):
    """認証開始リクエスト"""

    instance_url: str  # Misskeyインスタンスのベース URL


class AuthStartResponse(BaseModel):
    """認証開始レスポンス"""

    auth_url: str
    session_id: str


class AuthCallbackRequest(BaseModel):
    """認証コールバックリクエスト"""

    session_id: str
    token: str  # MiAuthから受け取ったトークン


class AuthCallbackResponse(BaseModel):
    """認証コールバックレスポンス"""

    access_token: str  # YamiiのセッショントークンY
    user_id: str
    username: str
    instance_url: str
    expires_at: str


class SessionInfo(BaseModel):
    """セッション情報"""

    user_id: str
    username: str
    instance_url: str
    expires_at: str


@router.post("/start", response_model=AuthStartResponse)
async def start_auth(request: AuthStartRequest) -> AuthStartResponse:
    """
    Misskey OAuth認証を開始

    MiAuthフローを使用してMisskeyアカウントで認証する。
    """
    settings = get_settings()

    # セッションIDを生成
    session_id = secrets.token_urlsafe(32)

    # MiAuth用のパラメータ
    # 参考: https://misskey-hub.net/ja/docs/for-developers/api/token/miauth/
    callback_url = f"{settings.api_host}/v1/auth/callback"

    params = {
        "name": "Yamii - AI相談",
        "callback": callback_url,
        "permission": "read:account",  # 最小限の権限のみ
    }

    # 認証URLを生成
    instance_url = request.instance_url.rstrip("/")
    auth_url = f"{instance_url}/miauth/{session_id}?{urlencode(params)}"

    # セッションを保存
    _pending_auth[session_id] = {
        "instance_url": instance_url,
        "created_at": datetime.now(),
    }

    logger.info(f"Auth started: session_id={session_id[:8]}...")

    return AuthStartResponse(
        auth_url=auth_url,
        session_id=session_id,
    )


@router.post("/callback", response_model=AuthCallbackResponse)
async def auth_callback(request: AuthCallbackRequest) -> AuthCallbackResponse:
    """
    Misskey OAuth認証コールバック

    MiAuthフロー完了後にトークンを検証し、セッションを作成する。
    """
    import httpx

    session_id = request.session_id

    # 保留中の認証を確認
    if session_id not in _pending_auth:
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    pending = _pending_auth.pop(session_id)
    instance_url = pending["instance_url"]

    # MiAuthトークンを検証
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{instance_url}/api/miauth/{session_id}/check",
                json={},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"MiAuth verification failed: {e}")
        raise HTTPException(status_code=400, detail="Authentication failed")

    if not data.get("ok"):
        raise HTTPException(status_code=400, detail="Authentication failed")

    user_data = data.get("user", {})
    user_id = user_data.get("id")
    username = user_data.get("username")

    if not user_id or not username:
        raise HTTPException(status_code=400, detail="Invalid user data")

    # Yamiiのセッショントークンを生成
    # ユーザーIDはインスタンスURLを含めて一意にする
    full_user_id = f"{username}@{instance_url.replace('https://', '').replace('http://', '')}"
    access_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=30)

    # セッションを保存
    _sessions[access_token] = {
        "user_id": full_user_id,
        "username": username,
        "instance_url": instance_url,
        "expires_at": expires_at,
    }

    logger.info(f"Auth completed: user={full_user_id}")

    return AuthCallbackResponse(
        access_token=access_token,
        user_id=full_user_id,
        username=username,
        instance_url=instance_url,
        expires_at=expires_at.isoformat(),
    )


@router.get("/session", response_model=SessionInfo)
async def get_session(request: Request) -> SessionInfo:
    """
    現在のセッション情報を取得
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ", 1)[1]

    if token not in _sessions:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    session = _sessions[token]

    # 有効期限チェック
    if datetime.now() > session["expires_at"]:
        del _sessions[token]
        raise HTTPException(status_code=401, detail="Session expired")

    return SessionInfo(
        user_id=session["user_id"],
        username=session["username"],
        instance_url=session["instance_url"],
        expires_at=session["expires_at"].isoformat(),
    )


@router.post("/logout")
async def logout(request: Request) -> dict:
    """
    ログアウト（セッション破棄）
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        if token in _sessions:
            del _sessions[token]
            logger.info("Session destroyed")

    return {"status": "ok"}


def get_current_user(request: Request) -> dict | None:
    """
    現在のユーザーを取得（内部ヘルパー）

    Returns:
        dict | None: ユーザー情報（未認証の場合None）
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]

    if token not in _sessions:
        return None

    session = _sessions[token]

    if datetime.now() > session["expires_at"]:
        del _sessions[token]
        return None

    return session
