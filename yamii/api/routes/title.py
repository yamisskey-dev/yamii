"""
タイトル生成エンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException

from ...core.logging import get_logger
from ..auth import verify_api_key
from ..dependencies import get_ai_provider
from ..schemas import SummarizeTitleRequest, SummarizeTitleResponse

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1",
    tags=["title"],
    dependencies=[Depends(verify_api_key)],
)

TITLE_SYSTEM_PROMPT = (
    "あなたはチャットのタイトル生成アシスタントです。"
    "ユーザーのメッセージを読み、その相談内容を短く要約したタイトルを生成してください。"
    "タイトルは日本語で、15文字以内で、簡潔にしてください。"
    "タイトルのみを出力し、他の説明は不要です。"
)


@router.post("/summarize-title", response_model=SummarizeTitleResponse)
async def summarize_title(
    request: SummarizeTitleRequest,
) -> SummarizeTitleResponse:
    """
    メッセージからチャットタイトルを生成
    """
    try:
        ai = get_ai_provider()
        title = await ai.generate(
            message=request.message,
            system_prompt=TITLE_SYSTEM_PROMPT,
            max_tokens=50,
        )
        # 改行や余分な空白を除去、50文字に制限
        title = title.strip().split("\n")[0].strip()
        if len(title) > 50:
            title = title[:50] + "..."

        return SummarizeTitleResponse(title=title)
    except Exception as e:
        logger.error(f"Title generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="タイトル生成に失敗しました",
        )
