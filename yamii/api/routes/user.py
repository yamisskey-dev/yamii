"""
ユーザー管理エンドポイント
Zero-Knowledge対応版 - サーバー側でのユーザーデータ管理
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ...domain.models.user import UserState
from ...domain.ports.storage_port import IStorage
from ..auth import verify_api_key
from ..dependencies import get_storage
from ..schemas import (
    UserProfileRequest,
)

router = APIRouter(
    prefix="/v1/users",
    tags=["users"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    storage: IStorage = Depends(get_storage),
) -> dict:
    """
    ユーザー基本情報を取得

    Note: Zero-Knowledge設計のため、詳細なユーザー情報は
    クライアント側で暗号化されたBlobとして管理されます。
    このエンドポイントはサーバー側で保持する最小限の情報のみ返します。
    """
    user = await storage.load_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "まだお話ししたことがないようです。いつでもお気軽にどうぞ。",
                "user_id": user_id,
            },
        )

    days_since_first = (datetime.now() - user.first_interaction).days
    top_topics = [t.topic for t in user.get_top_topics(5)]

    return {
        "user_id": user.user_id,
        "phase": user.phase.value,
        "total_interactions": user.total_interactions,
        "trust_score": user.trust_score,
        "days_since_first": days_since_first,
        "top_topics": top_topics,
        "display_name": user.display_name,
        "explicit_profile": user.explicit_profile,
    }


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    request: UserProfileRequest,
    storage: IStorage = Depends(get_storage),
) -> dict:
    """
    ユーザープロファイルを更新（存在しない場合は作成）
    """
    user = await storage.load_user(user_id)
    if user is None:
        user = UserState(user_id=user_id)

    if request.explicit_profile is not None:
        user.explicit_profile = request.explicit_profile
    if request.display_name is not None:
        user.display_name = request.display_name

    await storage.save_user(user)

    return {"message": "User updated successfully", "user_id": user_id}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    storage: IStorage = Depends(get_storage),
) -> dict:
    """
    ユーザーデータを削除（GDPR対応）
    """
    success = await storage.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "削除するデータがありません。",
                "user_id": user_id,
            },
        )

    return {
        "message": "データを削除しました。また話したくなったら、いつでも戻ってきてください。",
        "user_id": user_id,
    }


@router.get("/{user_id}/export")
async def export_user_data(
    user_id: str,
    storage: IStorage = Depends(get_storage),
) -> dict:
    """
    ユーザーデータをエクスポート（GDPR対応）

    Note: Zero-Knowledge設計のため、暗号化されたBlobは
    /v1/user-data/blob から別途取得してください。
    """
    data = await storage.export_user_data(user_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "エクスポートするデータがありません。いつでもお話ししてくださいね。",
                "user_id": user_id,
            },
        )

    # メンタルファースト: エクスポートにメッセージを追加
    data["_export_info"] = {
        "message": "これはあなたのデータです。プライバシーを守るために暗号化して保存されていました。",
        "exported_at": datetime.now().isoformat(),
        "your_rights": {
            "delete": "/v1/users/{user_id} DELETE で完全削除できます",
            "update": "/v1/users/{user_id} PUT でプロフィールを更新できます",
            "encrypted_data": "/v1/user-data/blob で暗号化データを取得できます",
        },
    }

    return data
