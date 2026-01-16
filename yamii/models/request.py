"""
標準化されたAPIリクエスト形式
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from .context import ContextMetadata


class CounselingAPIRequestV2(BaseModel):
    """
    カウンセリングAPIリクエスト V2
    型付けされたコンテキストをサポート
    """

    message: str = Field(description="相談メッセージ")
    user_id: str = Field(description="ユーザーID")
    user_name: str | None = Field(default=None, description="ユーザー表示名")
    session_id: str | None = Field(default=None, description="セッションID")
    context: ContextMetadata | None = Field(
        default=None, description="プラットフォームコンテキスト"
    )
    custom_prompt_id: str | None = Field(
        default=None, description="カスタムプロンプトID"
    )
    prompt_id: str | None = Field(default=None, description="プロンプトID")

    @model_validator(mode="before")
    @classmethod
    def convert_context(cls, data: Any) -> Any:
        """
        dict形式のコンテキストをContextMetadataに変換
        後方互換性のため
        """
        if isinstance(data, dict) and "context" in data:
            context = data.get("context")
            if isinstance(context, dict):
                data["context"] = ContextMetadata(**context)
        return data

    def get_platform(self) -> str:
        """プラットフォームを取得"""
        if self.context:
            return self.context.platform
        return "other"

    def is_misskey_request(self) -> bool:
        """Misskeyからのリクエストかどうか"""
        return self.context is not None and self.context.is_misskey_platform()

    def to_legacy_dict(self) -> dict[str, Any]:
        """
        旧形式のdictに変換
        既存のcounseling_serviceとの互換性のため
        """
        result = {
            "message": self.message,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "session_id": self.session_id,
            "custom_prompt_id": self.custom_prompt_id,
            "prompt_id": self.prompt_id,
        }

        if self.context:
            result["context"] = self.context.model_dump()

        return result
