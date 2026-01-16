"""
適応型カウンセリングサービス
関係性記憶システムを使用し、対話を通じてユーザーに適応するカウンセリングサービス

設計思想:
- 初期設定不要でシンプルなユーザー体験
- 対話を重ねるごとにユーザーの好みを学習
- 関係性フェーズに応じた対応の変化
- エピソード記憶による長期的な関係構築
"""

import aiohttp
import uuid
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..core.logging import get_logger, log_business_event, log_error
from ..core.exceptions import ExternalServiceError, ValidationError
from .emotion_service import EmotionAnalysisService, EmotionType
from ..memory import MemorySystem
from ..relationship import (
    RelationshipMemorySystem,
    get_relationship_memory,
    RelationshipPhase,
)


@dataclass
class AdaptiveCounselingRequest:
    """適応型カウンセリングリクエスト"""
    message: str
    user_id: str
    session_id: Optional[str] = None
    user_name: Optional[str] = None
    custom_instructions: Optional[str] = None  # 一時的なカスタム指示

    def __post_init__(self):
        if not self.message or not self.message.strip():
            raise ValidationError("メッセージは必須です", field="message")
        if not self.user_id or not self.user_id.strip():
            raise ValidationError("ユーザーIDは必須です", field="user_id")
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())


@dataclass
class AdaptiveCounselingResponse:
    """適応型カウンセリングレスポンス"""
    response: str
    session_id: str
    emotion_analysis: Dict[str, Any]
    follow_up_suggestions: List[str]

    # 関係性情報
    relationship_phase: str = "stranger"
    trust_score: float = 0.0
    adaptation_applied: bool = False

    @property
    def is_crisis(self) -> bool:
        return self.emotion_analysis.get("is_crisis", False)


class AdaptiveCounselingService:
    """
    適応型カウンセリングサービス

    特徴:
    - ゼロ設定で即座に利用開始可能
    - 関係性フェーズ（初対面→顔見知り→親しい→信頼）の管理
    - エピソード記憶による長期的な関係構築
    - 対話を通じてユーザーの好みを自動学習
    """

    # トピック検出キーワード
    TOPIC_KEYWORDS = {
        "仕事": ["仕事", "職場", "会社", "上司", "同僚", "転職", "キャリア"],
        "人間関係": ["友達", "友人", "人間関係", "付き合い"],
        "家族": ["家族", "親", "父", "母", "兄弟", "姉妹", "子供"],
        "恋愛": ["恋愛", "彼氏", "彼女", "恋人", "結婚", "離婚"],
        "健康": ["健康", "病気", "体調", "睡眠", "疲れ"],
        "お金": ["お金", "金銭", "借金", "貯金", "給料"],
        "将来": ["将来", "未来", "目標", "夢", "進路"],
        "ストレス": ["ストレス", "プレッシャー", "不安", "心配"],
        "自己肯定感": ["自信", "自己肯定", "価値", "存在意義"],
    }

    # 個人情報開示を示すパターン
    DISCLOSURE_PATTERNS = [
        r"私は(.+?)です",
        r"実は(.+)",
        r"(.+?)歳です",
        r"(.+?)に住んで",
        r"(.+?)で働いて",
        r"初めて話す",
        r"誰にも言ってない",
    ]

    def __init__(
        self,
        api_key: str,
        memory_system: Optional[MemorySystem] = None,
        data_dir: str = "data",
    ):
        self.api_key = api_key
        self.memory_system = memory_system or MemorySystem()
        self.relationship_memory = get_relationship_memory(data_dir)

        # 感情分析サービス
        self.emotion_service = EmotionAnalysisService()

        # API設定
        self.gemini_model = "gemini-2.0-flash-exp"
        self.gemini_api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent"
        )

        self.logger = get_logger("adaptive_counseling_service")

    async def counsel(
        self,
        request: AdaptiveCounselingRequest,
    ) -> AdaptiveCounselingResponse:
        """
        適応型カウンセリングを実行

        Args:
            request: カウンセリングリクエスト

        Returns:
            AdaptiveCounselingResponse
        """
        try:
            log_business_event(
                self.logger,
                "adaptive_counseling_request",
                user_id=request.user_id,
                session_id=request.session_id,
            )

            # 1. 感情分析
            emotion_analysis = self.emotion_service.analyze_emotion(request.message)

            # 2. トピック抽出
            topics = self._extract_topics(request.message)

            # 3. 個人情報の開示を検出
            user_shared_info = self._extract_shared_info(request.message)

            # 4. 関係性を更新（学習）
            user_data = self.relationship_memory.process_interaction(
                user_id=request.user_id,
                message=request.message,
                topics=topics,
                emotion=emotion_analysis.primary_emotion.value,
                emotion_intensity=emotion_analysis.intensity,
                is_crisis=emotion_analysis.is_crisis,
                user_shared_info=user_shared_info,
            )

            # 5. システムプロンプト生成（関係性考慮）
            system_prompt = self._build_adaptive_prompt(
                request=request,
                emotion_analysis=emotion_analysis,
                topics=topics,
            )

            # 6. AI応答生成
            ai_response = await self._generate_response(
                request.message, system_prompt
            )

            # 7. フォローアップ提案を生成
            follow_ups = self._generate_follow_up_suggestions(
                emotion=emotion_analysis.primary_emotion,
                topics=topics,
                phase=user_data.state.phase,
            )

            # 8. メモリに保存（セッション内一時記憶）
            self.memory_system.add_conversation(
                user_id=request.user_id,
                user_message=request.message,
                ai_response=ai_response,
                importance=emotion_analysis.intensity,
            )

            response = AdaptiveCounselingResponse(
                response=ai_response,
                session_id=request.session_id or str(uuid.uuid4()),
                emotion_analysis=emotion_analysis.to_dict(),
                follow_up_suggestions=follow_ups,
                relationship_phase=user_data.state.phase.value,
                trust_score=user_data.state.trust_score,
                adaptation_applied=user_data.profile.confidence_score > 0.2,
            )

            log_business_event(
                self.logger,
                "adaptive_counseling_response",
                user_id=request.user_id,
                relationship_phase=user_data.state.phase.value,
                trust_score=user_data.state.trust_score,
            )

            return response

        except Exception as e:
            log_error(self.logger, e, {"user_id": request.user_id})
            return self._create_fallback_response(request)

    def _build_adaptive_prompt(
        self,
        request: AdaptiveCounselingRequest,
        emotion_analysis: Any,
        topics: List[str],
    ) -> str:
        """適応型システムプロンプトを構築"""
        # カスタム指示がある場合は優先
        if request.custom_instructions:
            return request.custom_instructions

        # 関係性記憶システムからプロンプトを生成
        base_prompt = self.relationship_memory.generate_system_prompt(
            request.user_id
        )

        # 現在のコンテキストを追加
        context_info = self.relationship_memory.prompt_generator.generate_context_addendum(
            emotion=emotion_analysis.primary_emotion.value,
            emotion_intensity=emotion_analysis.intensity / 10.0,
            topics=topics,
            user_name=request.user_name or "",
        )

        # 危機対応
        if emotion_analysis.is_crisis:
            crisis_addendum = (
                self.relationship_memory.prompt_generator.generate_crisis_addendum()
            )
            return f"{base_prompt}\n{context_info}\n{crisis_addendum}"

        return f"{base_prompt}\n{context_info}"

    def _extract_topics(self, message: str) -> List[str]:
        """メッセージからトピックを抽出"""
        topics = []
        message_lower = message.lower()

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(kw in message_lower for kw in keywords):
                topics.append(topic)

        return topics[:3]  # 最大3つ

    def _extract_shared_info(self, message: str) -> List[str]:
        """メッセージから共有された個人情報を抽出"""
        shared_info = []

        for pattern in self.DISCLOSURE_PATTERNS:
            matches = re.findall(pattern, message)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match and len(match) < 50:  # 長すぎるものは除外
                    shared_info.append(match.strip())

        return shared_info[:5]  # 最大5つ

    def _generate_follow_up_suggestions(
        self,
        emotion: EmotionType,
        topics: List[str],
        phase: RelationshipPhase,
    ) -> List[str]:
        """フォローアップ提案を生成"""
        suggestions = []

        # 感情ベースの提案
        emotion_suggestions = {
            EmotionType.SADNESS: ["つらい気持ちをもう少し聞かせてください"],
            EmotionType.ANXIETY: ["何が一番心配ですか？"],
            EmotionType.ANGER: ["その怒りの裏にある本当の気持ちは何でしょう？"],
            EmotionType.LONELINESS: ["孤独を感じるのはどんな時ですか？"],
            EmotionType.STRESS: ["最も負担に感じていることは何ですか？"],
        }

        if emotion in emotion_suggestions:
            suggestions.extend(emotion_suggestions[emotion])

        # トピックベースの提案
        topic_suggestions = {
            "仕事": ["理想の働き方について考えたことはありますか？"],
            "人間関係": ["一番大切にしたい関係は何ですか？"],
            "将来": ["5年後、どんな自分でいたいですか？"],
        }

        for topic in topics:
            if topic in topic_suggestions:
                suggestions.extend(topic_suggestions[topic])
                break

        # 関係性フェーズに応じた提案
        if phase == RelationshipPhase.STRANGER:
            if not suggestions:
                suggestions = [
                    "他に話しておきたいことはありますか？",
                    "今の気持ちを一言で表すと？",
                ]
        elif phase == RelationshipPhase.TRUSTED:
            suggestions.append("長い目で見て、どうなりたいですか？")

        return suggestions[:2]

    async def _generate_response(
        self, message: str, system_prompt: str
    ) -> str:
        """AI応答を生成"""
        try:
            gemini_options = {
                "contents": [
                    {"role": "user", "parts": [{"text": message}]}
                ],
                "systemInstruction": {
                    "role": "system",
                    "parts": [{"text": system_prompt}],
                },
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.gemini_api_url,
                    params={"key": self.api_key},
                    json=gemini_options,
                ) as response:
                    if response.status != 200:
                        raise ExternalServiceError(
                            f"Gemini API error: HTTP {response.status}",
                            service_name="Gemini API",
                            status_code=response.status,
                        )

                    response_data = await response.json()

                    if (
                        "candidates" not in response_data
                        or not response_data["candidates"]
                    ):
                        raise ExternalServiceError(
                            "No candidates in Gemini response",
                            service_name="Gemini API",
                        )

                    candidate = response_data["candidates"][0]
                    response_text = candidate["content"]["parts"][0].get(
                        "text", ""
                    )

                    if not response_text.strip():
                        raise ExternalServiceError(
                            "Empty response from Gemini API",
                            service_name="Gemini API",
                        )

                    return response_text

        except aiohttp.ClientError as e:
            raise ExternalServiceError(
                f"Network error: {str(e)}",
                service_name="Gemini API",
            )

    def _create_fallback_response(
        self,
        request: AdaptiveCounselingRequest,
    ) -> AdaptiveCounselingResponse:
        """フォールバック応答"""
        return AdaptiveCounselingResponse(
            response=(
                "申し訳ありません。今少し調子が悪いようです。"
                "時間を置いてもう一度お試しいただくか、"
                "信頼できる方に直接相談することをお勧めします。"
                "あなたは一人ではありません。"
            ),
            session_id=request.session_id or str(uuid.uuid4()),
            emotion_analysis={
                "primary_emotion": "neutral",
                "intensity": 0,
                "is_crisis": False,
            },
            follow_up_suggestions=["他に何かお手伝いできることはありますか？"],
            relationship_phase="stranger",
            trust_score=0.0,
            adaptation_applied=False,
        )

    def get_relationship_summary(self, user_id: str) -> Dict[str, Any]:
        """ユーザーの関係性サマリーを取得"""
        return self.relationship_memory.get_relationship_summary(user_id)

    def reset_relationship(self, user_id: str) -> bool:
        """ユーザーの関係性をリセット"""
        return self.relationship_memory.reset_relationship(user_id)

    def export_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーデータをエクスポート（GDPR対応）"""
        return self.relationship_memory.export_user_data(user_id)

    def delete_user_data(self, user_id: str) -> bool:
        """ユーザーデータを削除（GDPR対応）"""
        return self.relationship_memory.delete_user_data(user_id)


def create_adaptive_counseling_service(
    api_key: str,
    data_dir: str = "data",
) -> AdaptiveCounselingService:
    """
    適応型カウンセリングサービスを作成

    Args:
        api_key: Gemini API キー
        data_dir: データディレクトリ

    Returns:
        AdaptiveCounselingService
    """
    return AdaptiveCounselingService(
        api_key=api_key,
        data_dir=data_dir,
    )
