"""
カウンセリングサービス
簡素化されたコアカウンセリングロジック
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..models.user import UserState
from ..models.conversation import (
    Episode,
    EpisodeType,
    Message,
    ConversationContext,
    ConversationPhase,
)
from ..models.emotion import EmotionType, EmotionAnalysis
from ..models.relationship import (
    RelationshipPhase,
    get_phase_instruction,
)
from .emotion import EmotionService
from ..ports.ai_port import IAIProvider
from ..ports.storage_port import IStorage


@dataclass
class CounselingRequest:
    """カウンセリングリクエスト"""
    message: str
    user_id: str
    session_id: Optional[str] = None
    user_name: Optional[str] = None

    def __post_init__(self):
        if not self.message or not self.message.strip():
            raise ValueError("メッセージは必須です")
        if not self.user_id or not self.user_id.strip():
            raise ValueError("ユーザーIDは必須です")
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())


@dataclass
class CounselingResponse:
    """カウンセリングレスポンス"""
    response: str
    session_id: str
    emotion_analysis: EmotionAnalysis
    advice_type: str
    follow_up_questions: List[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def is_crisis(self) -> bool:
        return self.emotion_analysis.is_crisis

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "session_id": self.session_id,
            "emotion_analysis": self.emotion_analysis.to_dict(),
            "advice_type": self.advice_type,
            "follow_up_questions": self.follow_up_questions,
            "is_crisis": self.is_crisis,
            "timestamp": self.timestamp.isoformat(),
        }


class AdviceTypeClassifier:
    """アドバイスタイプ分類器"""

    def __init__(self):
        self._category_keywords = {
            "crisis_support": [
                "死にたい", "消えたい", "自殺", "生きる意味", "限界",
                "自分を傷つけ", "終わりにしたい"
            ],
            "mental_health": [
                "うつ", "うつ病", "精神的", "メンタル", "心療内科",
                "精神科", "カウンセラー", "薬", "治療"
            ],
            "relationship": [
                "恋愛", "恋人", "彼氏", "彼女", "片思い", "失恋",
                "デート", "結婚", "離婚", "パートナー"
            ],
            "career": [
                "仕事", "職場", "転職", "就職", "会社", "上司",
                "同僚", "残業", "給料", "キャリア", "昇進"
            ],
            "family": [
                "家族", "親", "父", "母", "兄弟", "姉妹",
                "子供", "育児", "介護", "実家"
            ],
            "friendship": [
                "友達", "友人", "仲間", "人間関係", "サークル"
            ],
            "education": [
                "勉強", "学校", "大学", "受験", "テスト",
                "試験", "宿題", "成績", "進路"
            ],
            "health": [
                "健康", "病気", "体調", "病院", "医者", "症状"
            ]
        }

    def classify(self, message: str, emotion: EmotionType) -> str:
        """メッセージと感情からアドバイスタイプを分類"""
        message_lower = message.lower()

        # 危機的状況の優先判定
        if emotion == EmotionType.DEPRESSION:
            return "crisis_support"

        for crisis_keyword in self._category_keywords["crisis_support"]:
            if crisis_keyword in message_lower:
                return "crisis_support"

        # その他のカテゴリ判定
        for category, keywords in self._category_keywords.items():
            if category == "crisis_support":
                continue

            if any(keyword in message_lower for keyword in keywords):
                return category

        return "general_support"


class FollowUpGenerator:
    """フォローアップ質問生成器"""

    def __init__(self):
        self._templates = {
            "crisis_support": [
                "今、誰か信頼できる人はそばにいますか？",
                "専門のカウンセラーや医師に相談することを考えてみませんか？",
            ],
            "mental_health": [
                "この状況はいつ頃から続いていますか？",
                "今まで試してみた対処法はありますか？",
            ],
            "relationship": [
                "お相手とはどのくらいお付き合いされているのですか？",
                "あなた自身はどのような関係を望んでいますか？",
            ],
            "career": [
                "現在の職場環境についてもう少し教えてください",
                "理想的な働き方はどのようなものですか？",
            ],
            "family": [
                "ご家族との関係について詳しく教えてください",
                "この状況がどのくらい続いていますか？",
            ],
            "general_support": [
                "このことで一番困っていることは何ですか？",
                "理想的な状況はどのようなものでしょうか？",
            ]
        }

    def generate(self, advice_type: str) -> List[str]:
        """フォローアップ質問を生成"""
        templates = self._templates.get(advice_type, self._templates["general_support"])
        return templates[:2]


class CounselingService:
    """
    カウンセリングサービス

    簡素化されたコアサービス。AIプロバイダーとストレージは
    ポートインターフェースを通じて注入される。
    """

    def __init__(
        self,
        ai_provider: IAIProvider,
        storage: IStorage,
        emotion_service: Optional[EmotionService] = None,
    ):
        self.ai_provider = ai_provider
        self.storage = storage
        self.emotion_service = emotion_service or EmotionService()
        self.advice_classifier = AdviceTypeClassifier()
        self.follow_up_generator = FollowUpGenerator()

    async def generate_response(self, request: CounselingRequest) -> CounselingResponse:
        """
        カウンセリングレスポンスを生成

        Args:
            request: カウンセリングリクエスト

        Returns:
            CounselingResponse: レスポンス
        """
        # 1. ユーザー状態を取得または作成
        user = await self.storage.load_user(request.user_id)
        if user is None:
            user = UserState(user_id=request.user_id)

        # 2. 感情分析
        emotion_analysis = self.emotion_service.analyze(request.message)

        # 3. アドバイスタイプ分類
        advice_type = self.advice_classifier.classify(
            request.message, emotion_analysis.primary_emotion
        )

        # 4. システムプロンプト構築
        system_prompt = self._build_system_prompt(user, emotion_analysis, advice_type)

        # 5. AI応答生成
        ai_response = await self.ai_provider.generate(
            message=request.message,
            system_prompt=system_prompt,
        )

        # 6. フォローアップ質問生成
        follow_up_questions = self.follow_up_generator.generate(advice_type)

        # 7. ユーザー状態更新
        await self._update_user_state(user, request, emotion_analysis, advice_type)

        return CounselingResponse(
            response=ai_response,
            session_id=request.session_id,
            emotion_analysis=emotion_analysis,
            advice_type=advice_type,
            follow_up_questions=follow_up_questions,
        )

    def _build_system_prompt(
        self,
        user: UserState,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> str:
        """システムプロンプトを構築"""
        # 基本プロンプト（シンプル・中性的）
        base_prompt = """あなたは相談者の話に寄り添う相談相手です。
まず気持ちを受け止め、必要に応じて一緒に考えます。"""

        # フェーズ固有の指示
        phase_instruction = get_phase_instruction(user.phase)

        # 現在時刻と文脈情報
        now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        context_info = f"""
現在日時: {now}
相談者: {user.display_name or user.user_id}
関係性フェーズ: {user.phase.value}
対話回数: {user.total_interactions}回目
感情分析結果: {emotion_analysis.primary_emotion.value}（強度: {emotion_analysis.intensity:.1f}）
相談タイプ: {advice_type}
"""

        # 既知の情報があれば追加
        if user.known_facts:
            facts_text = "\n".join(f"- {fact}" for fact in user.known_facts[:5])
            context_info += f"\n相談者について知っていること:\n{facts_text}\n"

        # 危機的状況の特別指示
        if emotion_analysis.is_crisis:
            context_info += """
⚠️ 重要: これは危機的状況の可能性があります。
- 専門的な支援機関への相談を強く推奨する
- いのちの電話（0570-783-556）などの情報を提供する
- 「あなたは一人じゃない」というメッセージを伝える
- 安全の確保を最優先とする
"""

        return f"{base_prompt}\n\n{phase_instruction}\n\n{context_info}"

    async def _update_user_state(
        self,
        user: UserState,
        request: CounselingRequest,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> None:
        """ユーザー状態を更新"""
        # インタラクション記録
        user.update_interaction()

        # 感情パターン更新
        self.emotion_service.update_user_patterns(user, emotion_analysis)

        # トピック更新
        user.add_known_topic(advice_type)

        # 表示名更新
        if request.user_name:
            user.display_name = request.user_name

        # フェーズ更新チェック
        self._update_phase_if_needed(user)

        # エピソード生成（重要な会話の場合）
        if self._should_create_episode(emotion_analysis, advice_type):
            episode = self._create_episode(user, request, emotion_analysis, advice_type)
            user.add_episode(episode)

        # 保存
        await self.storage.save_user(user)

    def _update_phase_if_needed(self, user: UserState) -> None:
        """フェーズ更新が必要かチェック"""
        from ..models.relationship import PhaseTransition

        current_phase = user.phase
        new_phase = current_phase

        # インタラクション数に基づくフェーズ判定
        interactions = user.total_interactions
        if interactions <= 5:
            new_phase = RelationshipPhase.STRANGER
        elif interactions <= 20:
            new_phase = RelationshipPhase.ACQUAINTANCE
        elif interactions <= 50:
            new_phase = RelationshipPhase.FAMILIAR
        else:
            new_phase = RelationshipPhase.TRUSTED

        if new_phase != current_phase:
            # フェーズ遷移を記録
            transition = PhaseTransition(
                from_phase=current_phase,
                to_phase=new_phase,
                transitioned_at=datetime.now(),
                interaction_count=interactions,
                trigger="interaction_milestone",
            )
            user.phase_history.append(transition)
            user.phase = new_phase

    def _should_create_episode(
        self,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> bool:
        """エピソードを作成すべきか判定"""
        # 危機的状況
        if emotion_analysis.is_crisis:
            return True
        # 高い感情強度
        if emotion_analysis.intensity > 0.7:
            return True
        # 重要なトピック
        important_types = {"crisis_support", "mental_health", "relationship", "family"}
        if advice_type in important_types:
            return True
        return False

    def _create_episode(
        self,
        user: UserState,
        request: CounselingRequest,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> Episode:
        """エピソードを作成"""
        # エピソードタイプ判定
        if emotion_analysis.is_crisis:
            episode_type = EpisodeType.CRISIS
        elif emotion_analysis.intensity > 0.8:
            episode_type = EpisodeType.INSIGHT
        else:
            episode_type = EpisodeType.GENERAL

        return Episode(
            id=str(uuid.uuid4()),
            user_id=user.user_id,
            created_at=datetime.now(),
            summary=request.message[:200],  # 最初の200文字
            topics=[advice_type],
            emotional_context=emotion_analysis.primary_emotion.value,
            importance_score=emotion_analysis.intensity,
            emotional_intensity=emotion_analysis.intensity,
            episode_type=episode_type,
            emotion=emotion_analysis.primary_emotion,
            keywords=[advice_type],
        )
