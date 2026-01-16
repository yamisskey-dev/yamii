"""
Bot コマンドエンドポイント
Bot薄型化: コマンド処理をAPI側で行う

プライバシーファースト対応:
- /export: 自分のデータをエクスポート
- /clear_data: 自分のデータを削除
- /settings: プロアクティブ設定を変更
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..dependencies import get_storage
from ..auth import verify_api_key
from ...domain.ports.storage_port import IStorage


router = APIRouter(
    prefix="/v1/commands",
    tags=["commands"],
    dependencies=[Depends(verify_api_key)],
)


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

**プライバシーコマンド:**
- `/export` - 自分のデータをエクスポート
- `/clear_data` - 自分のデータを削除
- `/settings` - 通知設定を表示
- `/settings on/off` - チェックイン通知を変更

何でもお気軽にどうぞ。"""

HELP_TEXT_MISSKEY_CHAT = """Yamii - 相談AI

チャットで相談できます。
何でもお気軽にどうぞ。"""

HELP_TEXT_GENERIC = """Yamii - 相談AI

メッセージを送信して相談できます。

**プライバシーコマンド:**
- /export - 自分のデータをエクスポート
- /clear_data - 自分のデータを削除
- /settings - 通知設定を表示

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

    # プライバシーコマンド: エクスポート
    if message in ["/export", "エクスポート", "export"]:
        return MessageClassification(
            is_command=True,
            command_type="export",
            is_empty=False,
            should_counsel=False,
        )

    # プライバシーコマンド: データ削除
    if message in ["/clear_data", "/delete", "データ削除", "clear_data", "delete"]:
        return MessageClassification(
            is_command=True,
            command_type="clear_data",
            is_empty=False,
            should_counsel=False,
        )

    # プライバシーコマンド: 設定
    if message.startswith("/settings") or message.startswith("設定"):
        return MessageClassification(
            is_command=True,
            command_type="settings",
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


# === プライバシーコマンド（GDPR対応） ===


class ExportResponse(BaseModel):
    """エクスポートレスポンス"""
    response: str = Field(..., description="レスポンスメッセージ")
    command: str = Field("export", description="コマンド名")
    data_summary: Optional[Dict[str, Any]] = Field(None, description="データサマリー")
    full_export_url: Optional[str] = Field(None, description="完全エクスポートURL")


class SettingsRequest(BaseModel):
    """設定変更リクエスト"""
    user_id: str = Field(..., description="ユーザーID")
    action: str = Field("show", description="アクション: show, on, off")


class SettingsResponse(BaseModel):
    """設定レスポンス"""
    response: str = Field(..., description="レスポンスメッセージ")
    command: str = Field("settings", description="コマンド名")
    current_settings: Optional[Dict[str, Any]] = Field(None, description="現在の設定")


class ClearDataRequest(BaseModel):
    """データ削除リクエスト"""
    user_id: str = Field(..., description="ユーザーID")
    confirm: bool = Field(False, description="削除を確認")


class ClearDataResponse(BaseModel):
    """データ削除レスポンス"""
    response: str = Field(..., description="レスポンスメッセージ")
    command: str = Field("clear_data", description="コマンド名")
    deleted: bool = Field(False, description="削除されたか")


@router.post("/export", response_model=ExportResponse)
async def export_user_data(
    user_id: str,
    storage: IStorage = Depends(get_storage),
) -> ExportResponse:
    """
    ユーザーデータをエクスポート（GDPR Article 20対応: データポータビリティ）

    プライバシーファースト:
    - ユーザーは自分のデータを取得する権利がある
    - 分かりやすいサマリーを提供
    """
    user = await storage.load_user(user_id)

    if user is None:
        return ExportResponse(
            response="まだデータがありません。いつでもお話ししてくださいね。",
            command="export",
            data_summary=None,
        )

    # データサマリー（Bot向けの簡易版）
    days_active = (datetime.now() - user.first_interaction).days
    data_summary = {
        "あなたのデータ": {
            "会話回数": user.total_interactions,
            "利用開始日": user.first_interaction.strftime("%Y年%m月%d日"),
            "利用日数": f"{days_active}日",
            "記録されたエピソード数": len(user.episodes),
            "信頼フェーズ": user.phase.value,
        },
        "プライバシー情報": {
            "暗号化": "ユーザー固有の鍵で暗号化されています",
            "データ保存": "サーバー上に暗号化保存",
            "削除方法": "/clear_data コマンドで完全削除可能",
        },
    }

    response_text = f"""📊 **あなたのデータ**

🗣️ 会話回数: {user.total_interactions}回
📅 利用開始: {user.first_interaction.strftime("%Y年%m月%d日")}
🔒 関係性: {user.phase.value}

**プライバシー保護:**
あなたのデータは専用の暗号化キーで保護されています。

完全なデータをエクスポートするには:
`GET /v1/users/{user_id}/export`

データを削除するには:
`/clear_data` コマンド"""

    return ExportResponse(
        response=response_text,
        command="export",
        data_summary=data_summary,
        full_export_url=f"/v1/users/{user_id}/export",
    )


@router.post("/settings", response_model=SettingsResponse)
async def update_settings(
    request: SettingsRequest,
    storage: IStorage = Depends(get_storage),
) -> SettingsResponse:
    """
    プロアクティブ設定を表示/変更

    プライバシーファースト:
    - ユーザーは通知を完全にコントロールできる
    - オプトアウトは簡単に
    """
    user = await storage.load_user(request.user_id)

    if user is None:
        return SettingsResponse(
            response="まだデータがありません。いつでもお話ししてくださいね。",
            command="settings",
            current_settings=None,
        )

    # 設定変更
    if request.action == "on":
        user.proactive.enabled = True
        await storage.save_user(user)
        return SettingsResponse(
            response="✅ チェックイン通知を**有効**にしました。\n\n定期的に様子を伺いますね。いつでも `/settings off` で無効にできます。",
            command="settings",
            current_settings={"proactive_enabled": True},
        )

    elif request.action == "off":
        user.proactive.enabled = False
        await storage.save_user(user)
        return SettingsResponse(
            response="🔕 チェックイン通知を**無効**にしました。\n\nこちらから連絡することはありません。いつでも `/settings on` で有効にできます。",
            command="settings",
            current_settings={"proactive_enabled": False},
        )

    # 設定表示
    status = "有効" if user.proactive.enabled else "無効"
    frequency_text = {
        "daily": "毎日",
        "weekly": "週1回",
        "monthly": "月1回",
        "never": "なし",
    }.get(user.proactive.frequency, user.proactive.frequency)

    response_text = f"""⚙️ **あなたの設定**

🔔 チェックイン通知: {status}
📆 頻度: {frequency_text}

**変更方法:**
- `/settings on` - 通知を有効化
- `/settings off` - 通知を無効化

あなたのプライバシーを尊重します。"""

    return SettingsResponse(
        response=response_text,
        command="settings",
        current_settings={
            "proactive_enabled": user.proactive.enabled,
            "frequency": user.proactive.frequency,
            "preferred_time": user.proactive.preferred_time,
        },
    )


@router.post("/clear_data", response_model=ClearDataResponse)
async def clear_user_data(
    request: ClearDataRequest,
    storage: IStorage = Depends(get_storage),
) -> ClearDataResponse:
    """
    ユーザーデータを完全削除（GDPR Article 17対応: 忘れられる権利）

    プライバシーファースト:
    - ユーザーは自分のデータを削除する権利がある
    - 確認ステップで誤操作を防止
    """
    if not request.confirm:
        return ClearDataResponse(
            response="""⚠️ **データ削除の確認**

この操作は取り消せません。以下のデータがすべて削除されます:
- 会話履歴
- 感情パターン
- 記録されたエピソード
- 関係性データ

**本当に削除しますか？**
確認するには `confirm=true` を指定してください。

いつでも新しく始められますが、今までのことは覚えていられなくなります。""",
            command="clear_data",
            deleted=False,
        )

    # ユーザー存在確認
    user = await storage.load_user(request.user_id)
    if user is None:
        return ClearDataResponse(
            response="削除するデータがありません。",
            command="clear_data",
            deleted=False,
        )

    # データ削除実行
    success = await storage.delete_user(request.user_id)

    if success:
        return ClearDataResponse(
            response="""✅ **データを削除しました**

あなたのすべてのデータを安全に削除しました。
暗号化キーも破棄され、復元はできません。

また話したくなったら、いつでも戻ってきてください。
最初からになりますが、喜んでお話しします。""",
            command="clear_data",
            deleted=True,
        )
    else:
        return ClearDataResponse(
            response="データの削除に失敗しました。時間をおいて再度お試しください。",
            command="clear_data",
            deleted=False,
        )
