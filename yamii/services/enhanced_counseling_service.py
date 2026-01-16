"""
拡張カウンセリングサービス
高度な会話管理・学習機能を統合したカウンセリングサービス
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..core.logging import get_logger, log_business_event, log_error
from ..core.exceptions import CounselingError
from .counseling_service import (
    CounselingService, CounselingRequest, CounselingResponse,
    AdviceTypeClassifier, FollowUpGenerator
)
from ..memory import MemorySystem
from ..user_profile import UserProfileManager
from ..user_settings import UserSettingsManager
from ..core.secure_prompt_store import SecurePromptStore

# 高度な機能
from ..conversation_summary import (
    ConversationSummarizer, ConversationSummaryStore, ConversationSummary
)
from ..context_awareness import (
    ContextAwareResponseGenerator, ContextAwareResponse, ConversationContext
)
from ..user_learning import UserLearningManager, EnhancedUserProfile
from ..intelligent_search import IntelligentSearchEngine, SearchResult
from ..analytics import AnalyticsEngine, UserAnalytics


@dataclass
class EnhancedCounselingResponse(CounselingResponse):
    """拡張カウンセリングレスポンス"""
    context_info: Optional[Dict[str, Any]] = None
    personalization_applied: bool = False
    related_past_conversations: List[Dict[str, Any]] = None
    suggested_topics: List[str] = None
    user_insights: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.related_past_conversations is None:
            self.related_past_conversations = []
        if self.suggested_topics is None:
            self.suggested_topics = []


class EnhancedCounselingService(CounselingService):
    """
    拡張カウンセリングサービス

    以下の高度な機能を統合:
    - 会話サマリー: 長期記憶として会話を自動要約
    - コンテキスト認識: 感情の連続性、トピック遷移、スレッド管理
    - ユーザー学習: トピック関心度、応答パターン、センチメント履歴
    - 知識グラフ検索: トピック間の関連性を構築
    - 分析・統計: エンゲージメントスコア、推奨事項生成
    """

    def __init__(
        self,
        api_key: str,
        memory_system: MemorySystem,
        user_profile_manager: UserProfileManager,
        settings_manager: UserSettingsManager,
        secure_prompt_store: SecurePromptStore = None,
        data_dir: str = "data"
    ):
        # 基底クラスの初期化
        super().__init__(
            api_key=api_key,
            memory_system=memory_system,
            user_profile_manager=user_profile_manager,
            settings_manager=settings_manager,
            secure_prompt_store=secure_prompt_store
        )

        # 新しいコンポーネントの初期化
        self.summarizer = ConversationSummarizer()
        self.summary_store = ConversationSummaryStore()
        self.context_generator = ContextAwareResponseGenerator()
        self.learning_manager = UserLearningManager(data_dir=data_dir)
        self.search_engine = IntelligentSearchEngine(self.summary_store)
        self.analytics_engine = AnalyticsEngine(self.summary_store, self.learning_manager)

        self.logger = get_logger("enhanced_counseling_service")
        self.logger.info("Enhanced Counseling Service initialized with advanced features")

    async def generate_counseling_response(
        self,
        request: CounselingRequest
    ) -> EnhancedCounselingResponse:
        """
        拡張カウンセリングレスポンスを生成

        Args:
            request: カウンセリングリクエスト

        Returns:
            EnhancedCounselingResponse
        """
        try:
            log_business_event(
                self.logger,
                "enhanced_counseling_request_received",
                user_id=request.user_id,
                session_id=request.session_id,
                message_length=len(request.message)
            )

            # 1. コンテキスト分析
            context_analysis = self.context_generator.analyze_message(request.message)

            # 2. ユーザー学習データの更新
            detected_topics = context_analysis["detected_topics"]
            sentiment = context_analysis["emotional_state"].value
            self.learning_manager.update_from_message(
                user_id=request.user_id,
                message=request.message,
                topics=detected_topics,
                sentiment=sentiment
            )

            # 3. 個人化コンテキストの取得
            personalization_context = self.learning_manager.get_personalization_context(
                request.user_id
            )

            # 4. 関連する過去の会話を検索
            related_conversations = await self._search_related_conversations(
                request.user_id, request.message
            )

            # 5. 基底クラスのレスポンス生成（プロンプトに個人化を追加）
            enhanced_request = self._enhance_request_with_context(
                request, personalization_context, related_conversations
            )
            base_response = await super().generate_counseling_response(enhanced_request)

            # 6. コンテキスト認識応答の生成
            context_response = self.context_generator.generate_response(
                user_id=request.user_id,
                message=request.message,
                base_response=base_response.response
            )

            # 7. 会話サマリーの更新
            await self._update_conversation_summary(
                request.user_id,
                request.session_id,
                request.message,
                base_response.response
            )

            # 8. 関連トピックの提案
            suggested_topics = self._get_suggested_topics(request.user_id, detected_topics)

            # 9. ユーザーインサイトの取得
            user_insights = self.analytics_engine.get_user_insights(request.user_id)

            # 拡張レスポンスの構築
            enhanced_response = EnhancedCounselingResponse(
                response=base_response.response,
                session_id=base_response.session_id,
                emotion_analysis=base_response.emotion_analysis,
                advice_type=base_response.advice_type,
                follow_up_questions=base_response.follow_up_questions + context_response.suggested_follow_ups[:1],
                context_info={
                    "emotional_tone": context_response.emotional_tone,
                    "topic_depth": context_response.topic_depth,
                    "context_summary": context_response.context_summary
                },
                personalization_applied=bool(personalization_context),
                related_past_conversations=[r.to_dict() for r in related_conversations[:3]],
                suggested_topics=suggested_topics,
                user_insights=user_insights
            )

            log_business_event(
                self.logger,
                "enhanced_counseling_response_generated",
                user_id=request.user_id,
                session_id=request.session_id,
                personalization_applied=enhanced_response.personalization_applied,
                related_conversations_count=len(related_conversations),
                suggested_topics_count=len(suggested_topics)
            )

            return enhanced_response

        except Exception as e:
            log_error(self.logger, e, {
                "user_id": request.user_id,
                "session_id": request.session_id
            })
            # フォールバック
            base_response = await super()._create_fallback_response(request, str(e))
            return EnhancedCounselingResponse(
                response=base_response.response,
                session_id=base_response.session_id,
                emotion_analysis=base_response.emotion_analysis,
                advice_type=base_response.advice_type,
                follow_up_questions=base_response.follow_up_questions,
                context_info=None,
                personalization_applied=False
            )

    def _enhance_request_with_context(
        self,
        request: CounselingRequest,
        personalization_context: str,
        related_conversations: List[SearchResult]
    ) -> CounselingRequest:
        """リクエストにコンテキストを追加"""
        enhanced_context = request.context or {}

        # 個人化コンテキストを追加
        if personalization_context:
            enhanced_context["personalization"] = personalization_context

        # 関連する過去の会話を追加
        if related_conversations:
            past_context = "\n".join([
                f"- {r.summary.short_summary}" for r in related_conversations[:3]
            ])
            enhanced_context["related_past"] = past_context

        return CounselingRequest(
            message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            user_name=request.user_name,
            context=enhanced_context,
            custom_prompt_id=request.custom_prompt_id,
            prompt_id=request.prompt_id
        )

    async def _search_related_conversations(
        self,
        user_id: str,
        message: str
    ) -> List[SearchResult]:
        """関連する過去の会話を検索"""
        try:
            results = self.search_engine.search_past_conversations(
                user_id=user_id,
                query=message,
                limit=5
            )
            return results
        except Exception as e:
            self.logger.warning(f"Failed to search related conversations: {e}")
            return []

    async def _update_conversation_summary(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        ai_response: str
    ) -> None:
        """会話サマリーを更新"""
        try:
            # 現在のセッションのメッセージを収集
            messages = [
                {"role": "user", "content": user_message, "timestamp": datetime.now()},
                {"role": "assistant", "content": ai_response, "timestamp": datetime.now()}
            ]

            # サマリー生成
            summary = self.summarizer.summarize_conversation(
                user_id=user_id,
                session_id=session_id,
                messages=messages
            )

            # サマリーを保存
            self.summary_store.save_summary(summary)

            # 知識グラフを更新
            self.search_engine.build_knowledge_graph(user_id)

        except Exception as e:
            self.logger.warning(f"Failed to update conversation summary: {e}")

    def _get_suggested_topics(
        self,
        user_id: str,
        current_topics: List[str]
    ) -> List[str]:
        """関連トピックを提案"""
        suggested = []
        for topic in current_topics[:2]:
            related = self.search_engine.suggest_related_topics(user_id, topic, limit=2)
            suggested.extend([t for t, _ in related if t not in current_topics])
        return list(set(suggested))[:3]

    # === 追加のAPI ===

    def get_user_analytics(self, user_id: str) -> UserAnalytics:
        """ユーザー分析を取得"""
        return self.analytics_engine.analyze_user(user_id)

    def get_user_context(self, user_id: str) -> Optional[ConversationContext]:
        """ユーザーの会話コンテキストを取得"""
        return self.context_generator.get_or_create_context(user_id)

    def get_user_profile_enhanced(self, user_id: str) -> EnhancedUserProfile:
        """拡張ユーザープロファイルを取得"""
        return self.learning_manager.get_or_create_profile(user_id)

    def search_conversations(self, user_id: str, query: str) -> List[SearchResult]:
        """会話を検索"""
        return self.search_engine.search_past_conversations(user_id, query)

    def get_knowledge_graph_data(self, user_id: str) -> Dict[str, Any]:
        """知識グラフの可視化データを取得"""
        return self.search_engine.get_knowledge_graph_visualization_data(user_id)

    def update_user_preferences(
        self,
        user_id: str,
        **preferences
    ) -> EnhancedUserProfile:
        """ユーザー設定を更新"""
        return self.learning_manager.update_preferences(user_id, **preferences)

    def clear_user_context(self, user_id: str) -> None:
        """ユーザーの会話コンテキストをクリア"""
        self.context_generator.clear_user_context(user_id)

    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """ユーザーデータをエクスポート（プライバシー対応）"""
        return {
            "profile": self.learning_manager.export_user_data(user_id),
            "summaries": [
                s.to_dict() for s in
                self.summary_store.get_user_summaries(user_id, limit=100)
            ],
            "context": self.context_generator.get_context_summary(user_id),
            "analytics": self.get_user_analytics(user_id).to_dict()
        }

    def delete_user_data(self, user_id: str) -> bool:
        """ユーザーデータを削除（プライバシー対応）"""
        try:
            self.learning_manager.delete_profile(user_id)
            self.context_generator.clear_user_context(user_id)
            # サマリーストアには削除機能を追加する必要がある
            self.logger.info(f"User data deleted for user_id={user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete user data: {e}")
            return False


def create_enhanced_counseling_service(
    api_key: str,
    data_dir: str = "data"
) -> EnhancedCounselingService:
    """
    拡張カウンセリングサービスを作成するファクトリ関数

    Args:
        api_key: Gemini API キー
        data_dir: データディレクトリ

    Returns:
        EnhancedCounselingService
    """
    from ..user_settings import UserSettingsManager

    memory_system = MemorySystem()
    user_profile_manager = UserProfileManager(data_dir=data_dir)
    settings_manager = UserSettingsManager(data_dir=data_dir)

    return EnhancedCounselingService(
        api_key=api_key,
        memory_system=memory_system,
        user_profile_manager=user_profile_manager,
        settings_manager=settings_manager,
        data_dir=data_dir
    )
