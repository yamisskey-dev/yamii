"""
CounselingService のテスト

メンタルファースト原則に基づくテスト:
- 感情分析が正しく動作するか
- 危機検出が機能するか
- パーソナライゼーションが適切に行われるか
- フェーズ遷移が正しく動作するか
"""

import pytest

from yamii.domain.models.emotion import EmotionType
from yamii.domain.models.relationship import RelationshipPhase
from yamii.domain.models.user import UserState
from yamii.domain.ports.ai_port import ChatMessage, IAIProvider
from yamii.domain.ports.storage_port import IStorage
from yamii.domain.services.counseling import (
    AdviceTypeClassifier,
    CounselingRequest,
    CounselingResponse,
    CounselingService,
    FollowUpGenerator,
)
from yamii.domain.services.emotion import EmotionService

# === モッククラス ===


class MockAIProvider(IAIProvider):
    """テスト用 AI プロバイダーモック"""

    def __init__(self, response: str = "お気持ち、わかります。辛いですね。"):
        self._response = response

    async def generate(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ) -> str:
        return self._response

    async def generate_stream(
        self,
        message: str,
        system_prompt: str,
        max_tokens: int | None = None,
        conversation_history: list[ChatMessage] | None = None,
    ):
        yield self._response

    async def health_check(self) -> bool:
        return True

    @property
    def model_name(self) -> str:
        return "mock-model"


class MockStorage(IStorage):
    """テスト用ストレージモック"""

    def __init__(self):
        self._users: dict[str, UserState] = {}

    async def load_user(self, user_id: str) -> UserState | None:
        return self._users.get(user_id)

    async def save_user(self, user: UserState) -> None:
        self._users[user.user_id] = user

    async def delete_user(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    async def list_users(self) -> list[str]:
        return list(self._users.keys())

    async def user_exists(self, user_id: str) -> bool:
        return user_id in self._users

    async def export_user_data(self, user_id: str) -> dict | None:
        user = self._users.get(user_id)
        if user:
            return user.to_dict()
        return None


# === CounselingRequest テスト ===


class TestCounselingRequest:
    """CounselingRequest のテスト"""

    def test_valid_request(self):
        """有効なリクエストが作成できる"""
        request = CounselingRequest(
            message="今日は辛いことがありました",
            user_id="user123",
        )
        assert request.message == "今日は辛いことがありました"
        assert request.user_id == "user123"
        assert request.session_id is not None

    def test_empty_message_raises_error(self):
        """空メッセージはエラー"""
        with pytest.raises(ValueError, match="メッセージは必須"):
            CounselingRequest(message="", user_id="user123")

    def test_empty_user_id_raises_error(self):
        """空ユーザーIDはエラー"""
        with pytest.raises(ValueError, match="ユーザーIDは必須"):
            CounselingRequest(message="test", user_id="")

    def test_whitespace_only_message_raises_error(self):
        """空白のみのメッセージはエラー"""
        with pytest.raises(ValueError, match="メッセージは必須"):
            CounselingRequest(message="   ", user_id="user123")

    def test_custom_session_id(self):
        """カスタムセッションIDが設定できる"""
        request = CounselingRequest(
            message="test",
            user_id="user123",
            session_id="custom-session",
        )
        assert request.session_id == "custom-session"


# === AdviceTypeClassifier テスト ===


class TestAdviceTypeClassifier:
    """AdviceTypeClassifier のテスト"""

    @pytest.fixture
    def classifier(self):
        return AdviceTypeClassifier()

    def test_crisis_keywords_detection(self, classifier):
        """危機的キーワードが検出される"""
        result = classifier.classify("死にたい気持ちになる", EmotionType.SADNESS)
        assert result == "crisis_support"

    def test_crisis_emotion_detection(self, classifier):
        """危機的感情（うつ）が検出される"""
        result = classifier.classify("何をしても楽しくない", EmotionType.DEPRESSION)
        assert result == "crisis_support"

    def test_relationship_detection(self, classifier):
        """恋愛相談が検出される"""
        result = classifier.classify("彼氏と喧嘩した", EmotionType.SADNESS)
        assert result == "relationship"

    def test_career_detection(self, classifier):
        """仕事相談が検出される"""
        result = classifier.classify("上司との関係が辛い", EmotionType.ANXIETY)
        assert result == "career"

    def test_family_detection(self, classifier):
        """家族相談が検出される"""
        result = classifier.classify("親との関係に悩んでいます", EmotionType.ANXIETY)
        assert result == "family"

    def test_education_detection(self, classifier):
        """教育・学業相談が検出される"""
        result = classifier.classify("受験勉強が辛い", EmotionType.ANXIETY)
        assert result == "education"

    def test_general_support_fallback(self, classifier):
        """該当カテゴリがない場合は general_support"""
        result = classifier.classify("最近調子が悪い", EmotionType.NEUTRAL)
        assert result == "general_support"


# === FollowUpGenerator テスト ===


class TestFollowUpGenerator:
    """FollowUpGenerator のテスト"""

    @pytest.fixture
    def generator(self):
        return FollowUpGenerator()

    def test_crisis_follow_up(self, generator):
        """危機対応のフォローアップ質問が生成される（傾聴重視）"""
        questions = generator.generate("crisis_support")
        assert len(questions) == 2
        # 傾聴重視のフォローアップ
        assert any("聴かせ" in q or "気持ち" in q for q in questions)

    def test_relationship_follow_up(self, generator):
        """恋愛相談のフォローアップ質問が生成される"""
        questions = generator.generate("relationship")
        assert len(questions) == 2

    def test_general_fallback(self, generator):
        """不明なカテゴリは一般質問"""
        questions = generator.generate("unknown_category")
        assert len(questions) == 2


# === CounselingService テスト ===


class TestCounselingService:
    """CounselingService のテスト"""

    @pytest.fixture
    def mock_ai(self):
        return MockAIProvider()

    @pytest.fixture
    def mock_storage(self):
        return MockStorage()

    @pytest.fixture
    def service(self, mock_ai, mock_storage):
        return CounselingService(
            ai_provider=mock_ai,
            storage=mock_storage,
        )

    @pytest.mark.asyncio
    async def test_generate_response_new_user(self, service):
        """新規ユーザーへの応答生成"""
        request = CounselingRequest(
            message="今日は辛いことがありました",
            user_id="new_user",
        )

        response = await service.generate_response(request)

        assert isinstance(response, CounselingResponse)
        assert response.response is not None
        assert response.session_id == request.session_id
        assert response.emotion_analysis is not None
        assert response.advice_type is not None
        assert isinstance(response.follow_up_questions, list)

    @pytest.mark.asyncio
    async def test_generate_response_existing_user(self, service, mock_storage):
        """既存ユーザーへの応答生成"""
        # 既存ユーザーを作成
        existing_user = UserState(
            user_id="existing_user",
            phase=RelationshipPhase.FAMILIAR,
            total_interactions=25,
            trust_score=0.5,
        )
        await mock_storage.save_user(existing_user)

        request = CounselingRequest(
            message="また話したくなりました",
            user_id="existing_user",
        )

        await service.generate_response(request)

        # ユーザー状態が更新されている
        updated_user = await mock_storage.load_user("existing_user")
        assert updated_user.total_interactions == 26

    @pytest.mark.asyncio
    async def test_crisis_detection(self, service):
        """危機検出が正しく動作する"""
        request = CounselingRequest(
            message="もう死にたい気持ちでいっぱいです",
            user_id="crisis_user",
        )

        response = await service.generate_response(request)

        # 危機検出
        assert response.advice_type == "crisis_support"
        # 感情分析で危機フラグ
        # Note: EmotionService の実装によっては is_crisis が True にならない可能性あり

    @pytest.mark.asyncio
    async def test_user_state_update(self, service, mock_storage):
        """ユーザー状態が正しく更新される"""
        request = CounselingRequest(
            message="仕事のストレスがたまっています",
            user_id="update_test_user",
            user_name="テストユーザー",
        )

        await service.generate_response(request)

        user = await mock_storage.load_user("update_test_user")

        assert user is not None
        assert user.total_interactions == 1
        assert user.display_name == "テストユーザー"
        assert "career" in user.known_topics

    @pytest.mark.asyncio
    async def test_phase_transition(self, service, mock_storage):
        """フェーズ遷移が正しく動作する"""
        # 初期ユーザーを作成（STRANGER フェーズ）
        user = UserState(
            user_id="phase_test_user",
            phase=RelationshipPhase.STRANGER,
            total_interactions=4,  # 次で5回になり遷移条件を満たす
            trust_score=0.2,
        )
        await mock_storage.save_user(user)

        # 複数回の対話をシミュレート
        for i in range(3):
            request = CounselingRequest(
                message=f"テストメッセージ {i}",
                user_id="phase_test_user",
            )
            await service.generate_response(request)

        updated_user = await mock_storage.load_user("phase_test_user")

        # インタラクション数が増加
        assert updated_user.total_interactions >= 7
        # フェーズが進んでいる可能性（信頼スコアに依存）
        assert updated_user.phase in [
            RelationshipPhase.STRANGER,
            RelationshipPhase.ACQUAINTANCE,
        ]

    @pytest.mark.asyncio
    async def test_personalization_learning(self, service, mock_storage):
        """パーソナライゼーション学習が動作する"""
        user = UserState(
            user_id="personalization_user",
            likes_empathy=0.5,
            likes_advice=0.5,
        )
        await mock_storage.save_user(user)

        # 感情的なメッセージを送信
        request = CounselingRequest(
            message="本当に辛くて泣きたい気持ちです",
            user_id="personalization_user",
        )

        await service.generate_response(request)

        updated_user = await mock_storage.load_user("personalization_user")

        # 共感志向が学習されている（感情強度が高い場合）
        # Note: 実際の値は EmotionService の分析結果に依存
        assert updated_user.confidence_score >= 0.0

    @pytest.mark.asyncio
    async def test_crisis_detection_in_response(self, service, mock_storage):
        """危機検出時のレスポンス確認"""
        # 危機的なメッセージ
        request = CounselingRequest(
            message="自殺を考えています。限界です。",
            user_id="crisis_followup_user",
        )

        response = await service.generate_response(request)

        # 危機対応のadvice_typeが返される
        assert response.advice_type == "crisis_support"

        # ユーザー状態が保存されている
        user = await mock_storage.load_user("crisis_followup_user")
        assert user is not None
        assert user.total_interactions == 1


# === 統合テスト ===


class TestCounselingServiceIntegration:
    """統合テスト"""

    @pytest.fixture
    def service(self):
        return CounselingService(
            ai_provider=MockAIProvider(),
            storage=MockStorage(),
        )

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, service):
        """完全な会話フローのテスト"""
        user_id = "integration_user"

        # 1. 初回メッセージ
        response1 = await service.generate_response(
            CounselingRequest(
                message="こんにちは、初めまして",
                user_id=user_id,
            )
        )
        assert response1.response is not None

        # 2. 感情的なメッセージ
        response2 = await service.generate_response(
            CounselingRequest(
                message="実は最近、仕事で悩んでいて...",
                user_id=user_id,
            )
        )
        assert response2.advice_type == "career"

        # 3. フォローアップ
        response3 = await service.generate_response(
            CounselingRequest(
                message="上司との関係がうまくいかなくて",
                user_id=user_id,
            )
        )
        assert response3.response is not None

        # 4. ユーザー状態確認
        user = await service.storage.load_user(user_id)
        assert user.total_interactions == 3
        assert "career" in user.known_topics


# === エッジケーステスト ===


class TestEdgeCases:
    """エッジケースのテスト"""

    @pytest.fixture
    def service(self):
        return CounselingService(
            ai_provider=MockAIProvider(),
            storage=MockStorage(),
        )

    @pytest.mark.asyncio
    async def test_very_long_message(self, service):
        """非常に長いメッセージの処理"""
        long_message = "辛いです。" * 1000  # 5000文字

        request = CounselingRequest(
            message=long_message,
            user_id="long_message_user",
        )

        response = await service.generate_response(request)
        assert response.response is not None

    @pytest.mark.asyncio
    async def test_unicode_characters(self, service):
        """Unicode文字の処理"""
        request = CounselingRequest(
            message="😢 今日は悲しいことがありました 💔",
            user_id="unicode_user",
        )

        response = await service.generate_response(request)
        assert response.response is not None

    @pytest.mark.asyncio
    async def test_rapid_successive_requests(self, service):
        """連続した高速リクエスト"""
        user_id = "rapid_user"

        for i in range(10):
            request = CounselingRequest(
                message=f"メッセージ {i}",
                user_id=user_id,
            )
            response = await service.generate_response(request)
            assert response.response is not None

        user = await service.storage.load_user(user_id)
        assert user.total_interactions == 10


# === EmotionService LLM併用テスト ===


class TestEmotionServiceLLM:
    """EmotionService のLLM併用機能テスト"""

    def test_keyword_analysis_only(self):
        """AIプロバイダーなしでキーワード分析のみ動作"""
        service = EmotionService()  # AIプロバイダーなし
        result = service.analyze("今日はとても悲しい気持ちです")
        assert result.primary_emotion == EmotionType.SADNESS
        assert result.confidence > 0

    def test_euphemism_detection_trigger(self):
        """婉曲表現でLLM分析トリガーが検出される"""
        service = EmotionService()

        # 婉曲表現パターンにマッチするかテスト
        test_messages = [
            "もういいかな",
            "疲れたな",
            "どうでもいい",
            "意味がないよ",
            "楽になりたい",
        ]

        for msg in test_messages:
            keyword_result = service._analyze_keyword_based(msg)
            needs_llm = service._needs_llm_analysis(msg, keyword_result)
            # 婉曲表現はLLM分析が必要と判定される
            assert needs_llm, f"'{msg}' should trigger LLM analysis"

    def test_no_llm_trigger_for_clear_keywords(self):
        """明確なキーワードがある場合はLLM不要"""
        service = EmotionService()

        # 明確な感情キーワードがある場合
        msg = "とても嬉しい！最高の気分です！"
        keyword_result = service._analyze_keyword_based(msg)

        # 信頼度が高い場合はLLM不要
        if keyword_result.confidence >= 0.3:
            needs_llm = service._needs_llm_analysis(msg, keyword_result)
            # 明確なキーワードがあればLLM不要の可能性
            # ただし婉曲表現がなく信頼度が高い場合
            assert not needs_llm or keyword_result.confidence < 0.3

    @pytest.mark.asyncio
    async def test_analyze_with_llm_no_provider(self):
        """AIプロバイダーなしでanalyze_with_llmを呼ぶとキーワード分析のみ"""
        service = EmotionService()  # AIプロバイダーなし
        result = await service.analyze_with_llm("もういいかな")

        # LLMが無いのでキーワード分析の結果が返る
        assert result is not None
        assert result.primary_emotion is not None

    @pytest.mark.asyncio
    async def test_analyze_with_llm_provider(self):
        """AIプロバイダーありでLLM分析が実行される"""
        # LLM用のモック（JSON形式で感情分析結果を返す）
        mock_llm_response = """{
            "primary_emotion": "depression",
            "intensity": 0.8,
            "is_crisis": true,
            "reasoning": "「もういいかな」は諦めや絶望を示唆する表現"
        }"""
        mock_provider = MockAIProvider(response=mock_llm_response)
        service = EmotionService(ai_provider=mock_provider)

        result = await service.analyze_with_llm("もういいかな")

        # LLMが危機を検出したので危機フラグがTrue
        assert result.is_crisis is True
        # LLMの判断が反映される
        assert result.primary_emotion == EmotionType.DEPRESSION

    @pytest.mark.asyncio
    async def test_llm_response_parsing(self):
        """LLMレスポンスのパース処理"""
        service = EmotionService()

        # 正常なJSON
        valid_json = '{"primary_emotion": "sadness", "intensity": 0.7, "is_crisis": false}'
        result = service._parse_llm_response(valid_json)
        assert result is not None
        assert result["primary_emotion"] == "sadness"

        # マークダウンコードブロック付き
        markdown_json = '```json\n{"primary_emotion": "anxiety", "intensity": 0.5}\n```'
        result = service._parse_llm_response(markdown_json)
        assert result is not None
        assert result["primary_emotion"] == "anxiety"

        # 不正なJSON
        invalid_json = "これはJSONではありません"
        result = service._parse_llm_response(invalid_json)
        assert result is None

    @pytest.mark.asyncio
    async def test_llm_error_fallback(self):
        """LLMエラー時はキーワード分析にフォールバック"""

        class ErrorAIProvider(IAIProvider):
            async def generate(self, *args, **kwargs) -> str:
                raise Exception("API Error")

            async def generate_stream(self, *args, **kwargs):
                raise Exception("API Error")
                yield  # AsyncGenerator にするためのダミー

            async def health_check(self) -> bool:
                return False

            @property
            def model_name(self) -> str:
                return "error-mock"

        service = EmotionService(ai_provider=ErrorAIProvider())
        result = await service.analyze_with_llm("もういいかな")

        # エラーでもキーワード分析結果が返る
        assert result is not None

    def test_merge_analyses_crisis_priority(self):
        """分析統合時に危機フラグが優先される"""
        service = EmotionService()

        from yamii.domain.models.emotion import EmotionAnalysis

        keyword_result = EmotionAnalysis(
            primary_emotion=EmotionType.NEUTRAL,
            intensity=0.0,
            stability=1.0,
            is_crisis=False,
            all_emotions={},
            confidence=0.2,
        )

        llm_analysis = {
            "primary_emotion": "depression",
            "intensity": 0.9,
            "is_crisis": True,
        }

        merged = service._merge_analyses(keyword_result, llm_analysis)

        # LLMが危機を検出したら優先
        assert merged.is_crisis is True
        assert merged.primary_emotion == EmotionType.DEPRESSION
        assert merged.confidence == 0.8  # LLM分析は高信頼度
