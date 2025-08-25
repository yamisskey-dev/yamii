"""
Navi - 人生相談専用APIサーバー
独立したサーバーとして設計され、外部（yui等）から呼び出される
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .counseling_service import CounselingService, CounselingRequest, CounselingResponse
from .memory import MemorySystem
from .markdown_prompt_loader import get_prompt_loader, list_available_prompts, reload_prompts
from .user_profile import UserProfileManager, PERSONALITY_OPTIONS, CHARACTERISTIC_OPTIONS
from .user_settings import settings_manager, DEFAULT_PROMPT_TEMPLATES

# FastAPI アプリケーション作成
app = FastAPI(
    title="Navi - 人生相談APIサーバー",
    description="独立した人生相談AI サーバー。外部サービスから利用可能。",
    version="0.1.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# サービス初期化
memory_system = MemorySystem()
user_profile_manager = UserProfileManager()
counseling_service = None  # 初期化時に設定

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

class SessionStatusResponse(BaseModel):
    session_id: str
    user_id: str
    conversation_count: int
    last_interaction: datetime
    primary_emotions: List[str]

class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    service: str

# カスタムプロンプト関連モデル
class CustomPromptCreateRequest(BaseModel):
    name: str
    prompt_text: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []

class CustomPromptUpdateRequest(BaseModel):
    name: Optional[str] = None
    prompt_text: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class CustomPromptResponse(BaseModel):
    id: str
    name: str
    prompt_text: str
    description: str
    tags: List[str]
    user_id: str
    created_at: datetime
    updated_at: datetime
    usage_count: int
    is_active: bool

class CustomPromptListResponse(BaseModel):
    prompts: List[CustomPromptResponse]
    total_count: int

# ユーザープロファイル関連モデル
class UserProfileRequest(BaseModel):
    name: Optional[str] = None
    occupation: Optional[str] = None
    personality: Optional[str] = None
    characteristics: Optional[List[str]] = None
    additional_info: Optional[str] = None

class UserProfileResponse(BaseModel):
    user_id: str
    name: Optional[str]
    occupation: Optional[str]
    personality: Optional[str]
    characteristics: List[str]
    additional_info: Optional[str]
    created_at: str
    updated_at: str

# 依存関数
def get_counseling_service() -> CounselingService:
    """カウンセリングサービスを取得"""
    global counseling_service
    
    if counseling_service is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        counseling_service = CounselingService(api_key, None, user_profile_manager)
    
    return counseling_service


def get_user_profile_manager() -> UserProfileManager:
    """ユーザープロファイル管理サービスを取得"""
    return user_profile_manager

# エンドポイント定義
@app.get("/", response_model=dict)
async def root():
    """ルートエンドポイント"""
    return {
        "service": "Navi - 人生相談APIサーバー",
        "version": "0.1.0",
        "description": "独立した人生相談AIサーバー",
        "status": "running",
        "endpoints": [
            "/counseling - 人生相談メインエンドポイント",
            "/session/{session_id}/status - セッション状況確認",
            "/health - ヘルスチェック",
            "/custom-prompts - カスタムプロンプト管理",
            "/custom-prompts/templates - デフォルトテンプレート取得",
            "/prompts - NAVI.mdプロンプト管理",
            "/prompts/reload - プロンプト再読み込み"
        ]
    }

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """ヘルスチェック"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(),
        service="Navi Counseling API"
    )

@app.post("/counseling", response_model=CounselingAPIResponse)
async def counseling_chat(
    request: CounselingAPIRequest,
    service: CounselingService = Depends(get_counseling_service)
):
    """
    人生相談メインエンドポイント
    外部サービス（yui等）からの相談リクエストを処理
    """
    try:
        # セッションIDの生成または使用
        session_id = request.session_id or str(uuid.uuid4())
        
        # CounselingRequestオブジェクトの作成
        counseling_request = CounselingRequest(
            message=request.message,
            user_id=request.user_id,
            session_id=session_id,
            user_name=request.user_name,
            context=request.context,
            custom_prompt_id=request.custom_prompt_id,
            prompt_id=request.prompt_id
        )
        
        # カウンセリングレスポンス生成
        counseling_response = await service.generate_counseling_response(counseling_request)
        
        # 記憶システムに会話を保存
        memory_system.add_conversation(
            user_id=request.user_id,
            user_message=request.message,
            ai_response=counseling_response.response,
            importance=counseling_response.emotion_analysis.get('intensity', 5),
            context=counseling_response.advice_type
        )
        
        return CounselingAPIResponse(
            response=counseling_response.response,
            session_id=counseling_response.session_id,
            timestamp=datetime.now(),
            emotion_analysis=counseling_response.emotion_analysis,
            advice_type=counseling_response.advice_type,
            follow_up_questions=counseling_response.follow_up_questions,
            is_crisis=counseling_response.emotion_analysis.get('is_crisis', False)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Counseling processing failed: {str(e)}")

@app.get("/session/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """セッション状況を確認"""
    try:
        # セッションに関連する会話を検索
        session_conversations = [
            conv for conv in memory_system.conversations 
            if conv.get('session_id') == session_id
        ]
        
        if not session_conversations:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 最新の会話から情報を取得
        latest_conv = max(session_conversations, key=lambda x: x['timestamp'])
        
        # 主要感情を分析
        emotions = []
        for conv in session_conversations[-5:]:  # 最近5件
            context = conv.get('context', 'general_support')
            if context not in emotions:
                emotions.append(context)
        
        return SessionStatusResponse(
            session_id=session_id,
            user_id=latest_conv['user_id'],
            conversation_count=len(session_conversations),
            last_interaction=datetime.fromtimestamp(latest_conv['timestamp']),
            primary_emotions=emotions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@app.get("/users/{user_id}/summary")
async def get_user_counseling_summary(user_id: str):
    """ユーザーのカウンセリング要約を取得"""
    try:
        user_conversations = [
            conv for conv in memory_system.conversations 
            if conv['user_id'] == user_id and conv['isActive']
        ]
        
        if not user_conversations:
            return {"message": "No counseling history found", "user_id": user_id}
        
        # 統計情報を計算
        advice_types = {}
        total_importance = 0
        crisis_count = 0
        
        for conv in user_conversations:
            context = conv.get('context', 'general_support')
            advice_types[context] = advice_types.get(context, 0) + 1
            total_importance += conv.get('importance', 5)
            
            # 危機的状況の検出（簡易版）
            if any(word in conv['user_message'] for word in ['死にたい', '消えたい', '限界']):
                crisis_count += 1
        
        avg_importance = total_importance / len(user_conversations) if user_conversations else 0
        most_common_issue = max(advice_types, key=advice_types.get) if advice_types else 'general_support'
        
        return {
            "user_id": user_id,
            "total_conversations": len(user_conversations),
            "average_importance": round(avg_importance, 2),
            "most_common_issue": most_common_issue,
            "crisis_indicators": crisis_count,
            "issue_distribution": advice_types,
            "last_interaction": datetime.fromtimestamp(
                max(conv['timestamp'] for conv in user_conversations)
            ).isoformat() if user_conversations else None,
            "needs_attention": crisis_count > 0 or avg_importance > 7
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """セッションを削除（プライバシー保護）"""
    try:
        # セッション関連の会話を非アクティブ化
        deleted_count = 0
        for conv in memory_system.conversations:
            if conv.get('session_id') == session_id:
                conv['isActive'] = False
                deleted_count += 1
        
        return {
            "message": f"Session deleted successfully",
            "session_id": session_id,
            "conversations_deleted": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session deletion failed: {str(e)}")

@app.post("/admin/cleanup")
async def cleanup_old_data():
    """古いデータのクリーンアップ（管理者用）"""
    try:
        memory_system.cleanup_old_memories(days_to_keep=30)
        
        active_count = sum(1 for conv in memory_system.conversations if conv['isActive'])
        total_count = len(memory_system.conversations)
        
        return {
            "message": "Cleanup completed",
            "active_conversations": active_count,
            "total_conversations": total_count,
            "cleaned_conversations": total_count - active_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# カスタムプロンプト管理エンドポイント（暗号化データベース使用）
@app.post("/custom-prompts", response_model=dict)
async def create_custom_prompt(
    request: CustomPromptCreateRequest,
    user_id: str
):
    """カスタムプロンプトを作成（暗号化データベースに保存）"""
    try:
        success = settings_manager.save_custom_prompt(
            user_id=user_id,
            name=request.name,
            prompt_text=request.prompt_text,
            description=request.description,
            tags=request.tags
        )
        
        if success:
            return {
                "message": "Custom prompt created successfully",
                "name": request.name,
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save custom prompt")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create custom prompt: {str(e)}")

@app.get("/custom-prompts", response_model=dict)
async def list_user_custom_prompts(user_id: str):
    """ユーザーのカスタムプロンプト一覧を取得（暗号化データベースから）"""
    try:
        prompts = settings_manager.list_custom_prompts(user_id)
        
        return {
            "message": "Custom prompts retrieved successfully",
            "user_id": user_id,
            "prompts": prompts,
            "total_count": len(prompts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch custom prompts: {str(e)}")

@app.get("/custom-prompts/{prompt_name}", response_model=dict)
async def get_custom_prompt(prompt_name: str, user_id: str):
    """特定のカスタムプロンプトを取得（暗号化データベースから）"""
    try:
        prompt = settings_manager.get_custom_prompt(user_id, prompt_name)
        
        if not prompt:
            raise HTTPException(status_code=404, detail="Custom prompt not found")
        
        return {
            "message": "Custom prompt retrieved successfully",
            "user_id": user_id,
            "name": prompt_name,
            "prompt": prompt
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch custom prompt: {str(e)}")

@app.put("/custom-prompts/{prompt_name}", response_model=dict)
async def update_custom_prompt(
    prompt_name: str,
    user_id: str,
    request: CustomPromptUpdateRequest
):
    """カスタムプロンプトを更新（暗号化データベースで）"""
    try:
        # 既存のプロンプトを取得
        existing_prompt = settings_manager.get_custom_prompt(user_id, prompt_name)
        if not existing_prompt:
            raise HTTPException(status_code=404, detail="Custom prompt not found")
        
        # 更新用のデータを準備
        updated_name = request.name if request.name is not None else prompt_name
        updated_prompt_text = request.prompt_text if request.prompt_text is not None else existing_prompt["prompt_text"]
        updated_description = request.description if request.description is not None else existing_prompt.get("description", "")
        updated_tags = request.tags if request.tags is not None else existing_prompt.get("tags", [])
        
        # 既存のプロンプトを削除（名前が変わる場合）
        if updated_name != prompt_name:
            settings_manager.delete_custom_prompt(user_id, prompt_name)
        
        # 新しいデータで保存
        success = settings_manager.save_custom_prompt(
            user_id=user_id,
            name=updated_name,
            prompt_text=updated_prompt_text,
            description=updated_description,
            tags=updated_tags
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update custom prompt")
        
        return {
            "message": "Custom prompt updated successfully",
            "user_id": user_id,
            "name": updated_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update custom prompt: {str(e)}")

@app.delete("/custom-prompts/{prompt_name}", response_model=dict)
async def delete_custom_prompt(prompt_name: str, user_id: str):
    """カスタムプロンプトを削除（暗号化データベースから）"""
    try:
        success = settings_manager.delete_custom_prompt(user_id, prompt_name)
        
        if not success:
            raise HTTPException(status_code=404, detail="Custom prompt not found")
        
        return {
            "message": "Custom prompt deleted successfully",
            "user_id": user_id,
            "name": prompt_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete custom prompt: {str(e)}")

@app.get("/custom-prompts/templates/default", response_model=dict)
async def get_default_prompt_templates():
    """デフォルトプロンプトテンプレートを取得"""
    return {
        "message": "Default prompt templates",
        "templates": DEFAULT_PROMPT_TEMPLATES
    }

@app.post("/custom-prompts/from-template", response_model=dict)
async def create_prompt_from_template(
    user_id: str,
    template_name: str,
    custom_name: Optional[str] = None
):
    """テンプレートからカスタムプロンプトを作成"""
    try:
        if template_name not in DEFAULT_PROMPT_TEMPLATES:
            raise HTTPException(status_code=404, detail="Template not found")
        
        template = DEFAULT_PROMPT_TEMPLATES[template_name]
        
        success = settings_manager.save_custom_prompt(
            user_id=user_id,
            name=custom_name or template['name'],
            prompt_text=template['prompt_text'],
            description=template['description'],
            tags=template['tags']
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create custom prompt from template")
        
        return {
            "message": "Custom prompt created from template",
            "template_name": template_name,
            "name": custom_name or template['name']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create prompt from template: {str(e)}")


# NAVI.mdプロンプト管理エンドポイント
@app.get("/prompts", response_model=dict)
async def get_available_prompts():
    """利用可能なNAVI.mdプロンプト一覧を取得"""
    try:
        from .markdown_prompt_loader import list_available_prompts
        prompts = list_available_prompts()
        return {
            "message": "Available prompts from NAVI.md",
            "prompts": prompts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list prompts: {str(e)}")

@app.post("/prompts/reload", response_model=dict)
async def reload_navi_prompts():
    """NAVI.mdプロンプトをリロード"""
    try:
        from .markdown_prompt_loader import reload_prompts, list_available_prompts
        reload_prompts()
        prompts = list_available_prompts()
        return {
            "message": "NAVI.md prompts reloaded successfully",
            "total_prompts": len(prompts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload prompts: {str(e)}")

@app.get("/prompts/{prompt_id}", response_model=dict)
async def get_prompt_info(prompt_id: str):
    """特定のプロンプト情報を取得"""
    try:
        from .markdown_prompt_loader import get_prompt_loader
        
        loader = get_prompt_loader()
        prompt_info = loader.get_prompt_info(prompt_id)
        
        if not prompt_info['found']:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        return {
            "message": "Prompt information",
            "prompt": prompt_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prompt info: {str(e)}")

# ユーザープロファイル管理エンドポイント
@app.post("/profile", response_model=dict)
async def set_user_profile(
    request: UserProfileRequest,
    user_id: str,
    manager: UserProfileManager = Depends(get_user_profile_manager)
):
    """ユーザープロファイルを設定"""
    try:
        success = manager.set_user_profile(
            user_id=user_id,
            name=request.name,
            occupation=request.occupation,
            personality=request.personality,
            characteristics=request.characteristics,
            additional_info=request.additional_info
        )
        
        if success:
            return {"message": "Profile updated successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to update profile")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set profile: {str(e)}")

@app.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    manager: UserProfileManager = Depends(get_user_profile_manager)
):
    """ユーザープロファイルを取得"""
    try:
        profile = manager.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return UserProfileResponse(**profile)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

@app.delete("/profile", response_model=dict)
async def delete_user_profile(
    user_id: str,
    manager: UserProfileManager = Depends(get_user_profile_manager)
):
    """ユーザープロファイルを削除"""
    try:
        success = manager.delete_user_profile(user_id)
        
        if success:
            return {"message": "Profile deleted successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=404, detail="Profile not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete profile: {str(e)}")

@app.get("/profile/options", response_model=dict)
async def get_profile_options():
    """プロファイル設定用の選択肢を取得"""
    return {
        "personalities": PERSONALITY_OPTIONS,
        "characteristics": CHARACTERISTIC_OPTIONS
    }

@app.get("/profile/{user_id}/prompt", response_model=dict)
async def get_user_dynamic_prompt(
    user_id: str,
    manager: UserProfileManager = Depends(get_user_profile_manager)
):
    """ユーザープロファイルから生成された動的プロンプトを取得"""
    try:
        prompt = manager.generate_prompt_from_profile(user_id)
        profile = manager.get_user_profile(user_id)
        
        return {
            "user_id": user_id,
            "prompt": prompt,
            "has_profile": profile is not None,
            "profile_complete": bool(profile and profile.get("name") and profile.get("occupation") and profile.get("personality"))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate prompt: {str(e)}")

# ユーザー設定管理エンドポイント（暗号化データベース使用）
@app.post("/user-settings", response_model=dict)
async def save_user_settings(user_id: str, settings: dict):
    """ユーザー設定を保存（暗号化データベースに）"""
    try:
        success = settings_manager.save_user_settings(user_id, settings)
        
        if success:
            return {"message": "User settings saved successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to save user settings")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.get("/user-settings", response_model=dict)
async def get_user_settings(user_id: str):
    """ユーザー設定を取得（暗号化データベースから）"""
    try:
        settings = settings_manager.get_user_settings(user_id)
        
        if settings is None:
            # デフォルト設定を返す
            return {
                "user_id": user_id,
                "settings": {
                    "prompt_preference": {"prompt_id": None, "custom_prompt_name": None},
                    "ui_preferences": {},
                    "notification_settings": {}
                }
            }
        
        return {"user_id": user_id, "settings": settings}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")

@app.get("/user-settings/prompt-preference", response_model=dict)
async def get_user_prompt_preference(user_id: str):
    """ユーザーのプロンプト設定を取得"""
    try:
        settings = settings_manager.get_user_settings(user_id)
        
        if settings and "prompt_preference" in settings:
            preferences = settings["prompt_preference"]
            return {
                "user_id": user_id,
                "prompt_id": preferences.get("prompt_id"),
                "custom_prompt_name": preferences.get("custom_prompt_name")
            }
        
        return {
            "user_id": user_id,
            "prompt_id": None,
            "custom_prompt_name": None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prompt preference: {str(e)}")

@app.post("/user-settings/prompt-preference", response_model=dict)
async def set_user_prompt_preference(
    user_id: str,
    prompt_id: Optional[str] = None,
    custom_prompt_name: Optional[str] = None
):
    """ユーザーのプロンプト設定を保存"""
    try:
        # 既存の設定を取得
        existing_settings = settings_manager.get_user_settings(user_id) or {}
        
        # プロンプト設定を更新
        existing_settings["prompt_preference"] = {
            "prompt_id": prompt_id,
            "custom_prompt_name": custom_prompt_name
        }
        
        success = settings_manager.save_user_settings(user_id, existing_settings)
        
        if success:
            return {"message": "Prompt preference saved successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to save prompt preference")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save prompt preference: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)