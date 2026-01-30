"""
カウンセリングサービス
メンタルファースト: 寄り添いと安全を最優先
"""

import os
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models.emotion import EmotionAnalysis, EmotionType
from ..models.relationship import (
    DepthLevel,
    RelationshipPhase,
    ToneLevel,
)
from ..models.user import UserState
from ..ports.ai_port import ChatMessage, IAIProvider
from ..ports.storage_port import IStorage
from .emotion import EmotionService


# プロンプトファイルのパス
# 環境変数で設定可能、デフォルトは /app/config（Docker環境用）
# 開発環境では相対パスも自動で解決
_config_dir_str = os.environ.get("YAMII_CONFIG_DIR", "/app/config")
CONFIG_DIR = Path(_config_dir_str)
# 相対パスの場合は、プロジェクトルートからの相対として解決
if not CONFIG_DIR.is_absolute():
    CONFIG_DIR = Path(__file__).parent.parent.parent.parent / _config_dir_str
DEFAULT_PROMPT_FILE = CONFIG_DIR / "YAMII.md"


def _load_prompt_from_file() -> str:
    """
    YAMII.mdからデフォルトプロンプトを読み込む

    Raises:
        FileNotFoundError: YAMII.mdが存在しない場合
    """
    if not DEFAULT_PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"YAMII.md not found at {DEFAULT_PROMPT_FILE}. "
            "Please create config/YAMII.md with the system prompt."
        )

    content = DEFAULT_PROMPT_FILE.read_text(encoding="utf-8")
    return content.strip()


@dataclass
class ConversationMessage:
    """会話履歴の1メッセージ"""

    role: str  # "user" or "assistant"
    content: str


@dataclass
class CounselingRequest:
    """カウンセリングリクエスト"""

    message: str
    user_id: str
    session_id: str | None = None
    user_name: str | None = None
    # セッション内文脈保持: クライアントが管理する会話履歴
    conversation_history: list[ConversationMessage] | None = None

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
    follow_up_questions: list[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def is_crisis(self) -> bool:
        return self.emotion_analysis.is_crisis

    def to_dict(self) -> dict[str, Any]:
        return {
            "response": self.response,
            "session_id": self.session_id,
            "emotion_analysis": self.emotion_analysis.to_dict(),
            "advice_type": self.advice_type,
            "follow_up_questions": self.follow_up_questions,
            "is_crisis": self.is_crisis,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CounselingStreamContext:
    """ストリーミング応答のメタデータコンテキスト"""

    session_id: str
    emotion_analysis: EmotionAnalysis
    advice_type: str
    follow_up_questions: list[str]
    user: UserState
    request: CounselingRequest

    @property
    def is_crisis(self) -> bool:
        return self.emotion_analysis.is_crisis


class AdviceTypeClassifier:
    """アドバイスタイプ分類器"""

    def __init__(self):
        self._category_keywords = {
            "crisis_support": [
                "死にたい",
                "消えたい",
                "自殺",
                "生きる意味",
                "限界",
                "自分を傷つけ",
                "終わりにしたい",
            ],
            "mental_health": [
                "うつ",
                "うつ病",
                "精神的",
                "メンタル",
                "心療内科",
                "精神科",
                "カウンセラー",
                "薬",
                "治療",
            ],
            "relationship": [
                "恋愛",
                "恋人",
                "彼氏",
                "彼女",
                "片思い",
                "失恋",
                "デート",
                "結婚",
                "離婚",
                "パートナー",
            ],
            "career": [
                "仕事",
                "職場",
                "転職",
                "就職",
                "会社",
                "上司",
                "同僚",
                "残業",
                "給料",
                "キャリア",
                "昇進",
            ],
            "family": [
                "家族",
                "親",
                "父",
                "母",
                "兄弟",
                "姉妹",
                "子供",
                "育児",
                "介護",
                "実家",
            ],
            "friendship": ["友達", "友人", "仲間", "人間関係", "サークル"],
            "education": [
                "勉強",
                "学校",
                "大学",
                "受験",
                "テスト",
                "試験",
                "宿題",
                "成績",
                "進路",
            ],
            "health": ["健康", "病気", "体調", "病院", "医者", "症状"],
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
                "もう少し聴かせてもらえますか？",
                "今の気持ちを言葉にするとしたら、どんな感じですか？",
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
            ],
        }

    def generate(self, advice_type: str) -> list[str]:
        """フォローアップ質問を生成"""
        templates = self._templates.get(advice_type, self._templates["general_support"])
        return templates[:2]


class CounselingService:
    """
    カウンセリングサービス

    メンタルファースト原則:
    - 寄り添いを最優先
    - 危機的状況への迅速な対応
    - ユーザーの好みに合わせたパーソナライゼーション
    - 継続的な関係性構築
    """

    def __init__(
        self,
        ai_provider: IAIProvider,
        storage: IStorage,
        emotion_service: EmotionService | None = None,
    ):
        self.ai_provider = ai_provider
        self.storage = storage
        # EmotionServiceにもAIプロバイダーを渡して婉曲表現検出を有効化
        self.emotion_service = emotion_service or EmotionService(ai_provider=ai_provider)
        self.advice_classifier = AdviceTypeClassifier()
        self.follow_up_generator = FollowUpGenerator()

    async def generate_response(self, request: CounselingRequest) -> CounselingResponse:
        """
        カウンセリングレスポンスを生成

        メンタルファースト: 感情に寄り添い、安全を確保
        """
        # 1. ユーザー状態を取得または作成
        user = await self.storage.load_user(request.user_id)
        if user is None:
            user = UserState(user_id=request.user_id)

        # 2. 感情分析（LLM併用で婉曲表現も検出）
        emotion_analysis = await self.emotion_service.analyze_with_llm(request.message)

        # 3. アドバイスタイプ分類
        advice_type = self.advice_classifier.classify(
            request.message, emotion_analysis.primary_emotion
        )

        # 4. パーソナライズされたシステムプロンプト構築
        system_prompt = self._build_personalized_prompt(
            user, emotion_analysis, advice_type
        )

        # 5. AI応答生成（セッション内文脈保持）
        # 会話履歴をChatMessage形式に変換
        chat_history: list[ChatMessage] | None = None
        if request.conversation_history:
            chat_history = [
                ChatMessage(role=msg.role, content=msg.content)
                for msg in request.conversation_history
            ]

        ai_response = await self.ai_provider.generate(
            message=request.message,
            system_prompt=system_prompt,
            conversation_history=chat_history,
        )

        # 6. フォローアップ質問生成
        follow_up_questions = self.follow_up_generator.generate(advice_type)

        # 7. ユーザー状態更新（パーソナライゼーション含む）
        await self._update_user_state(user, request, emotion_analysis, advice_type)

        return CounselingResponse(
            response=ai_response,
            session_id=request.session_id,
            emotion_analysis=emotion_analysis,
            advice_type=advice_type,
            follow_up_questions=follow_up_questions,
        )

    async def generate_response_stream(
        self, request: CounselingRequest
    ) -> tuple[AsyncGenerator[str, None], "CounselingStreamContext"]:
        """
        カウンセリングレスポンスをストリーミング生成

        Returns:
            tuple: (AI応答チャンクのAsyncGenerator, メタデータコンテキスト)
        """
        # 1. ユーザー状態を取得または作成
        user = await self.storage.load_user(request.user_id)
        if user is None:
            user = UserState(user_id=request.user_id)

        # 2. 感情分析（LLM併用で婉曲表現も検出）
        emotion_analysis = await self.emotion_service.analyze_with_llm(request.message)

        # 3. アドバイスタイプ分類
        advice_type = self.advice_classifier.classify(
            request.message, emotion_analysis.primary_emotion
        )

        # 4. パーソナライズされたシステムプロンプト構築
        system_prompt = self._build_personalized_prompt(
            user, emotion_analysis, advice_type
        )

        # 5. フォローアップ質問生成
        follow_up_questions = self.follow_up_generator.generate(advice_type)

        # コンテキストオブジェクトを構築
        context = CounselingStreamContext(
            session_id=request.session_id or str(uuid.uuid4()),
            emotion_analysis=emotion_analysis,
            advice_type=advice_type,
            follow_up_questions=follow_up_questions,
            user=user,
            request=request,
        )

        # 6. AI応答をストリーミング生成
        chat_history: list[ChatMessage] | None = None
        if request.conversation_history:
            chat_history = [
                ChatMessage(role=msg.role, content=msg.content)
                for msg in request.conversation_history
            ]

        stream = self.ai_provider.generate_stream(
            message=request.message,
            system_prompt=system_prompt,
            conversation_history=chat_history,
        )

        return stream, context

    async def finalize_stream(
        self, context: "CounselingStreamContext"
    ) -> None:
        """ストリーム完了後にユーザー状態を更新"""
        await self._update_user_state(
            context.user, context.request, context.emotion_analysis, context.advice_type
        )

    def _build_personalized_prompt(
        self,
        user: UserState,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> str:
        """
        パーソナライズされたシステムプロンプトを構築

        メンタルファースト: ユーザーの好みと状態に合わせる
        最適化: リスト結合で空セクションを除外
        """
        # ベースプロンプトを取得（ファイル優先、フォールバック）
        base_prompt = self._get_base_prompt(user)

        # 各セクションを収集（空文字列は除外）
        # Note: エピソードコンテキストはZero-Knowledge設計のため削除（ノーログ）
        # Note: 危機対応はYAMII.mdに統合されているため、別途追加しない
        sections = [
            base_prompt,
            self._get_explicit_profile(user),
            self._get_phase_specific_instruction(user),
            self._get_personalization_instruction(user),
            self._get_context_info(user, emotion_analysis, advice_type),
        ]

        # 空文字列を除外して結合
        return "\n\n".join(s for s in sections if s)

    def _get_base_prompt(self, user: UserState) -> str:
        """
        デフォルトプロンプトを取得

        YAMII.mdファイルから読み込む。
        ファイルがない場合はFileNotFoundErrorが発生する。
        """
        return _load_prompt_from_file()

    def _get_explicit_profile(self, user: UserState) -> str:
        """ユーザーが設定したカスタム指示"""
        if user.explicit_profile:
            return f"【ユーザーからの指示】\n{user.explicit_profile}"
        return ""

    def _get_phase_specific_instruction(self, user: UserState) -> str:
        """フェーズに応じた指示（未使用 - カスタムプロンプトで対応）"""
        return ""

    def _get_personalization_instruction(self, user: UserState) -> str:
        """パーソナライゼーション指示（未使用 - カスタムプロンプトで対応）"""
        return ""

    def _get_context_info(
        self,
        user: UserState,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> str:
        """コンテキスト情報（シンプル版）"""
        # 名前があれば使う
        name_part = f"（{user.display_name}さん）" if user.display_name else ""

        # 感情が強い場合のみ言及
        emotion_part = ""
        if emotion_analysis.intensity > 0.5:
            emotion_part = f"今{emotion_analysis.primary_emotion.value}な様子。"

        if name_part or emotion_part:
            return f"{name_part}{emotion_part}"
        return ""

    async def _update_user_state(
        self,
        user: UserState,
        request: CounselingRequest,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> None:
        """ユーザー状態を更新（パーソナライゼーション学習含む）"""
        # インタラクション記録
        user.update_interaction()

        # 感情パターン更新
        self.emotion_service.update_user_patterns(user, emotion_analysis)

        # トピック更新
        user.add_known_topic(advice_type)
        user.update_topic_affinity(advice_type)

        # 表示名更新
        if request.user_name:
            user.display_name = request.user_name

        # パーソナライゼーションスコア更新
        self._update_personalization_scores(user, emotion_analysis, advice_type)

        # 信頼スコア更新
        self._update_trust_scores(user, emotion_analysis)

        # フェーズ更新チェック
        self._update_phase_if_needed(user)

        # Note: エピソード生成は Zero-Knowledge 設計のため削除（ノーログ）
        # Note: 危機時のフォローアップスケジュールは Proactive 機能削除のため削除

        # 保存
        await self.storage.save_user(user)

    def _update_personalization_scores(
        self,
        user: UserState,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> None:
        """パーソナライゼーションスコアを学習"""
        # 学習率（徐々に学習）
        learning_rate = 0.05

        # 感情強度が高い場合、共感を好む傾向として学習
        if emotion_analysis.intensity > 0.6:
            user.likes_empathy = min(1.0, user.likes_empathy + learning_rate)

        # 特定のカテゴリはアドバイス志向として学習
        if advice_type in ["career", "education", "health"]:
            user.likes_advice = min(1.0, user.likes_advice + learning_rate)

        # 学習の確信度を上げる
        user.confidence_score = min(1.0, user.confidence_score + learning_rate / 2)

    def _update_trust_scores(
        self,
        user: UserState,
        emotion_analysis: EmotionAnalysis,
    ) -> None:
        """信頼スコアを更新"""
        # 継続的な対話は信頼度を上げる
        base_increase = 0.01

        # 感情開示がある場合は開示度を上げる
        if emotion_analysis.intensity > 0.5:
            user.openness_score = min(1.0, user.openness_score + base_increase * 2)

        # 継続的な対話は親密度を上げる
        user.rapport_score = min(1.0, user.rapport_score + base_increase)

        # 信頼度は時間と開示度に基づいて上昇
        trust_increase = base_increase * (1 + user.openness_score)
        user.trust_score = min(1.0, user.trust_score + trust_increase)

    def _update_phase_if_needed(self, user: UserState) -> None:
        """フェーズ更新が必要かチェック（信頼スコアも考慮）"""
        from ..models.relationship import PhaseTransition

        current_phase = user.phase
        new_phase = current_phase

        # インタラクション数と信頼スコアに基づくフェーズ判定
        interactions = user.total_interactions
        trust = user.trust_score

        # フェーズ判定（インタラクション数 + 信頼スコアのハイブリッド）
        if interactions <= 5 and trust < 0.2:
            new_phase = RelationshipPhase.STRANGER
        elif (interactions <= 20 or trust < 0.4) and interactions > 5:
            new_phase = RelationshipPhase.ACQUAINTANCE
        elif (interactions <= 50 or trust < 0.7) and interactions > 20:
            new_phase = RelationshipPhase.FAMILIAR
        elif interactions > 50 or trust >= 0.7:
            new_phase = RelationshipPhase.TRUSTED

        if new_phase != current_phase:
            # フェーズ遷移を記録
            transition = PhaseTransition(
                from_phase=current_phase,
                to_phase=new_phase,
                transitioned_at=datetime.now(),
                interaction_count=interactions,
                trigger=f"trust:{trust:.2f}",
            )
            user.phase_history.append(transition)
            user.phase = new_phase
