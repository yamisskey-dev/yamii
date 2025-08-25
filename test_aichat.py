import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

# aichat機能のテスト用データ型定義
class AiChatRequest:
    def __init__(self, question: str, prompt: str, api: str, key: str, 
                 from_mention: bool = True, friend_name: Optional[str] = None,
                 grounding: bool = False, history: Optional[List[Dict]] = None,
                 memory: Optional[Dict] = None):
        self.question = question
        self.prompt = prompt
        self.api = api
        self.key = key
        self.from_mention = from_mention
        self.friend_name = friend_name
        self.grounding = grounding
        self.history = history or []
        self.memory = memory

class Base64File:
    def __init__(self, file_type: str, base64_data: str, url: Optional[str] = None):
        self.type = file_type
        self.base64 = base64_data
        self.url = url

class AiChatResponse:
    def __init__(self, text: str, grounding_metadata: Optional[str] = None):
        self.text = text
        self.grounding_metadata = grounding_metadata

class TestAiChatService:
    """AIチャット機能のテストクラス"""
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Gemini APIのレスポンスをモック"""
        return {
            "candidates": [{
                "content": {
                    "parts": [{"text": "こんにちは！お元気ですか？ :smile:"}]
                },
                "groundingMetadata": {
                    "groundingChunks": [
                        {
                            "web": {
                                "uri": "https://example.com",
                                "title": "参考サイト"
                            }
                        }
                    ],
                    "webSearchQueries": ["天気 今日"]
                }
            }]
        }
    
    @pytest.fixture
    def sample_chat_request(self):
        """テスト用のチャットリクエスト"""
        return AiChatRequest(
            question="今日の天気はどうですか？",
            prompt="あなたは親しみやすいAIアシスタントです。",
            api="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent",
            key="test-api-key",
            from_mention=True,
            friend_name="テストユーザー",
            grounding=True
        )
    
    @pytest.mark.asyncio
    async def test_generate_text_by_gemini_basic(self, sample_chat_request, mock_gemini_response):
        """基本的なGeminiテキスト生成のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        files = []
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_gemini_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await service.generate_text_by_gemini(sample_chat_request, files, False)
            
            assert result is not None
            assert "こんにちは！お元気ですか？" in result
            assert ":smile:" in result
    
    @pytest.mark.asyncio
    async def test_generate_text_with_grounding(self, sample_chat_request, mock_gemini_response):
        """グラウンディング機能のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        files = []
        sample_chat_request.grounding = True
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_gemini_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await service.generate_text_by_gemini(sample_chat_request, files, False)
            
            assert result is not None
            assert "参考(1):" in result
            assert "検索ワード:" in result
    
    @pytest.mark.asyncio
    async def test_generate_text_with_files(self, sample_chat_request, mock_gemini_response):
        """画像ファイル付きテキスト生成のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        files = [Base64File("image/jpeg", "base64encodeddata", "https://example.com/image.jpg")]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_gemini_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await service.generate_text_by_gemini(sample_chat_request, files, False)
            
            assert result is not None
            assert "こんにちは！お元気ですか？" in result
    
    @pytest.mark.asyncio
    async def test_youtube_url_processing(self, sample_chat_request, mock_gemini_response):
        """YouTube URL処理のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        files = []
        sample_chat_request.question = "この動画について教えて https://www.youtube.com/watch?v=abc123"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_gemini_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await service.generate_text_by_gemini(sample_chat_request, files, False)
            
            assert result is not None
    
    def test_normalize_youtube_url(self):
        """YouTube URL正規化のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        
        # 通常のYouTube URL
        url1 = "https://www.youtube.com/watch?v=abc123"
        assert service.normalize_youtube_url(url1) == "https://www.youtube.com/watch?v=abc123"
        
        # youtu.be形式
        url2 = "https://youtu.be/abc123"
        assert service.normalize_youtube_url(url2) == "https://www.youtube.com/watch?v=abc123"
        
        # パラメータ付きURL
        url3 = "https://www.youtube.com/watch?v=abc123&t=30s"
        assert service.normalize_youtube_url(url3) == "https://www.youtube.com/watch?v=abc123"
    
    def test_is_youtube_url(self):
        """YouTube URL判定のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        
        assert service.is_youtube_url("https://www.youtube.com/watch?v=abc123") == True
        assert service.is_youtube_url("https://youtu.be/abc123") == True
        assert service.is_youtube_url("https://m.youtube.com/watch?v=abc123") == True
        assert service.is_youtube_url("https://google.com") == False
        assert service.is_youtube_url("https://example.com") == False
    
    def test_analyze_mood(self):
        """感情分析のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        
        # ポジティブな感情
        assert service.analyze_mood("嬉しいです :smile:") == "happy"
        assert service.analyze_mood("楽しい一日でした") == "happy"
        
        # ネガティブな感情
        assert service.analyze_mood("悲しいです :cry:") == "sad"
        assert service.analyze_mood("辛いことがありました") == "sad"
        
        # 怒りの感情
        assert service.analyze_mood("イライラします :angry:") == "angry"
        assert service.analyze_mood("怒っています") == "angry"
        
        # 不安な感情
        assert service.analyze_mood("心配です :worried:") == "anxious"
        assert service.analyze_mood("不安になります") == "anxious"
        
        # 中性
        assert service.analyze_mood("こんにちは") == "neutral"
    
    def test_calculate_importance(self):
        """重要度計算のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        
        # 基本的なメッセージ
        importance1 = service.calculate_importance("こんにちは")
        assert importance1 == 5  # デフォルト重要度
        
        # 感情的なメッセージ
        importance2 = service.calculate_importance("嬉しいです！")
        assert importance2 > 5
        
        # 質問形式のメッセージ
        importance3 = service.calculate_importance("これはどうですか？")
        assert importance3 > 5
        
        # 長いメッセージ
        long_message = "これは非常に長いメッセージです。" * 10
        importance4 = service.calculate_importance(long_message)
        assert importance4 > 5
    
    def test_extract_current_topic(self):
        """話題抽出のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        
        assert service.extract_current_topic("今日の天気はどうですか？") == "weather"
        assert service.extract_current_topic("仕事が忙しいです") == "work"
        assert service.extract_current_topic("映画を見ました") == "hobby"
        assert service.extract_current_topic("家族と過ごしました") == "family"
        assert service.extract_current_topic("こんにちは") == "general"
    
    def test_manage_human_like_memory(self):
        """人間らしい記憶管理のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        
        # 初期記憶
        memory = None
        new_conversation = {
            "id": "conv1",
            "userMessage": "今日は良い天気ですね",
            "aiResponse": "本当にそうですね！"
        }
        
        updated_memory = service.manage_human_like_memory(memory, new_conversation)
        
        assert updated_memory is not None
        assert len(updated_memory["conversations"]) == 1
        assert updated_memory["conversations"][0]["userMessage"] == "今日は良い天気ですね"
        assert updated_memory["conversationContext"]["currentTopic"] == "weather"
    
    def test_organize_memories(self):
        """記憶整理のテスト"""
        from navi.aichat import AiChatService
        
        service = AiChatService()
        
        # テスト用の会話履歴
        conversations = [
            {
                "id": "conv1",
                "timestamp": datetime.now().timestamp() - 86400 * 8,  # 8日前
                "userMessage": "古いメッセージ",
                "aiResponse": "返答",
                "importance": 3,
                "isActive": True
            },
            {
                "id": "conv2", 
                "timestamp": datetime.now().timestamp() - 3600,  # 1時間前
                "userMessage": "新しいメッセージ",
                "aiResponse": "返答",
                "importance": 8,
                "isActive": True
            }
        ]
        
        organized = service.organize_memories(conversations)
        
        # 古くて重要度の低いメッセージは非アクティブになる
        assert organized[0]["isActive"] == False
        # 新しくて重要度の高いメッセージはアクティブのまま
        assert organized[1]["isActive"] == True

class TestAiChatAPI:
    """AIチャットAPIのテストクラス"""
    
    @pytest.fixture
    async def client(self):
        """テスト用のFastAPIクライアント"""
        from fastapi.testclient import TestClient
        from navi.main import app
        
        return TestClient(app)
    
    def test_counseling_models_structure(self, client):
        """人生相談用データモデル構造テスト"""
        from navi.counseling_service import CounselingRequest, CounselingResponse
        
        # リクエストモデルのテスト
        request = CounselingRequest(
            message="テストメッセージ",
            user_id="test_user",
            user_name="テスト太郎"
        )
        assert request.message == "テストメッセージ"
        assert request.user_id == "test_user"
        assert request.user_name == "テスト太郎"
        
        # レスポンスモデルのテスト
        response = CounselingResponse(
            response="応答テスト",
            session_id="test_session",
            emotion_analysis={"primary_emotion": "neutral", "intensity": 1, "is_crisis": False, "all_emotions": {}},
            advice_type="general_support"
        )
        assert response.response == "応答テスト"
        assert response.session_id == "test_session"
        assert response.advice_type == "general_support"
    
    def test_counseling_health_endpoint(self, client):
        """人生相談ヘルスチェックエンドポイントのテスト"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_counseling_session_history(self, client):
        """人生相談セッション履歴のテスト（実際のエンドポイントはないが、メモリ機能をテスト）"""
        from navi.memory import MemorySystem
        
        memory_system = MemorySystem()
        memory_system.add_conversation(
            user_id="test_user",
            user_message="悩みがあります",
            ai_response="お聞きします",
            importance=7
        )
        
        context = memory_system.get_user_context("test_user")
        assert context is not None
        assert "悩みがあります" in context
    
    def test_counseling_emotion_analysis(self, client):
        """人生相談感情分析のテスト"""
        from navi.counseling_service import CounselingService
        
        service = CounselingService("test-api-key")
        
        # 悲しみの感情
        emotion = service.analyze_emotion("とても悲しいです")
        assert emotion["primary_emotion"] in ["sadness", "depression"]
        assert emotion["intensity"] >= 0
        
        # 不安の感情
        emotion2 = service.analyze_emotion("将来が不安です")
        assert emotion2["primary_emotion"] in ["anxiety", "stress"]
        assert emotion2["intensity"] >= 0

class TestMemorySystem:
    """記憶システムのテストクラス"""
    
    def test_memory_initialization(self):
        """記憶システム初期化のテスト"""
        from navi.memory import MemorySystem
        
        memory_system = MemorySystem()
        assert memory_system.conversations == []
        assert memory_system.user_profiles == {}
    
    def test_add_conversation(self):
        """会話追加のテスト"""
        from navi.memory import MemorySystem
        
        memory_system = MemorySystem()
        memory_system.add_conversation(
            user_id="test_user",
            user_message="こんにちは",
            ai_response="こんにちは！",
            importance=5
        )
        
        assert len(memory_system.conversations) == 1
        assert memory_system.conversations[0]["user_message"] == "こんにちは"
    
    def test_get_user_context(self):
        """ユーザーコンテキスト取得のテスト"""
        from navi.memory import MemorySystem
        
        memory_system = MemorySystem()
        memory_system.add_conversation(
            user_id="test_user", 
            user_message="天気について話しましょう",
            ai_response="はい、天気の話をしましょう！",
            importance=6
        )
        
        context = memory_system.get_user_context("test_user")
        assert context is not None
        assert "天気について話しましょう" in context

if __name__ == "__main__":
    pytest.main([__file__])