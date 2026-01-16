"""
カウンセリングエンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException

from ...domain.services.counseling import (
    CounselingRequest as DomainRequest,
)
from ...domain.services.counseling import (
    CounselingService,
)
from ..auth import verify_api_key
from ..dependencies import get_counseling_service
from ..schemas import (
    CounselingRequest,
    CounselingResponse,
    EmotionAnalysisResponse,
)

router = APIRouter(
    prefix="/v1/counseling",
    tags=["counseling"],
    dependencies=[Depends(verify_api_key)],
)

# 危機対応リソース（日本）
CRISIS_RESOURCES = [
    "いのちの電話: 0570-783-556",
    "よりそいホットライン: 0120-279-338",
    "こころの健康相談統一ダイヤル: 0570-064-556",
]


def _format_crisis_response(response: str, resources: list[str]) -> str:
    """危機対応レスポンスを整形"""
    parts = [
        response,
        "",
        "⚠️ **相談窓口**",
        *[f"📞 {r}" for r in resources],
        "",
        "あなたは一人ではありません。",
    ]
    return "\n".join(parts)


@router.post("", response_model=CounselingResponse)
async def counseling(
    request: CounselingRequest,
    service: CounselingService = Depends(get_counseling_service),
) -> CounselingResponse:
    """
    カウンセリングメインエンドポイント

    メッセージを受け取り、感情分析・アドバイス生成を行う。
    """
    try:
        # ドメインリクエストに変換
        domain_request = DomainRequest(
            message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            user_name=request.user_name,
        )

        # カウンセリング実行
        result = await service.generate_response(domain_request)

        # 危機対応の場合は整形済みレスポンスを生成
        formatted_response: str | None = None
        crisis_resources: list[str] | None = None

        if result.is_crisis:
            crisis_resources = CRISIS_RESOURCES
            formatted_response = _format_crisis_response(result.response, CRISIS_RESOURCES)
        else:
            formatted_response = result.response

        # APIレスポンスに変換
        return CounselingResponse(
            response=result.response,
            session_id=result.session_id,
            timestamp=result.timestamp,
            emotion_analysis=EmotionAnalysisResponse(
                primary_emotion=result.emotion_analysis.primary_emotion.value,
                intensity=result.emotion_analysis.intensity,
                stability=result.emotion_analysis.stability,
                is_crisis=result.emotion_analysis.is_crisis,
                all_emotions=result.emotion_analysis.all_emotions,
                confidence=result.emotion_analysis.confidence,
            ),
            advice_type=result.advice_type,
            follow_up_questions=result.follow_up_questions,
            is_crisis=result.is_crisis,
            formatted_response=formatted_response,
            crisis_resources=crisis_resources,
        )

    except ValueError as e:
        # メンタルファースト: 入力エラーも温かく
        raise HTTPException(
            status_code=400,
            detail={
                "message": "うまく受け取れませんでした。もう一度お試しください。",
                "error": str(e),
                "suggestion": "メッセージが空でないか確認してください。",
            }
        )
    except Exception as e:
        # メンタルファースト: システムエラーでも安心感を
        raise HTTPException(
            status_code=500,
            detail={
                "message": "申し訳ありません。一時的な問題が発生しました。",
                "error": str(e),
                "suggestion": "しばらく待ってからもう一度お試しください。問題が続く場合は、直接相談窓口へのご連絡もご検討ください。",
                "resources": CRISIS_RESOURCES,
            }
        )
