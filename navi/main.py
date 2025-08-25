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
from .custom_prompt import CustomPromptManager, DEFAULT_PROMPT_TEMPLATES
from .markdown_prompt_loader import get_prompt_loader, list_available_prompts, reload_prompts

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
custom_prompt_manager = CustomPromptManager()
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

# 依存関数
def get_counseling_service() -> CounselingService:
    """カウンセリングサービスを取得"""
    global counseling_service
    
    if counseling_service is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        counseling_service = CounselingService(api_key, custom_prompt_manager)
    
    return counseling_service

def get_custom_prompt_manager() -> CustomPromptManager:
    """カスタムプロンプト管理サービスを取得"""
    return custom_prompt_manager

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

# カスタムプロンプト管理エンドポイント
@app.post("/custom-prompts", response_model=dict)
async def create_custom_prompt(
    request: CustomPromptCreateRequest,
    user_id: str,
    manager: CustomPromptManager = Depends(get_custom_prompt_manager)
):
    """カスタムプロンプトを作成"""
    try:
        prompt_id = manager.create_custom_prompt(
            user_id=user_id,
            name=request.name,
            prompt_text=request.prompt_text,
            description=request.description,
            tags=request.tags
        )
        
        return {
            "message": "Custom prompt created successfully",
            "prompt_id": prompt_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create custom prompt: {str(e)}")

@app.get("/custom-prompts", response_model=CustomPromptListResponse)
async def list_user_custom_prompts(
    user_id: str,
    manager: CustomPromptManager = Depends(get_custom_prompt_manager)
):
    """ユーザーのカスタムプロンプト一覧を取得"""
    try:
        prompts = manager.get_user_prompts(user_id)
        
        prompt_responses = []
        for prompt in prompts:
            prompt_responses.append(CustomPromptResponse(
                id=prompt['id'],
                name=prompt['name'],
                prompt_text=prompt['prompt_text'],
                description=prompt['description'],
                tags=prompt['tags'],
                user_id=prompt['user_id'],
                created_at=datetime.fromisoformat(prompt['created_at']),
                updated_at=datetime.fromisoformat(prompt['updated_at']),
                usage_count=prompt['usage_count'],
                is_active=prompt['is_active']
            ))
        
        return CustomPromptListResponse(
            prompts=prompt_responses,
            total_count=len(prompt_responses)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch custom prompts: {str(e)}")

@app.get("/custom-prompts/{prompt_id}", response_model=CustomPromptResponse)
async def get_custom_prompt(
    prompt_id: str,
    user_id: str,
    manager: CustomPromptManager = Depends(get_custom_prompt_manager)
):
    """特定のカスタムプロンプトを取得"""
    try:
        prompt = manager.get_custom_prompt(prompt_id)
        
        if not prompt:
            raise HTTPException(status_code=404, detail="Custom prompt not found")
        
        if prompt['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return CustomPromptResponse(
            id=prompt['id'],
            name=prompt['name'],
            prompt_text=prompt['prompt_text'],
            description=prompt['description'],
            tags=prompt['tags'],
            user_id=prompt['user_id'],
            created_at=datetime.fromisoformat(prompt['created_at']),
            updated_at=datetime.fromisoformat(prompt['updated_at']),
            usage_count=prompt['usage_count'],
            is_active=prompt['is_active']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch custom prompt: {str(e)}")

@app.put("/custom-prompts/{prompt_id}", response_model=dict)
async def update_custom_prompt(
    prompt_id: str,
    user_id: str,
    request: CustomPromptUpdateRequest,
    manager: CustomPromptManager = Depends(get_custom_prompt_manager)
):
    """カスタムプロンプトを更新"""
    try:
        success = manager.update_custom_prompt(
            prompt_id=prompt_id,
            user_id=user_id,
            name=request.name,
            prompt_text=request.prompt_text,
            description=request.description,
            tags=request.tags
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Custom prompt not found or access denied")
        
        return {
            "message": "Custom prompt updated successfully",
            "prompt_id": prompt_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update custom prompt: {str(e)}")

@app.delete("/custom-prompts/{prompt_id}", response_model=dict)
async def delete_custom_prompt(
    prompt_id: str,
    user_id: str,
    manager: CustomPromptManager = Depends(get_custom_prompt_manager)
):
    """カスタムプロンプトを削除"""
    try:
        success = manager.delete_custom_prompt(prompt_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Custom prompt not found or access denied")
        
        return {
            "message": "Custom prompt deleted successfully",
            "prompt_id": prompt_id
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
    custom_name: Optional[str] = None,
    manager: CustomPromptManager = Depends(get_custom_prompt_manager)
):
    """テンプレートからカスタムプロンプトを作成"""
    try:
        if template_name not in DEFAULT_PROMPT_TEMPLATES:
            raise HTTPException(status_code=404, detail="Template not found")
        
        template = DEFAULT_PROMPT_TEMPLATES[template_name]
        
        prompt_id = manager.create_custom_prompt(
            user_id=user_id,
            name=custom_name or template['name'],
            prompt_text=template['prompt_text'],
            description=template['description'],
            tags=template['tags']
        )
        
        return {
            "message": "Custom prompt created from template",
            "prompt_id": prompt_id,
            "template_name": template_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create prompt from template: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)