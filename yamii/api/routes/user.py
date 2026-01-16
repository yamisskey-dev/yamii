"""
ユーザー管理エンドポイント
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from ..schemas import (
    UserSummaryResponse,
    UserProfileRequest,
    ProactiveSettingsResponse,
    EpisodeResponse,
    EpisodeListResponse,
)
from ..dependencies import get_storage
from ..auth import verify_api_key
from ...domain.ports.storage_port import IStorage

router = APIRouter(
    prefix="/v1/users",
    tags=["users"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("/{user_id}", response_model=UserSummaryResponse)
async def get_user(
    user_id: str,
    storage: IStorage = Depends(get_storage),
) -> UserSummaryResponse:
    """
    ユーザー情報を取得
    """
    user = await storage.load_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "まだお話ししたことがないようです。いつでもお気軽にどうぞ。",
                "user_id": user_id,
            }
        )

    days_since_first = (datetime.now() - user.first_interaction).days
    top_topics = [t.topic for t in user.get_top_topics(5)]

    return UserSummaryResponse(
        user_id=user.user_id,
        phase=user.phase.value,
        total_interactions=user.total_interactions,
        trust_score=user.trust_score,
        days_since_first=days_since_first,
        episode_count=len(user.episodes),
        top_topics=top_topics,
        proactive=ProactiveSettingsResponse(
            enabled=user.proactive.enabled,
            frequency=user.proactive.frequency,
            preferred_time=user.proactive.preferred_time,
            last_outreach=user.proactive.last_outreach,
            next_scheduled=user.proactive.next_scheduled,
        ),
    )


@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    request: UserProfileRequest,
    storage: IStorage = Depends(get_storage),
) -> dict:
    """
    ユーザープロファイルを更新
    """
    user = await storage.load_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "まだお話ししたことがないようです。先にお話ししてからプロフィールを設定できます。",
                "user_id": user_id,
            }
        )

    if request.explicit_profile is not None:
        user.explicit_profile = request.explicit_profile
    if request.display_name is not None:
        user.display_name = request.display_name

    await storage.save_user(user)

    return {"message": "User updated successfully", "user_id": user_id}


@router.delete("/{user_id}", response_model=dict)
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
            }
        )

    return {
        "message": "データを削除しました。また話したくなったら、いつでも戻ってきてください。",
        "user_id": user_id,
    }


@router.get("/{user_id}/export", response_model=dict)
async def export_user_data(
    user_id: str,
    storage: IStorage = Depends(get_storage),
) -> dict:
    """
    ユーザーデータをエクスポート（GDPR対応）
    """
    data = await storage.export_user_data(user_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "エクスポートするデータがありません。いつでもお話ししてくださいね。",
                "user_id": user_id,
            }
        )

    # メンタルファースト: エクスポートにメッセージを追加
    data["_export_info"] = {
        "message": "これはあなたのデータです。プライバシーを守るために暗号化して保存されていました。",
        "exported_at": datetime.now().isoformat(),
        "your_rights": {
            "delete": "/v1/users/{user_id} DELETE で完全削除できます",
            "update": "/v1/users/{user_id} PUT でプロフィールを更新できます",
        },
    }

    return data


@router.get("/{user_id}/episodes", response_model=EpisodeListResponse)
async def get_user_episodes(
    user_id: str,
    limit: int = 10,
    storage: IStorage = Depends(get_storage),
) -> EpisodeListResponse:
    """
    ユーザーのエピソードを取得
    """
    user = await storage.load_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "まだエピソードがありません。お話しすると記録されていきます。",
                "user_id": user_id,
            }
        )

    recent_episodes = user.get_recent_episodes(limit)

    episodes = [
        EpisodeResponse(
            id=ep.id,
            created_at=ep.created_at,
            summary=ep.summary,
            topics=ep.topics,
            emotion=ep.emotion.value,
            importance_score=ep.importance_score,
            episode_type=ep.episode_type.value,
        )
        for ep in recent_episodes
    ]

    return EpisodeListResponse(
        episodes=episodes,
        total=len(user.episodes),
    )
