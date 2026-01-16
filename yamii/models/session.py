"""
セッション管理の拡張型定義
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class SessionContext(BaseModel):
    """
    拡張セッションコンテキスト
    プラットフォームメタデータと感情推移を含む
    """

    session_id: str = Field(description="セッションID")
    user_id: str = Field(description="ユーザーID")
    platform: str = Field(default="other", description="プラットフォーム識別子")
    created_at: datetime = Field(
        default_factory=datetime.now, description="セッション作成時刻"
    )
    last_interaction: datetime = Field(
        default_factory=datetime.now, description="最終インタラクション時刻"
    )
    platform_metadata: dict[str, Any] | None = Field(
        default=None, description="プラットフォーム固有メタデータ"
    )
    interaction_count: int = Field(default=0, description="インタラクション回数")
    mood_trajectory: list[str] = Field(default_factory=list, description="感情推移履歴")

    def add_interaction(self, emotion: str | None = None) -> None:
        """インタラクションを記録"""
        self.interaction_count += 1
        self.last_interaction = datetime.now()
        if emotion:
            self.mood_trajectory.append(emotion)

    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """セッションが期限切れかどうか"""
        elapsed = (datetime.now() - self.last_interaction).total_seconds()
        return elapsed > timeout_seconds

    def get_mood_summary(self) -> dict[str, int]:
        """感情の出現回数サマリーを取得"""
        summary: dict[str, int] = {}
        for mood in self.mood_trajectory:
            summary[mood] = summary.get(mood, 0) + 1
        return summary

    @field_serializer("created_at", "last_interaction")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()
