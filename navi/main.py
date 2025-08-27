"""
Navi - 人生相談専用APIサーバー
プラットフォーム非依存の独立APIサーバー
クリーンアーキテクチャとレイヤード設計を採用
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.dependencies import (
    get_memory_system, get_user_profile_manager, get_settings_manager,
    get_secure_prompt_store_dependency, get_counseling_service
)
from .core.logging import NaviLogger, get_logger, log_request, log_response, log_error
from .core.exceptions import NaviException, ExternalServiceError, ValidationError
from .services.counseling_service import CounselingRequest, CounselingResponse
from .memory import MemorySystem
from .user_profile import UserProfileManager, PERSONALITY_OPTIONS, CHARACTERISTIC_OPTIONS
from .user_settings import UserSettingsManager, DEFAULT_PROMPT_TEMPLATES

# ログシステムを初期化
NaviLogger.configure(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE")
)

# FastAPI アプリケーション作成
app = FastAPI(
    title="Navi - 人生相談APIサーバー",
    description="プラットフォーム非依存の独立人生相談AIサーバー",
    version="1.0.0"
)

# CORS設定 - 任意のオリジンを許可（本番環境では適切に制限してください）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

logger = get_logger("main")

# リクエスト/レスポンスモデル
class CounselingAPIRequest(BaseModel):
    message: str
    user_id: str
    user_name: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[dict] = None
    custom_prompt_id: Optional[str] = None
    prompt_id: Optional[str] = None

class CounselingAPIResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime
    emotion_analysis: dict
    advice_type: str
    follow_up_questions: List[str]
    is_crisis: bool


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    service: str
    version: str

class CustomPromptCreateRequest(BaseModel):
    prompt_text: str

class UserProfileRequest(BaseModel):
    profile_text: Optional[str] = None

class UserProfileResponse(BaseModel):
    user_id: str
    profile_text: Optional[str]
    created_at: str
    updated_at: str

# エラーハンドラー
@app.exception_handler(NaviException)
async def navi_exception_handler(request, exc: NaviException):
    log_error(logger, exc, {"endpoint": str(request.url)})
    return HTTPException(
        status_code=400 if isinstance(exc, ValidationError) else 500,
        detail={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(ExternalServiceError)
async def external_service_exception_handler(request, exc: ExternalServiceError):
    log_error(logger, exc, {"endpoint": str(request.url)})
    return HTTPException(
        status_code=503,
        detail={
            "error_code": exc.error_code,
            "message": "外部サービスで問題が発生しています。しばらく時間を置いてからお試しください。",
            "details": exc.details
        }
    )

# エンドポイント定義
@app.get("/", response_model=dict)
async def root():
    """ルートエンドポイント"""
    return {
        "service": "Navi - 人生相談APIサーバー",
        "version": "1.0.0",
        "description": "プラットフォーム非依存の独立人生相談AIサーバー",
        "status": "running",
        "features": {
            "clean_architecture": True,
            "dependency_injection": True,
            "structured_logging": True,
            "emotion_analysis": True,
            "crisis_detection": True,
            "custom_prompts": True,
            "user_profiles": True
        },
        "endpoints": [
            "/counseling - 人生相談メインエンドポイント",
            "/health - ヘルスチェック",
            "/custom-prompts - カスタムプロンプト管理",
            "/profile - ユーザープロファイル管理"
        ]
    }

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """ヘルスチェック"""
    try:
        # 依存関係の健全性チェック
        memory_system = get_memory_system()
        settings_manager = get_settings_manager()
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now(),
            service="Navi Counseling API",
            version="1.0.0"
        )
    except Exception as e:
        log_error(logger, e)
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "error": str(e)
        })

@app.post("/counseling", response_model=CounselingAPIResponse)
async def counseling_chat(
    request: CounselingAPIRequest,
    counseling_service = Depends(get_counseling_service),
    memory_system: MemorySystem = Depends(get_memory_system)
):
    """
    人生相談メインエンドポイント
    任意のクライアントアプリケーションからの相談リクエストを処理
    """
    start_time = datetime.now()
    log_request(logger, request.user_id, "/counseling", "POST", 
               message_length=len(request.message))
    
    try:
        # リクエストを内部形式に変換
        counseling_request = CounselingRequest(
            message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            user_name=request.user_name,
            context=request.context,
            custom_prompt_id=request.custom_prompt_id,
            prompt_id=request.prompt_id
        )
        
        # カウンセリングレスポンス生成
        counseling_response = await counseling_service.generate_counseling_response(
            counseling_request
        )
        
        # APIレスポンス形式に変換
        api_response = CounselingAPIResponse(
            response=counseling_response.response,
            session_id=counseling_response.session_id,
            timestamp=datetime.now(),
            emotion_analysis=counseling_response.emotion_analysis,
            advice_type=counseling_response.advice_type,
            follow_up_questions=counseling_response.follow_up_questions,
            is_crisis=counseling_response.is_crisis
        )
        
        # レスポンスログ
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        log_response(logger, request.user_id, "/counseling", 200, duration_ms,
                    advice_type=counseling_response.advice_type,
                    is_crisis=counseling_response.is_crisis)
        
        return api_response
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except ExternalServiceError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except Exception as e:
        log_error(logger, e, {"user_id": request.user_id})
        raise HTTPException(status_code=500, detail="Internal server error")


# カスタムプロンプト管理エンドポイント
@app.post("/custom-prompts", response_model=dict)
async def create_custom_prompt(
    request: CustomPromptCreateRequest,
    user_id: str,
    settings_manager: UserSettingsManager = Depends(get_settings_manager)
):
    """カスタムプロンプトを作成"""
    try:
        success = settings_manager.save_custom_prompt(
            user_id=user_id,
            name="custom_prompt",
            prompt_text=request.prompt_text,
            description="",
            tags=[]
        )
        
        if success:
            return {
                "message": "Custom prompt created successfully",
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save custom prompt")
        
    except Exception as e:
        log_error(logger, e)
        raise HTTPException(status_code=500, detail=f"Failed to create custom prompt: {str(e)}")

@app.get("/custom-prompts", response_model=dict)
async def get_user_custom_prompt(
    user_id: str,
    settings_manager: UserSettingsManager = Depends(get_settings_manager)
):
    """ユーザーのカスタムプロンプトを取得"""
    try:
        prompt = settings_manager.get_custom_prompt(user_id)
        
        if prompt:
            return {
                "message": "Custom prompt retrieved successfully",
                "user_id": user_id,
                "prompt": prompt,
                "has_custom_prompt": True
            }
        else:
            return {
                "message": "No custom prompt found",
                "user_id": user_id,
                "prompt": None,
                "has_custom_prompt": False
            }
        
    except Exception as e:
        log_error(logger, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch custom prompt: {str(e)}")

@app.delete("/custom-prompts", response_model=dict)
async def delete_custom_prompt(
    user_id: str,
    settings_manager: UserSettingsManager = Depends(get_settings_manager)
):
    """カスタムプロンプトを削除"""
    try:
        success = settings_manager.delete_custom_prompt(user_id)
        if success:
            return {"message": "Custom prompt deleted successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=404, detail="Custom prompt not found")
    except Exception as e:
        log_error(logger, e)
        raise HTTPException(status_code=500, detail=str(e))

# ユーザープロファイル管理エンドポイント
@app.post("/profile", response_model=dict)
async def set_user_profile(
    request: UserProfileRequest,
    user_id: str,
    profile_manager: UserProfileManager = Depends(get_user_profile_manager)
):
    """ユーザープロファイルを設定"""
    try:
        success = profile_manager.set_user_profile(
            user_id=user_id,
            profile_text=request.profile_text
        )
        
        if success:
            return {"message": "Profile updated successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to update profile")
            
    except Exception as e:
        log_error(logger, e)
        raise HTTPException(status_code=500, detail=f"Failed to set profile: {str(e)}")

@app.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    profile_manager: UserProfileManager = Depends(get_user_profile_manager)
):
    """ユーザープロファイルを取得"""
    try:
        profile = profile_manager.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return UserProfileResponse(**profile)
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e)
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

@app.delete("/profile", response_model=dict)
async def delete_user_profile(
    user_id: str,
    profile_manager: UserProfileManager = Depends(get_user_profile_manager)
):
    """ユーザープロファイルを削除"""
    try:
        success = profile_manager.delete_user_profile(user_id)
        
        if success:
            return {"message": "Profile deleted successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=404, detail="Profile not found")
            
    except Exception as e:
        log_error(logger, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete profile: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)