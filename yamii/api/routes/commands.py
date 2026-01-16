"""
Bot コマンドエンドポイント
Bot薄型化: コマンド処理をAPI側で行う
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from ..dependencies import get_storage, get_counseling_service
from ...domain.ports.storage_port import IStorage
from ...domain.services.counseling import CounselingService


router = APIRouter(prefix="/v1/commands", tags=["commands"])


class CommandResponse(BaseModel):
    """コマンドレスポンス"""
    response: str = Field(..., description="レスポンステキスト")
    command: str = Field(..., description="実行されたコマンド")
    is_command: bool = Field(True, description="コマンドとして処理されたか")


class MessageRequest(BaseModel):
    """メッセージリクエスト"""
    message: str = Field(..., description="メッセージテキスト")
    user_id: str = Field(..., description="ユーザーID")
    platform: str = Field("generic", description="プラットフォーム名")
    bot_name: str = Field("yamii", description="Bot名")


class MessageClassification(BaseModel):
    """メッセージ分類結果"""
    is_command: bool = Field(..., description="コマンドかどうか")
    command_type: Optional[str] = Field(None, description="コマンドタイプ")
    is_empty: bool = Field(..., description="空メッセージかどうか")
    should_counsel: bool = Field(..., description="カウンセリングに回すべきか")


# === ヘルプテキスト定義 ===

HELP_TEXT_MISSKEY = """**Yamii - 相談AI**

話しかけるだけで相談できます。
- メンション: @yamii 相談内容
- リプライ: 会話を続ける
- DM: プライベートな相談

何でもお気軽にどうぞ。"""

HELP_TEXT_MISSKEY_CHAT = """Yamii - 相談AI

チャットで相談できます。
何でもお気軽にどうぞ。"""

HELP_TEXT_GENERIC = """Yamii - 相談AI

メッセージを送信して相談できます。
何でもお気軽にどうぞ。"""

EMPTY_MESSAGE_RESPONSE = "何かお話ししたいことがあれば、気軽に話しかけてください。"


@router.get("/help", response_model=CommandResponse)
async def get_help(
    platform: str = "generic",
    context: str = "note",
) -> CommandResponse:
    """
    ヘルプメッセージを取得

    - platform: misskey, generic
    - context: note, chat (Misskey用)
    """
    if platform == "misskey":
        if context == "chat":
            help_text = HELP_TEXT_MISSKEY_CHAT
        else:
            help_text = HELP_TEXT_MISSKEY
    else:
        help_text = HELP_TEXT_GENERIC

    return CommandResponse(
        response=help_text,
        command="help",
        is_command=True,
    )


@router.get("/status", response_model=CommandResponse)
async def get_status(
    storage: IStorage = Depends(get_storage),
) -> CommandResponse:
    """
    システムステータスを取得
    """
    try:
        # ストレージ接続確認（簡易チェック）
        status_text = "Yamii API: 正常"
    except Exception:
        status_text = "Yamii API: 接続エラー"

    return CommandResponse(
        response=status_text,
        command="status",
        is_command=True,
    )


@router.post("/classify", response_model=MessageClassification)
async def classify_message(
    request: MessageRequest,
) -> MessageClassification:
    """
    メッセージを分類

    Bot側でコマンド判定ロジックを持たず、API側で判定する。
    """
    message = request.message.strip().lower() if request.message else ""

    # 空メッセージ
    if not message:
        return MessageClassification(
            is_command=False,
            command_type=None,
            is_empty=True,
            should_counsel=False,
        )

    # ヘルプコマンド
    if message in ["/help", "ヘルプ", "help"]:
        return MessageClassification(
            is_command=True,
            command_type="help",
            is_empty=False,
            should_counsel=False,
        )

    # ステータスコマンド
    if message in ["/status", "ステータス", "status"]:
        return MessageClassification(
            is_command=True,
            command_type="status",
            is_empty=False,
            should_counsel=False,
        )

    # 通常メッセージ → カウンセリング
    return MessageClassification(
        is_command=False,
        command_type=None,
        is_empty=False,
        should_counsel=True,
    )


@router.post("/empty-response", response_model=CommandResponse)
async def get_empty_response() -> CommandResponse:
    """
    空メッセージへのレスポンスを取得
    """
    return CommandResponse(
        response=EMPTY_MESSAGE_RESPONSE,
        command="empty",
        is_command=False,
    )
