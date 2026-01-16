"""
プラットフォームコンテキストメタデータの型定義
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PlatformType = Literal["misskey", "mastodon", "web", "cli", "other"]


class ContextMetadata(BaseModel):
    """
    プラットフォームコンテキストメタデータ
    Yuiなどのクライアントから送信されるコンテキスト情報を型安全に扱う
    """

    # 基本フィールド
    platform: PlatformType = Field(
        default="other",
        description="プラットフォーム識別子"
    )
    bot_name: str | None = Field(
        default=None,
        description="ボット名"
    )
    client_version: str | None = Field(
        default=None,
        description="クライアントバージョン"
    )
    api_version: str = Field(
        default="1.0.0",
        description="APIバージョン"
    )

    # Misskey固有フィールド
    note_visibility: str | None = Field(
        default=None,
        description="Misskeyノートの可視性 (public/home/followers/direct)"
    )
    note_id: str | None = Field(
        default=None,
        description="元ノートのID"
    )

    # 追加メタデータ
    extra: dict[str, Any] | None = Field(
        default=None,
        description="その他のプラットフォーム固有メタデータ"
    )

    def is_misskey_platform(self) -> bool:
        """Misskeyプラットフォームかどうか"""
        return self.platform == "misskey"

    def is_mastodon_platform(self) -> bool:
        """Mastodonプラットフォームかどうか"""
        return self.platform == "mastodon"

    def get_effective_visibility(self) -> str:
        """
        効果的な可視性を取得
        Misskey以外のプラットフォームではデフォルト値を返す
        """
        if self.is_misskey_platform() and self.note_visibility:
            return self.note_visibility
        return "home"

    model_config = ConfigDict(extra="allow")  # 未知のフィールドも許可（後方互換性）
