"""
API Schemas
Pydanticモデル定義
Zero-Knowledge アーキテクチャ対応版
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# === カウンセリング ===


class ConversationMessage(BaseModel):
    """会話履歴の1メッセージ"""

    role: str = Field(..., description="user または assistant")
    content: str = Field(..., description="メッセージ内容")


class CounselingRequest(BaseModel):
    """カウンセリングリクエスト"""

    message: str = Field(..., min_length=1, description="相談メッセージ")
    user_id: str = Field(..., min_length=1, description="ユーザーID")
    user_name: str | None = Field(None, description="表示名")
    session_id: str | None = Field(None, description="セッションID")
    # セッション内文脈保持: クライアントが管理する会話履歴（最大10件推奨）
    conversation_history: list[ConversationMessage] | None = Field(
        None,
        description="セッション内の会話履歴（クライアント管理、最大10件推奨）",
        max_length=20,
    )


class EmotionAnalysisResponse(BaseModel):
    """感情分析結果"""

    primary_emotion: str
    intensity: float
    stability: float
    is_crisis: bool
    all_emotions: dict[str, float]
    confidence: float


class CounselingResponse(BaseModel):
    """カウンセリングレスポンス"""

    response: str
    session_id: str
    timestamp: datetime
    emotion_analysis: EmotionAnalysisResponse
    advice_type: str
    follow_up_questions: list[str]
    is_crisis: bool
    # 危機対応情報を含む整形済みレスポンス
    formatted_response: str | None = Field(
        None, description="プラットフォーム表示用整形済みレスポンス"
    )
    crisis_resources: list[str] | None = Field(None, description="危機対応リソース")


# === ユーザー ===


class UserProfileRequest(BaseModel):
    """ユーザープロファイル設定リクエスト"""

    explicit_profile: str | None = Field(None, max_length=1000)
    display_name: str | None = Field(None, max_length=100)


# === システム ===


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""

    status: str
    timestamp: datetime
    version: str
    components: dict[str, bool]


class APIInfoResponse(BaseModel):
    """API情報レスポンス"""

    service: str
    version: str
    description: str
    features: list[str]
