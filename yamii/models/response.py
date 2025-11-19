"""
標準化されたAPIレスポンス形式
"""

from datetime import datetime
from typing import Generic, TypeVar, Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, field_serializer


T = TypeVar("T")


class FieldError(BaseModel):
    """フィールドエラー詳細"""
    field: str = Field(description="エラーが発生したフィールド名")
    message: str = Field(description="エラーメッセージ")
    code: Optional[str] = Field(default=None, description="エラーコード")


class ApiError(BaseModel):
    """APIエラー詳細"""
    code: str = Field(description="エラーコード")
    message: str = Field(description="エラーメッセージ")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="追加のエラー詳細"
    )
    field_errors: Optional[List[FieldError]] = Field(
        default=None,
        description="フィールドごとのエラー詳細"
    )
    retry_after: Optional[int] = Field(
        default=None,
        description="リトライまでの秒数"
    )
    troubleshooting_steps: Optional[List[str]] = Field(
        default=None,
        description="トラブルシューティング手順"
    )


class ApiResponse(BaseModel, Generic[T]):
    """
    標準化されたAPIレスポンスラッパー
    成功/失敗を一貫した形式で返す
    """
    success: bool = Field(description="処理成功フラグ")
    data: Optional[T] = Field(default=None, description="レスポンスデータ")
    error: Optional[ApiError] = Field(default=None, description="エラー詳細")
    api_version: str = Field(default="1.0.0", description="APIバージョン")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="レスポンス生成時刻"
    )

    model_config = ConfigDict(extra="allow")


class CounselingAPIResponseV2(BaseModel):
    """
    カウンセリングAPIレスポンス V2
    Yuiが期待する形式との完全互換
    """
    response: str = Field(description="AI応答テキスト")
    session_id: str = Field(description="セッションID")
    timestamp: datetime = Field(description="タイムスタンプ")
    emotion_analysis: Dict[str, Any] = Field(
        description="感情分析結果",
        default_factory=lambda: {
            "primary_emotion": "neutral",
            "intensity": 5,
            "is_crisis": False,
            "all_emotions": {}
        }
    )
    advice_type: str = Field(
        default="supportive",
        description="アドバイスタイプ"
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="フォローアップ質問リスト"
    )
    is_crisis: bool = Field(
        default=False,
        description="危機状態フラグ"
    )

    # V2追加フィールド
    api_version: str = Field(
        default="1.0.0",
        description="APIバージョン"
    )
    platform_specific: Optional[Dict[str, Any]] = Field(
        default=None,
        description="プラットフォーム固有の追加情報"
    )

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()
