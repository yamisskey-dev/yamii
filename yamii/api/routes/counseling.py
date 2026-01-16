"""
カウンセリングエンドポイント
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

from ..schemas import (
    CounselingRequest,
    CounselingResponse,
    EmotionAnalysisResponse,
)
from ..dependencies import get_counseling_service
from ...domain.services.counseling import (
    CounselingService,
    CounselingRequest as DomainRequest,
)

router = APIRouter(prefix="/v1/counseling", tags=["counseling"])


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
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
