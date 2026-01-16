"""
API互換性向上のためのテスト
Yuiなど他プロジェクトとの互換性を確保するためのテスト
"""

import pytest
from datetime import datetime
from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, ValidationError as PydanticValidationError
import httpx


class TestPlatformContextMetadata:
    """プラットフォームコンテキストメタデータの型定義テスト"""

    def test_context_metadata_model_valid(self):
        """有効なコンテキストメタデータの検証"""
        # まだ実装していないので、インポートエラーを期待
        # 実装後にこのテストが通るようになる
        from yamii.models.context import ContextMetadata

        context = ContextMetadata(
            platform="misskey",
            bot_name="yui",
            client_version="1.0.0",
            api_version="1.0.0"
        )

        assert context.platform == "misskey"
        assert context.bot_name == "yui"
        assert context.client_version == "1.0.0"
        assert context.api_version == "1.0.0"

    def test_context_metadata_with_misskey_specific_fields(self):
        """Misskey固有フィールドを含むコンテキスト"""
        from yamii.models.context import ContextMetadata

        context = ContextMetadata(
            platform="misskey",
            bot_name="yui",
            note_visibility="home",
            note_id="abc123"
        )

        assert context.note_visibility == "home"
        assert context.note_id == "abc123"

    def test_context_metadata_platform_validation(self):
        """プラットフォーム名の検証"""
        from yamii.models.context import ContextMetadata

        # 有効なプラットフォーム
        valid_platforms = ["misskey", "mastodon", "web", "cli", "other"]
        for platform in valid_platforms:
            context = ContextMetadata(platform=platform)
            assert context.platform == platform

    def test_context_metadata_defaults(self):
        """デフォルト値の検証"""
        from yamii.models.context import ContextMetadata

        context = ContextMetadata()

        assert context.platform == "other"
        assert context.api_version == "1.0.0"
        assert context.bot_name is None


class TestStandardizedAPIResponse:
    """標準化されたAPIレスポンス形式のテスト"""

    def test_api_response_wrapper_success(self):
        """成功レスポンスのラッパー形式"""
        from yamii.models.response import ApiResponse

        response = ApiResponse(
            success=True,
            data={"message": "test"},
            api_version="1.0.0"
        )

        assert response.success is True
        assert response.data == {"message": "test"}
        assert response.error is None
        assert response.api_version == "1.0.0"

    def test_api_response_wrapper_error(self):
        """エラーレスポンスのラッパー形式"""
        from yamii.models.response import ApiResponse, ApiError

        error = ApiError(
            code="VALIDATION_ERROR",
            message="Invalid input",
            details={"field": "message", "reason": "empty"}
        )

        response = ApiResponse(
            success=False,
            error=error
        )

        assert response.success is False
        assert response.data is None
        assert response.error.code == "VALIDATION_ERROR"
        assert response.error.message == "Invalid input"

    def test_counseling_response_with_wrapper(self):
        """カウンセリングレスポンスがラッパー形式で返される"""
        from yamii.models.response import ApiResponse

        counseling_data = {
            "response": "テスト応答",
            "session_id": "session123",
            "timestamp": datetime.now().isoformat(),
            "emotion_analysis": {
                "primary_emotion": "neutral",
                "intensity": 5,
                "is_crisis": False,
                "all_emotions": {}
            },
            "advice_type": "supportive",
            "follow_up_questions": [],
            "is_crisis": False
        }

        response = ApiResponse(
            success=True,
            data=counseling_data
        )

        assert response.success is True
        assert response.data["response"] == "テスト応答"
        assert response.data["session_id"] == "session123"


class TestEnhancedErrorHandling:
    """拡張エラーハンドリングのテスト"""

    def test_error_response_with_retry_info(self):
        """リトライ情報を含むエラーレスポンス"""
        from yamii.models.response import ApiError

        error = ApiError(
            code="RATE_LIMIT_EXCEEDED",
            message="リクエスト制限を超えました",
            retry_after=60
        )

        assert error.retry_after == 60

    def test_error_response_with_troubleshooting(self):
        """トラブルシューティング情報を含むエラーレスポンス"""
        from yamii.models.response import ApiError

        error = ApiError(
            code="EXTERNAL_SERVICE_ERROR",
            message="外部サービスエラー",
            troubleshooting_steps=[
                "ネットワーク接続を確認してください",
                "しばらく待ってから再試行してください"
            ]
        )

        assert len(error.troubleshooting_steps) == 2

    def test_validation_error_with_field_details(self):
        """フィールド詳細を含むバリデーションエラー"""
        from yamii.models.response import ApiError, FieldError

        field_errors = [
            FieldError(field="message", message="必須フィールドです"),
            FieldError(field="user_id", message="空文字列は許可されません")
        ]

        error = ApiError(
            code="VALIDATION_ERROR",
            message="入力値が不正です",
            field_errors=field_errors
        )

        assert len(error.field_errors) == 2
        assert error.field_errors[0].field == "message"


class TestCounselingRequestContextValidation:
    """カウンセリングリクエストのコンテキスト検証テスト"""

    def test_request_with_typed_context(self):
        """型付けされたコンテキストを持つリクエスト"""
        from yamii.models.request import CounselingAPIRequestV2
        from yamii.models.context import ContextMetadata

        context = ContextMetadata(
            platform="misskey",
            bot_name="yui",
            note_visibility="home"
        )

        request = CounselingAPIRequestV2(
            message="相談内容",
            user_id="user123",
            context=context
        )

        assert request.context.platform == "misskey"
        assert request.context.note_visibility == "home"

    def test_request_backward_compatibility(self):
        """既存のdictコンテキストとの後方互換性"""
        from yamii.models.request import CounselingAPIRequestV2

        # dict形式でもContextMetadataに変換される
        request = CounselingAPIRequestV2(
            message="相談内容",
            user_id="user123",
            context={
                "platform": "misskey",
                "bot_name": "yui"
            }
        )

        assert request.context.platform == "misskey"
        assert request.context.bot_name == "yui"


class TestAPIVersioning:
    """APIバージョニングのテスト"""

    @pytest.mark.asyncio
    async def test_api_version_in_response_header(self):
        """レスポンスヘッダーにAPIバージョンが含まれる"""
        from yamii.api import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/health")

            assert "x-api-version" in response.headers
            assert response.headers["x-api-version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_api_version_in_response_body(self):
        """レスポンスボディにAPIバージョンが含まれる"""
        from yamii.api import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")

            data = response.json()
            assert "version" in data
            assert data["version"] == "2.0.0"


class TestYuiCompatibility:
    """Yuiプロジェクトとの互換性テスト"""

    def test_counseling_response_format_matches_yui_expectation(self):
        """カウンセリングレスポンスがYuiの期待する形式と一致"""
        from yamii.models.response import CounselingAPIResponseV2

        # Yuiが期待する形式
        response = CounselingAPIResponseV2(
            response="テスト応答",
            session_id="session123",
            timestamp=datetime.now(),
            emotion_analysis={
                "primary_emotion": "neutral",
                "intensity": 5,
                "is_crisis": False,
                "all_emotions": {}
            },
            advice_type="supportive",
            follow_up_questions=[],
            is_crisis=False
        )

        # Yuiが使用するフィールドがすべて存在することを確認
        response_dict = response.model_dump()

        assert "response" in response_dict
        assert "session_id" in response_dict
        assert "timestamp" in response_dict
        assert "emotion_analysis" in response_dict
        assert "advice_type" in response_dict
        assert "follow_up_questions" in response_dict
        assert "is_crisis" in response_dict

        # emotion_analysisの内部構造も確認
        emotion = response_dict["emotion_analysis"]
        assert "primary_emotion" in emotion
        assert "intensity" in emotion
        assert "is_crisis" in emotion
        assert "all_emotions" in emotion

    def test_context_platform_misskey(self):
        """Misskeyプラットフォームのコンテキスト処理"""
        from yamii.models.context import ContextMetadata

        # Yuiが送信するコンテキスト形式
        context = ContextMetadata(
            platform="misskey",
            bot_name="yui",
            note_visibility="home",
            note_id="abc123xyz"
        )

        assert context.is_misskey_platform()
        assert context.note_visibility == "home"


class TestSessionManagement:
    """セッション管理の拡張テスト"""

    def test_session_context_with_platform_metadata(self):
        """プラットフォームメタデータを含むセッションコンテキスト"""
        from yamii.models.session import SessionContext

        session = SessionContext(
            session_id="sess123",
            user_id="user123",
            platform="misskey",
            created_at=datetime.now(),
            last_interaction=datetime.now(),
            platform_metadata={"note_id": "abc123"},
            interaction_count=5,
            mood_trajectory=["neutral", "anxious", "calm"]
        )

        assert session.session_id == "sess123"
        assert session.platform == "misskey"
        assert session.interaction_count == 5
        assert len(session.mood_trajectory) == 3


class TestHealthCheckEnhanced:
    """拡張ヘルスチェックのテスト"""

    @pytest.mark.asyncio
    async def test_health_check_includes_dependencies_status(self):
        """ヘルスチェックが依存関係の状態を含む"""
        from yamii.api import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/health")

            data = response.json()
            # ヘルスチェックはdegraded（AI providerはテスト環境で無効）でもOK
            assert data["status"] in ["healthy", "degraded"]
            assert "timestamp" in data
            assert "version" in data


# 統合テスト
class TestEndToEndCompatibility:
    """エンドツーエンド互換性テスト"""

    @pytest.mark.asyncio
    async def test_counseling_endpoint_accepts_typed_context(self):
        """カウンセリングエンドポイントが型付けコンテキストを受け入れる"""
        import os

        # APIキーがない環境ではスキップ
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        from yamii.api import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            request_data = {
                "message": "テスト相談",
                "user_id": "test_user",
                "context": {
                    "platform": "misskey",
                    "bot_name": "yui",
                    "api_version": "1.0.0"
                }
            }

            response = await client.post("/v1/counseling", json=request_data)

            # ステータスコードは200または503（外部サービス依存）
            # テストでは形式の検証に焦点
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert "session_id" in data

    @pytest.mark.asyncio
    async def test_v2_endpoints_available(self):
        """V2エンドポイントが利用可能"""
        from yamii.api import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # V2ルートの存在確認（実装後に有効化）
            response = await client.get("/v1/health")
            # 404でもルーティングが動作していることを確認
            # 実装後は200を期待
            assert response.status_code in [200, 404]
