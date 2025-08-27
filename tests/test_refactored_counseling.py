"""
リファクタリング版カウンセリング機能のテスト
クリーンアーキテクチャに対応したテスト設計
"""

import pytest
import asyncio
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path

from navi.services.emotion_service import EmotionAnalysisService, EmotionType
from navi.services.counseling_service import (
    CounselingService, CounselingRequest, CounselingResponse,
    AdviceTypeClassifier, FollowUpGenerator
)
from navi.core.exceptions import ValidationError, ExternalServiceError
from navi.memory import MemorySystem
from navi.user_profile import UserProfileManager
from navi.user_settings import UserSettingsManager
from navi.core.secure_prompt_store import SecurePromptStore, get_secure_prompt_store
from navi.core.encryption import get_e2ee_crypto, get_key_manager


class TestEmotionAnalysisService:
    """感情分析サービスのテスト"""
    
    def setup_method(self):
        self.emotion_service = EmotionAnalysisService()
    
    def test_analyze_basic_emotions(self):
        """基本感情分析のテスト"""
        # 幸福
        analysis = self.emotion_service.analyze_emotion("今日はとても嬉しいです")
        assert analysis.primary_emotion == EmotionType.HAPPINESS
        assert analysis.intensity > 0
        assert not analysis.is_crisis
        
        # 悲しみ
        analysis = self.emotion_service.analyze_emotion("悲しくて辛いです")
        assert analysis.primary_emotion == EmotionType.SADNESS
        assert analysis.intensity > 0
        
        # 不安
        analysis = self.emotion_service.analyze_emotion("とても心配で不安です")
        assert analysis.primary_emotion == EmotionType.ANXIETY
        assert analysis.intensity > 0
    
    def test_crisis_detection(self):
        """危機状況検出のテスト"""
        crisis_messages = [
            "死にたいです",
            "もう消えたい",
            "生きる意味がない",
            "もう限界です"
        ]
        
        for message in crisis_messages:
            analysis = self.emotion_service.analyze_emotion(message)
            assert analysis.is_crisis, f"Crisis not detected for: {message}"
    
    def test_empty_message_validation(self):
        """空メッセージのバリデーション"""
        with pytest.raises(ValidationError):
            self.emotion_service.analyze_emotion("")
        
        with pytest.raises(ValidationError):
            self.emotion_service.analyze_emotion("   ")
    
    def test_confidence_calculation(self):
        """信頼度計算のテスト"""
        # 明確な感情表現
        analysis1 = self.emotion_service.analyze_emotion("とても嬉しくて楽しくて最高です")
        
        # 曖昧な表現
        analysis2 = self.emotion_service.analyze_emotion("こんにちは")
        
        assert analysis1.confidence > analysis2.confidence


class TestAdviceTypeClassifier:
    """アドバイスタイプ分類器のテスト"""
    
    def setup_method(self):
        self.classifier = AdviceTypeClassifier()
    
    def test_crisis_classification(self):
        """危機状況の分類"""
        result = self.classifier.classify("死にたいです", EmotionType.DEPRESSION)
        assert result == "crisis_support"
    
    def test_relationship_classification(self):
        """恋愛関係の分類"""
        result = self.classifier.classify("彼女と喧嘩しました", EmotionType.SADNESS)
        assert result == "relationship"
    
    def test_career_classification(self):
        """キャリア関連の分類"""
        result = self.classifier.classify("仕事で悩んでいます", EmotionType.STRESS)
        assert result == "career"
    
    def test_general_fallback(self):
        """一般サポートへのフォールバック"""
        result = self.classifier.classify("普通の相談です", EmotionType.NEUTRAL)
        assert result == "general_support"


class TestFollowUpGenerator:
    """フォローアップ質問生成器のテスト"""
    
    def setup_method(self):
        self.generator = FollowUpGenerator()
    
    def test_crisis_support_questions(self):
        """危機サポート用質問の生成"""
        questions = self.generator.generate("crisis_support", EmotionType.DEPRESSION)
        assert len(questions) <= 2  # 危機時は質問数を制限
        assert any("信頼できる人" in q for q in questions)
    
    def test_general_support_questions(self):
        """一般サポート用質問の生成"""
        questions = self.generator.generate("general_support", EmotionType.NEUTRAL)
        assert len(questions) <= 2
        assert len(questions) > 0


class TestCounselingService:
    """統合されたカウンセリングサービスのテスト"""
    
    def setup_method(self):
        # テスト用の一時ディレクトリ
        self.test_dir = tempfile.mkdtemp()
        self.test_db = str(Path(self.test_dir) / "test.db")
        self.test_key = str(Path(self.test_dir) / "test.key")
        
        # 依存関係のセットアップ
        self.memory_system = MemorySystem()
        self.user_profile_manager = UserProfileManager(self.test_dir)
        self.settings_manager = UserSettingsManager(self.test_db, self.test_key)
        self.prompt_store = get_prompt_store()
        
        # カウンセリングサービス
        self.counseling_service = CounselingService(
            api_key="test_api_key",
            memory_system=self.memory_system,
            user_profile_manager=self.user_profile_manager,
            settings_manager=self.settings_manager,
            prompt_store=self.prompt_store
        )
    
    def teardown_method(self):
        shutil.rmtree(self.test_dir)
    
    def test_counseling_request_validation(self):
        """カウンセリングリクエストのバリデーション"""
        # 正常なリクエスト
        request = CounselingRequest(
            message="テストメッセージ",
            user_id="test_user"
        )
        assert request.message == "テストメッセージ"
        assert request.user_id == "test_user"
        assert request.session_id is not None  # 自動生成される
        
        # 空メッセージでエラー
        with pytest.raises(ValidationError):
            CounselingRequest(message="", user_id="test_user")
        
        # 空ユーザーIDでエラー
        with pytest.raises(ValidationError):
            CounselingRequest(message="テスト", user_id="")
    
    @pytest.mark.asyncio
    async def test_counseling_response_generation_with_mock(self):
        """モックを使用したカウンセリングレスポンス生成のテスト"""
        request = CounselingRequest(
            message="最近悩みがあります",
            user_id="test_user"
        )
        
        # Gemini APIをモック
        mock_response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "お話を聞かせてください。どのようなことでお悩みですか？"}]
                }
            }]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value.__aenter__.return_value = mock_response
            
            response = await self.counseling_service.generate_counseling_response(request)
            
            assert isinstance(response, CounselingResponse)
            assert response.session_id == request.session_id
            assert response.advice_type in ['general_support', 'mental_health']
            assert len(response.follow_up_questions) > 0
    
    @pytest.mark.asyncio
    async def test_external_service_error_handling(self):
        """外部サービスエラーハンドリングのテスト"""
        request = CounselingRequest(
            message="テスト",
            user_id="test_user"
        )
        
        # APIエラーをシミュレート
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_post.return_value.__aenter__.return_value = mock_response
            
            response = await self.counseling_service.generate_counseling_response(request)
            
            # フォールバック応答が返される
            assert "申し訳ありません" in response.response
            assert response.advice_type == "general_support"
    
    def test_prompt_selection_priority(self):
        """プロンプト選択優先度のテスト"""
        user_id = "test_user"
        
        # カスタムプロンプトを設定
        self.settings_manager.save_custom_prompt(
            user_id=user_id,
            name="テストプロンプト",
            prompt_text="あなたはテスト用のカウンセラーです。"
        )
        
        request = CounselingRequest(
            message="相談があります",
            user_id=user_id
        )
        
        # プロンプト取得をテスト（非同期メソッドを同期的にテスト）
        prompt = asyncio.run(
            self.counseling_service._get_system_prompt(
                request, 
                Mock(primary_emotion=EmotionType.NEUTRAL, intensity=1, is_crisis=False, confidence=0.5),
                "general_support"
            )
        )
        
        assert "テスト用のカウンセラー" in prompt
    
    def test_memory_integration(self):
        """メモリシステム統合のテスト"""
        # 会話を追加
        self.memory_system.add_conversation(
            user_id="test_user",
            user_message="前回の相談内容",
            ai_response="前回の応答",
            importance=5
        )
        
        # メモリが正しく保存されているか確認
        context = self.memory_system.get_user_context("test_user")
        assert "前回の相談内容" in context


class TestIntegrationWithAPI:
    """API統合テスト"""
    
    def test_fastapi_integration(self):
        """FastAPI統合のテスト"""
        from fastapi.testclient import TestClient
        from navi.main import app
        
        client = TestClient(app)
        
        # ヘルスチェック
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'test_api_key'})
    def test_error_handling_integration(self):
        """エラーハンドリング統合テスト"""
        from fastapi.testclient import TestClient
        from navi.main import app
        
        client = TestClient(app)
        
        # 不正なリクエスト
        response = client.post("/counseling", json={
            "message": "",  # 空メッセージ
            "user_id": "test_user"
        })
        
        assert response.status_code == 400  # Custom validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])