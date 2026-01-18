"""
システム設定エンドポイント
デフォルトプロンプトの取得（閲覧のみ）

編集機能はYAMI DAO連携後に開放予定
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/v1/config", tags=["config"])

# プロンプトファイルのパス
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
DEFAULT_PROMPT_FILE = CONFIG_DIR / "YAMII.md"


class PromptResponse(BaseModel):
    """プロンプトレスポンス"""

    prompt: str
    updated_at: Optional[datetime] = None
    source: str  # "file"


def _load_prompt_from_file() -> tuple[str, bool]:
    """
    YAMII.mdからプロンプトを読み込む

    Returns:
        (prompt_content, file_exists)
    """
    if not DEFAULT_PROMPT_FILE.exists():
        return "", False

    content = DEFAULT_PROMPT_FILE.read_text(encoding="utf-8")
    return content.strip(), True


@router.get("/prompt", response_model=PromptResponse)
async def get_prompt() -> PromptResponse:
    """
    デフォルトプロンプトを取得（閲覧のみ）

    YAMII.mdファイルから読み込む。
    """
    prompt, file_exists = _load_prompt_from_file()

    if not file_exists:
        raise HTTPException(
            status_code=404,
            detail="YAMII.md not found. Please create config/YAMII.md",
        )

    # ファイルの更新日時を取得
    stat = DEFAULT_PROMPT_FILE.stat()
    updated_at = datetime.fromtimestamp(stat.st_mtime)

    return PromptResponse(
        prompt=prompt,
        updated_at=updated_at,
        source="file",
    )


# ============================================================
# 以下の編集機能はYAMI DAO連携後に開放予定
# ============================================================
#
# class PromptUpdateRequest(BaseModel):
#     """プロンプト更新リクエスト"""
#     prompt: str
#
#
# def _save_prompt_to_file(prompt: str) -> None:
#     """プロンプトをYAMII.mdに保存"""
#     CONFIG_DIR.mkdir(parents=True, exist_ok=True)
#     DEFAULT_PROMPT_FILE.write_text(prompt, encoding="utf-8")
#
#
# @router.put("/prompt", response_model=PromptResponse)
# async def update_prompt(request: PromptUpdateRequest) -> PromptResponse:
#     """デフォルトプロンプトを更新"""
#     if not request.prompt.strip():
#         raise HTTPException(status_code=400, detail="Prompt cannot be empty")
#     _save_prompt_to_file(request.prompt)
#     return PromptResponse(
#         prompt=request.prompt,
#         updated_at=datetime.now(),
#         source="file",
#     )
#
#
# @router.post("/prompt/reset", response_model=PromptResponse)
# async def reset_prompt() -> PromptResponse:
#     """デフォルトプロンプトを初期状態にリセット"""
#     # INITIAL_PROMPT定数に戻す
#     pass
