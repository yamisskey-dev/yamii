"""
プロアクティブアウトリーチエンドポイント
Bot APIの差別化機能
"""

from fastapi import APIRouter, HTTPException, Depends

from ..schemas import (
    ProactiveSettingsRequest,
    ProactiveSettingsResponse,
    OutreachDecisionResponse,
    TriggerOutreachRequest,
)
from ..dependencies import get_storage, get_outreach_service
from ...domain.ports.storage_port import IStorage
from ...domain.services.outreach import ProactiveOutreachService

router = APIRouter(prefix="/v1", tags=["outreach"])


@router.get("/users/{user_id}/outreach/settings", response_model=ProactiveSettingsResponse)
async def get_outreach_settings(
    user_id: str,
    storage: IStorage = Depends(get_storage),
) -> ProactiveSettingsResponse:
    """
    ユーザーのプロアクティブ設定を取得
    """
    user = await storage.load_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return ProactiveSettingsResponse(
        enabled=user.proactive.enabled,
        frequency=user.proactive.frequency,
        preferred_time=user.proactive.preferred_time,
        last_outreach=user.proactive.last_outreach,
        next_scheduled=user.proactive.next_scheduled,
    )


@router.put("/users/{user_id}/outreach/settings", response_model=ProactiveSettingsResponse)
async def update_outreach_settings(
    user_id: str,
    request: ProactiveSettingsRequest,
    outreach_service: ProactiveOutreachService = Depends(get_outreach_service),
    storage: IStorage = Depends(get_storage),
) -> ProactiveSettingsResponse:
    """
    ユーザーのプロアクティブ設定を更新
    """
    success = await outreach_service.update_outreach_settings(
        user_id=user_id,
        enabled=request.enabled,
        frequency=request.frequency,
        preferred_time=request.preferred_time,
    )

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    # 更新後の設定を返す
    user = await storage.load_user(user_id)
    return ProactiveSettingsResponse(
        enabled=user.proactive.enabled,
        frequency=user.proactive.frequency,
        preferred_time=user.proactive.preferred_time,
        last_outreach=user.proactive.last_outreach,
        next_scheduled=user.proactive.next_scheduled,
    )


@router.get("/users/{user_id}/outreach/analyze", response_model=OutreachDecisionResponse)
async def analyze_outreach(
    user_id: str,
    outreach_service: ProactiveOutreachService = Depends(get_outreach_service),
) -> OutreachDecisionResponse:
    """
    ユーザーにチェックインが必要か分析

    Bot側から定期的に呼び出してチェックインが必要かを判断する。
    """
    decision = await outreach_service.analyze_user_patterns(user_id)

    return OutreachDecisionResponse(
        should_reach_out=decision.should_reach_out,
        reason=decision.reason.value if decision.reason else None,
        message=decision.message,
        priority=decision.priority,
    )


@router.post("/outreach/trigger", response_model=dict)
async def trigger_outreach(
    request: TriggerOutreachRequest,
    outreach_service: ProactiveOutreachService = Depends(get_outreach_service),
) -> dict:
    """
    手動でアウトリーチをトリガー

    管理者またはスケジューラーから呼び出される。
    実際のメッセージ送信はプラットフォームアダプター経由で行う。
    """
    # 分析を実行
    decision = await outreach_service.analyze_user_patterns(request.user_id)

    if request.message:
        # カスタムメッセージが指定された場合
        return {
            "user_id": request.user_id,
            "message": request.message,
            "triggered": True,
            "note": "Custom message provided",
        }

    if decision.should_reach_out:
        return {
            "user_id": request.user_id,
            "message": decision.message,
            "reason": decision.reason.value if decision.reason else None,
            "triggered": True,
        }

    return {
        "user_id": request.user_id,
        "message": None,
        "triggered": False,
        "note": "No outreach needed at this time",
    }
