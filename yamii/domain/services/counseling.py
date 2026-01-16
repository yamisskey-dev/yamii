"""
カウンセリングサービス
メンタルファースト: 寄り添いと安全を最優先
"""

import uuid
from datetime import datetime, timedelta
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
    ToneLevel,
    DepthLevel,
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

        メンタルファースト: 感情に寄り添い、安全を確保
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

        # 4. パーソナライズされたシステムプロンプト構築
        system_prompt = self._build_personalized_prompt(
            user, emotion_analysis, advice_type
        )

        # 5. AI応答生成
        ai_response = await self.ai_provider.generate(
            message=request.message,
            system_prompt=system_prompt,
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
        """
        # 基本プロンプト
        base_prompt = self._get_base_prompt(user)

        # フェーズ固有の指示
        phase_instruction = self._get_phase_specific_instruction(user)

        # パーソナライゼーション指示
        personalization = self._get_personalization_instruction(user)

        # コンテキスト情報
        context_info = self._get_context_info(user, emotion_analysis, advice_type)

        # 危機対応（最優先）
        crisis_instruction = ""
        if emotion_analysis.is_crisis:
            crisis_instruction = self._get_crisis_instruction(user)

        # 最近のエピソードコンテキスト
        episode_context = self._get_episode_context(user)

        return f"""{base_prompt}

{phase_instruction}

{personalization}

{context_info}

{episode_context}

{crisis_instruction}"""

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

        tone = tone_instructions.get(user.preferred_tone, tone_instructions[ToneLevel.BALANCED])
        depth = depth_instructions.get(user.preferred_depth, depth_instructions[DepthLevel.MEDIUM])

        return f"""あなたは相談者の話に寄り添う相談相手です。
まず気持ちを受け止め、必要に応じて一緒に考えます。

【トーン】{tone}
【長さ】{depth}
【重要】SNSでの会話なので自然で読みやすく。"""

    def _get_phase_specific_instruction(self, user: UserState) -> str:
        """フェーズに応じた詳細な指示"""
        phase = user.phase

        if phase == RelationshipPhase.STRANGER:
            return """【初対面の対応】
- 丁寧な言葉遣いを心がける
- まずは安心感を与える
- 押しつけがましいアドバイスは避ける
- 「よかったら教えてください」など配慮のある言い回しを使う"""

        elif phase == RelationshipPhase.ACQUAINTANCE:
            return """【顔見知りとしての対応】
- 前回の会話を軽く参照してよい
- 少し親しみを込めた言葉遣いが可能
- 「以前〇〇とおっしゃっていましたね」など過去の文脈を活かす
- ただし踏み込みすぎない"""

        elif phase == RelationshipPhase.FAMILIAR:
            return """【親しい関係としての対応】
- 自然体で会話できる
- 過去の会話を積極的に参照
- 「〇〇さんらしいですね」など相手をよく知っている前提で話す
- 具体的なアドバイスも可能"""

        else:  # TRUSTED
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

    def _get_episode_context(self, user: UserState) -> str:
        """最近のエピソードからのコンテキスト"""
        recent = user.get_recent_episodes(3)
        if not recent:
            return ""

        episode_texts = []
        for ep in recent:
            days_ago = (datetime.now() - ep.created_at).days
            if days_ago == 0:
                time_desc = "今日"
            elif days_ago == 1:
                time_desc = "昨日"
            else:
                time_desc = f"{days_ago}日前"

            episode_texts.append(
                f"  - {time_desc}: {ep.summary[:50]}...（{ep.emotional_context}）"
            )

        return f"""【最近の会話】
{chr(10).join(episode_texts)}

※ 同じアドバイスの繰り返しは避け、前回の続きとして話す"""

    def _get_crisis_instruction(self, user: UserState) -> str:
        """危機対応の特別指示"""
        # 過去の危機エピソードを確認
        crisis_history = [
            ep for ep in user.episodes
            if ep.episode_type == EpisodeType.CRISIS
        ]

        instruction = """
⚠️ 【最優先: 危機対応】
この方は今、とても辛い状況にいる可能性があります。

1. まず安全の確認
   - 「今、安全な場所にいますか？」
   - 「誰か一緒にいる人はいますか？」

2. 寄り添いのメッセージ
   - 「話してくれてありがとうございます」
   - 「あなたは一人じゃありません」
   - 「今の気持ちを聴かせてください」

3. 必ず専門機関の情報を提供
   - いのちの電話: 0570-783-556
   - よりそいホットライン: 0120-279-338
   - こころの健康相談統一ダイヤル: 0570-064-556

4. フォローアップの約束
   - 「また話しかけてください」
   - 「あなたのことを心配しています」
"""

        if crisis_history:
            instruction += f"""
【重要】この方は過去にも辛い時期がありました（{len(crisis_history)}回）
より丁寧に、継続的なサポートを意識してください。
"""

        return instruction

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

        # エピソード生成（重要な会話の場合）
        if self._should_create_episode(emotion_analysis, advice_type):
            episode = self._create_episode(user, request, emotion_analysis, advice_type)
            user.add_episode(episode)

        # 危機時のフォローアップをスケジュール
        if emotion_analysis.is_crisis:
            self._schedule_crisis_follow_up(user)

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
        user.confidence_score = min(
            1.0,
            user.confidence_score + learning_rate / 2
        )

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
        if emotion_analysis.intensity > 0.6:  # 閾値を下げて記録を増やす
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

    def _schedule_crisis_follow_up(self, user: UserState) -> None:
        """危機時のフォローアップをスケジュール"""
        # プロアクティブ設定を強制有効化（危機対応）
        user.proactive.enabled = True
        user.proactive.follow_up_enabled = True

        # 24時間以内のフォローアップをスケジュール
        user.proactive.next_scheduled = datetime.now() + timedelta(hours=24)
