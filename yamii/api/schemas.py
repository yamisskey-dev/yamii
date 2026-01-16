"""
API Schemas
Pydanticモデル定義
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# === カウンセリング ===

class CounselingRequest(BaseModel):
    """カウンセリングリクエスト"""
    message: str = Field(..., min_length=1, description="相談メッセージ")
    user_id: str = Field(..., min_length=1, description="ユーザーID")
    user_name: Optional[str] = Field(None, description="表示名")
    session_id: Optional[str] = Field(None, description="セッションID")


class EmotionAnalysisResponse(BaseModel):
    """感情分析結果"""
    primary_emotion: str
    intensity: float
    stability: float
    is_crisis: bool
    all_emotions: Dict[str, float]
    confidence: float


class CounselingResponse(BaseModel):
    """カウンセリングレスポンス"""
    response: str
    session_id: str
    timestamp: datetime
    emotion_analysis: EmotionAnalysisResponse
    advice_type: str
    follow_up_questions: List[str]
    is_crisis: bool


# === ユーザー ===

class ProactiveSettingsRequest(BaseModel):
    """プロアクティブ設定リクエスト"""
    enabled: Optional[bool] = None
    frequency: Optional[str] = Field(None, pattern="^(daily|weekly|never)$")
    preferred_time: Optional[str] = Field(None, pattern="^[0-2][0-9]:[0-5][0-9]$")


class ProactiveSettingsResponse(BaseModel):
    """プロアクティブ設定レスポンス"""
    enabled: bool
    frequency: str
    preferred_time: Optional[str]
    last_outreach: Optional[datetime]
    next_scheduled: Optional[datetime]


class UserSummaryResponse(BaseModel):
    """ユーザーサマリーレスポンス"""
    user_id: str
    phase: str
    total_interactions: int
    trust_score: float
    days_since_first: int
    episode_count: int
    top_topics: List[str]
    proactive: ProactiveSettingsResponse


class UserProfileRequest(BaseModel):
    """ユーザープロファイル設定リクエスト"""
    explicit_profile: Optional[str] = Field(None, max_length=1000)
    display_name: Optional[str] = Field(None, max_length=100)


# === エピソード ===

class EpisodeResponse(BaseModel):
    """エピソードレスポンス"""
    id: str
    created_at: datetime
    summary: str
    topics: List[str]
    emotion: str
    importance_score: float
    episode_type: str


class EpisodeListResponse(BaseModel):
    """エピソードリストレスポンス"""
    episodes: List[EpisodeResponse]
    total: int


# === アウトリーチ ===

class OutreachDecisionResponse(BaseModel):
    """アウトリーチ判断レスポンス"""
    should_reach_out: bool
    reason: Optional[str]
    message: Optional[str]
    priority: int


class TriggerOutreachRequest(BaseModel):
    """手動アウトリーチトリガーリクエスト"""
    user_id: str
    message: Optional[str] = None


# === システム ===

class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str
    timestamp: datetime
    version: str
    components: Dict[str, bool]


class APIInfoResponse(BaseModel):
    """API情報レスポンス"""
    service: str
    version: str
    description: str
    features: List[str]
