"""
ユーザーデータAPI
Zero-Knowledge 暗号化Blobの保存・取得
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ...adapters.storage.encrypted_blob_file import EncryptedBlobFileAdapter
from ...core.logging import get_logger
from .auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/user-data", tags=["user-data"])

# シングルトンインスタンス
_blob_storage: EncryptedBlobFileAdapter | None = None


def get_blob_storage() -> EncryptedBlobFileAdapter:
    """暗号化Blobストレージを取得"""
    global _blob_storage
    if _blob_storage is None:
        _blob_storage = EncryptedBlobFileAdapter()
    return _blob_storage


class SaveBlobRequest(BaseModel):
    """暗号化Blob保存リクエスト"""

    encrypted_data: str  # Base64エンコードされた暗号文
    nonce: str  # Base64エンコードされたnonce


class BlobResponse(BaseModel):
    """暗号化Blobレスポンス"""

    encrypted_data: str
    nonce: str
    created_at: str
    updated_at: str


def require_auth(request: Request) -> dict:
    """認証を要求"""
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@router.put("/blob")
async def save_user_blob(
    body: SaveBlobRequest,
    request: Request,
    storage: EncryptedBlobFileAdapter = Depends(get_blob_storage),
) -> dict:
    """
    暗号化されたユーザーデータを保存

    クライアント側で暗号化されたデータをそのまま保存する。
    サーバーは暗号文の内容を知ることはできない（Zero-Knowledge）。
    """
    user = require_auth(request)
    user_id = user["user_id"]

    await storage.save_blob(
        user_id=user_id,
        encrypted_data=body.encrypted_data,
        nonce=body.nonce,
    )

    logger.info(f"Saved encrypted blob for user: {user_id}")

    return {"status": "ok"}


@router.get("/blob", response_model=BlobResponse | None)
async def get_user_blob(
    request: Request,
    storage: EncryptedBlobFileAdapter = Depends(get_blob_storage),
) -> BlobResponse | None:
    """
    暗号化されたユーザーデータを取得

    サーバーは暗号文をそのまま返す。
    復号はクライアント側で行う（Zero-Knowledge）。
    """
    user = require_auth(request)
    user_id = user["user_id"]

    blob = await storage.load_blob(user_id)

    if blob is None:
        return None

    return BlobResponse(
        encrypted_data=blob.data,
        nonce=blob.nonce,
        created_at=blob.created_at.isoformat(),
        updated_at=blob.updated_at.isoformat(),
    )


@router.delete("/blob")
async def delete_user_blob(
    request: Request,
    storage: EncryptedBlobFileAdapter = Depends(get_blob_storage),
) -> dict:
    """
    ユーザーデータを削除（GDPR対応）

    暗号化されたBlobを完全に削除する。
    """
    user = require_auth(request)
    user_id = user["user_id"]

    deleted = await storage.delete_blob(user_id)

    if deleted:
        logger.info(f"Deleted blob for user: {user_id}")
        return {"status": "ok", "deleted": True}
    else:
        return {"status": "ok", "deleted": False}


@router.get("/exists")
async def check_user_data_exists(
    request: Request,
    storage: EncryptedBlobFileAdapter = Depends(get_blob_storage),
) -> dict:
    """
    ユーザーデータが存在するかチェック
    """
    user = require_auth(request)
    user_id = user["user_id"]

    exists = await storage.blob_exists(user_id)

    return {"exists": exists}
