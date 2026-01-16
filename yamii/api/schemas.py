"""
API Schemas
Pydanticモデル定義
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# === カウンセリング ===


class CounselingRequest(BaseModel):
    """カウンセリングリクエスト"""

    message: str = Field(..., min_length=1, description="相談メッセージ")
    user_id: str = Field(..., min_length=1, description="ユーザーID")
    user_name: str | None = Field(None, description="表示名")
    session_id: str | None = Field(None, description="セッションID")


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
    # Bot向け: 危機対応情報を含む整形済みレスポンス
    formatted_response: str | None = Field(
        None, description="プラットフォーム表示用整形済みレスポンス"
    )
    crisis_resources: list[str] | None = Field(None, description="危機対応リソース")


# === ユーザー ===


class ProactiveSettingsRequest(BaseModel):
    """プロアクティブ設定リクエスト"""

    enabled: bool | None = None
    frequency: str | None = Field(None, pattern="^(daily|weekly|never)$")
    preferred_time: str | None = Field(None, pattern="^[0-2][0-9]:[0-5][0-9]$")


class ProactiveSettingsResponse(BaseModel):
    """プロアクティブ設定レスポンス"""

    enabled: bool
    frequency: str
    preferred_time: str | None
    last_outreach: datetime | None
    next_scheduled: datetime | None


class UserSummaryResponse(BaseModel):
    """ユーザーサマリーレスポンス"""

    user_id: str
    phase: str
    total_interactions: int
    trust_score: float
    days_since_first: int
    episode_count: int
    top_topics: list[str]
    proactive: ProactiveSettingsResponse


class UserProfileRequest(BaseModel):
    """ユーザープロファイル設定リクエスト"""

    explicit_profile: str | None = Field(None, max_length=1000)
    display_name: str | None = Field(None, max_length=100)


# === エピソード ===


class EpisodeResponse(BaseModel):
    """エピソードレスポンス"""

    id: str
    created_at: datetime
    summary: str
    topics: list[str]
    emotion: str
    importance_score: float
    episode_type: str


class EpisodeListResponse(BaseModel):
    """エピソードリストレスポンス"""

    episodes: list[EpisodeResponse]
    total: int


# === アウトリーチ ===


class OutreachDecisionResponse(BaseModel):
    """アウトリーチ判断レスポンス"""

    should_reach_out: bool
    reason: str | None
    message: str | None
    priority: int


class TriggerOutreachRequest(BaseModel):
    """手動アウトリーチトリガーリクエスト"""

    user_id: str
    message: str | None = None


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
