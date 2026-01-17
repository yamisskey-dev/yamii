"""
カウンセリングサービス
メンタルファースト: 寄り添いと安全を最優先
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
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
        # 各セクションを収集（空文字列は除外）
        # Note: エピソードコンテキストはZero-Knowledge設計のため削除（ノーログ）
        sections = [
            self._get_base_prompt(user),
            self._get_phase_specific_instruction(user),
            self._get_personalization_instruction(user),
            self._get_context_info(user, emotion_analysis, advice_type),
        ]

        # 危機対応（最優先で末尾に追加）
        if emotion_analysis.is_crisis:
            sections.append(self._get_crisis_instruction())

        # 空文字列を除外して結合
        return "\n\n".join(s for s in sections if s)

    def _get_base_prompt(self, user: UserState) -> str:
        """ユーザーの好みに合わせた基本プロンプト"""
        # トーン設定
        tone_instructions = {
            ToneLevel.WARM: "温かみのある言葉で、相手を包み込むように話してください。",
            ToneLevel.PROFESSIONAL: "専門的かつ信頼感のある言葉遣いで対応してください。",
            ToneLevel.CASUAL: "友達のように気軽で親しみやすい話し方をしてください。",
            ToneLevel.BALANCED: "温かみがありつつも適度な距離感を保ってください。",
        }

        # 深さ設定
        depth_instructions = {
            DepthLevel.SHALLOW: "短く簡潔に、1-2文程度で応答してください。",
            DepthLevel.MEDIUM: "適度な長さで、2-3文（100-150文字）で応答してください。",
            DepthLevel.DEEP: "丁寧に掘り下げて、3-4文（150-200文字）で応答してください。",
        }

        tone = tone_instructions.get(
            user.preferred_tone, tone_instructions[ToneLevel.BALANCED]
        )
        depth = depth_instructions.get(
            user.preferred_depth, depth_instructions[DepthLevel.MEDIUM]
        )

        return f"""あなたは相談者の話に寄り添う相談相手です。
まず気持ちを受け止め、必要に応じて一緒に考えます。

【トーン】{tone}
【長さ】{depth}
【重要】SNSでの会話なので自然で読みやすく。"""

    def _get_phase_specific_instruction(self, user: UserState) -> str:
        """フェーズに応じた詳細な指示"""
        match user.phase:
            case RelationshipPhase.STRANGER:
                return """【初対面の対応】
- 丁寧な言葉遣いを心がける
- まずは安心感を与える
- 押しつけがましいアドバイスは避ける
- 「よかったら教えてください」など配慮のある言い回しを使う"""

            case RelationshipPhase.ACQUAINTANCE:
                return """【顔見知りとしての対応】
- 前回の会話を軽く参照してよい
- 少し親しみを込めた言葉遣いが可能
- 「以前〇〇とおっしゃっていましたね」など過去の文脈を活かす
- ただし踏み込みすぎない"""

            case RelationshipPhase.FAMILIAR:
                return """【親しい関係としての対応】
- 自然体で会話できる
- 過去の会話を積極的に参照
- 「〇〇さんらしいですね」など相手をよく知っている前提で話す
- 具体的なアドバイスも可能"""

            case RelationshipPhase.TRUSTED:
                return """【信頼関係に基づく対応】
- 率直で正直なやり取りが可能
- 必要であれば厳しいことも伝えられる
- 長期的な視点でのアドバイスが可能
- 相手の成長を見守る姿勢で"""

    def _get_personalization_instruction(self, user: UserState) -> str:
        """ユーザーの好みに基づくパーソナライゼーション"""
        instructions = []

        # 共感重視度
        if user.likes_empathy > 0.7:
            instructions.append("- 感情に深く寄り添い、共感を丁寧に示す")
        elif user.likes_empathy < 0.4:
            instructions.append("- 感情面は軽めに触れ、実用的な対話を心がける")

        # アドバイス志向
        if user.likes_advice > 0.6:
            instructions.append("- 具体的なアドバイスや提案を積極的に行う")
        elif user.likes_advice < 0.4:
            instructions.append("- アドバイスは控えめに、傾聴を重視する")

        # 質問志向
        if user.likes_questions > 0.6:
            instructions.append("- 掘り下げる質問を積極的に投げかける")
        elif user.likes_questions < 0.4:
            instructions.append("- 質問は最小限に、相手のペースを尊重する")

        # 詳細志向
        if user.likes_detail > 0.6:
            instructions.append("- 詳細な説明や背景情報を含める")
        elif user.likes_detail < 0.4:
            instructions.append("- シンプルで簡潔な表現を心がける")

        if instructions:
            return "【この方の好み】\n" + "\n".join(instructions)
        return ""

    def _get_context_info(
        self,
        user: UserState,
        emotion_analysis: EmotionAnalysis,
        advice_type: str,
    ) -> str:
        """コンテキスト情報"""
        now = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        info = f"""【現在の状況】
現在日時: {now}
相談者: {user.display_name or "（名前未設定）"}
関係性: {user.phase.value}（{user.total_interactions}回目の対話）
検出された感情: {emotion_analysis.primary_emotion.value}（強度: {emotion_analysis.intensity:.1f}）
相談カテゴリ: {advice_type}"""

        # 既知の情報
        if user.known_facts:
            facts_text = "\n".join(f"  - {fact}" for fact in user.known_facts[:5])
            info += f"\n\n【この方について知っていること】\n{facts_text}"

        # 関心のあるトピック
        top_topics = user.get_top_topics(3)
        if top_topics:
            topics_text = ", ".join(t.topic for t in top_topics)
            info += f"\n\n【よく話題にすること】{topics_text}"

        return info

    def _get_crisis_instruction(self) -> str:
        """危機対応の特別指示 - 傾聴重視アプローチ"""
        # Note: 過去の危機履歴はZero-Knowledge設計のため参照不可（ノーログ）
        return """
【重要: この方は辛い状況にいる可能性があります】

あなたの最も大切な役割は「聴くこと」です。

■ やるべきこと
- 話を最後まで聴いてください
- 相手の気持ちを自分の言葉で言い換えて確認してください
- 「辛いですね」「それは苦しかったですね」など共感を示してください
- 話してくれたことへの感謝を伝えてください
- 沈黙も受け入れてください

■ やってはいけないこと
- 解決策やアドバイスを急いで提示しない
- 「頑張って」「前向きに」など励ましの言葉を使わない
- 相談窓口や電話番号をいきなり案内しない
- 話を遮ったり、話題を変えたりしない
- 「気持ちはわかります」と安易に言わない（本当にはわからないから）

■ 専門機関の案内について
相手から「どこに相談すればいい？」「誰かに話したい」と
明確に聞かれた場合にのみ、自然な流れで案内してください。
こちらから押し付けることは絶対にしないでください。
"""

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
