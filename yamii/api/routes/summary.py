"""
会話コンテキスト要約エンドポイント（会話メモリ用）
"""

from fastapi import APIRouter, Depends, HTTPException

from ...core.logging import get_logger
from ..auth import verify_api_key
from ..dependencies import get_ai_provider
from ..schemas import SummarizeContextRequest, SummarizeContextResponse

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1",
    tags=["summary"],
    dependencies=[Depends(verify_api_key)],
)

CONTEXT_SUMMARY_SYSTEM_PROMPT = (
    "あなたはカウンセリング記録の要約アシスタントです。"
    "相談者とカウンセラーの会話を、後続のカウンセリングで文脈として使うために要約してください。\n"
    "要約には以下を必ず含めること:\n"
    "- 相談の主題と経緯\n"
    "- 相談者に関する重要な事実（登場人物・状況など）\n"
    "- 相談者の感情の変遷\n"
    "- これまでの助言の要点\n"
    "【これまでの要約】が与えられた場合は、新しい会話の内容を統合して更新すること。\n"
    "400字以内の日本語で、要約のみを出力してください。"
)


@router.post("/summarize-context", response_model=SummarizeContextResponse)
async def summarize_context(
    request: SummarizeContextRequest,
) -> SummarizeContextResponse:
    """
    会話履歴のローリング要約を生成・更新する

    ステートレス: 既存要約と新しいメッセージを受け取り、統合した要約を返す。
    サーバー側には何も保存しない（Zero-Knowledge 設計）。
    """
    try:
        parts = []
        if request.previous_summary:
            parts.append(f"【これまでの要約】\n{request.previous_summary}")

        lines = "\n".join(
            f"{'相談者' if m.role == 'user' else 'カウンセラー'}: {m.content}"
            for m in request.messages
        )
        parts.append(f"【新しい会話】\n{lines}")

        ai = get_ai_provider()
        summary = await ai.generate(
            message="\n\n".join(parts),
            system_prompt=CONTEXT_SUMMARY_SYSTEM_PROMPT,
            max_tokens=600,
        )

        return SummarizeContextResponse(summary=summary.strip())
    except Exception as e:
        logger.error(f"Context summarization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="要約の生成に失敗しました",
        )
