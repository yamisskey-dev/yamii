"""
プロアクティブアウトリーチサービス
Bot APIならではの機能 - ユーザーに先にチェックインする

ChatGPT/Claude/Gemini WebUIやAwarefy/Ubieが提供できない
独自の価値を提供する核心機能

メンタルファースト強化:
- ユーザーのフェーズに応じたトーン調整
- パーソナライズされたメッセージ
- 危機予防のための早期介入
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import random

from ..models.user import UserState
from ..models.relationship import RelationshipPhase
from ..models.emotion import EmotionType, NEGATIVE_EMOTIONS
from ..ports.storage_port import IStorage
from .emotion import EmotionService


class OutreachReason(Enum):
    """アウトリーチの理由"""
    ABSENCE = "absence"                    # 不在チェックイン
    SENTIMENT_DECLINE = "sentiment_decline"  # センチメント悪化
    FOLLOW_UP = "follow_up"                # フォローアップ
    SCHEDULED = "scheduled"                # 定期チェックイン
    MILESTONE = "milestone"                # マイルストーン（記念日など）
    CRISIS_FOLLOW_UP = "crisis_follow_up"  # 危機後フォローアップ


@dataclass
class OutreachDecision:
    """アウトリーチ判断結果"""
    should_reach_out: bool
    reason: Optional[OutreachReason] = None
    message: Optional[str] = None
    priority: int = 0  # 0-10, 高いほど優先
    user_id: Optional[str] = None  # ユーザーID（バッチ処理用）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_reach_out": self.should_reach_out,
            "reason": self.reason.value if self.reason else None,
            "message": self.message,
            "priority": self.priority,
            "user_id": self.user_id,
        }


@dataclass
class ScheduledOutreach:
    """スケジュールされたアウトリーチ"""
    user_id: str
    scheduled_at: datetime
    reason: OutreachReason
    message: str
    executed: bool = False
    executed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "scheduled_at": self.scheduled_at.isoformat(),
            "reason": self.reason.value,
            "message": self.message,
            "executed": self.executed,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }


class ProactiveOutreachService:
    """
    プロアクティブアウトリーチサービス

    Bot APIの最大の差別化ポイント。
    ユーザーが連絡しなくても、パターン検出でBotから先にチェックインする。

    メンタルファースト:
    - 関係性フェーズに応じたトーン
    - ユーザーの好みを反映
    - 押しつけがましくないメッセージ
    """

    def __init__(
        self,
        storage: IStorage,
        emotion_service: Optional[EmotionService] = None,
    ):
        self.storage = storage
        self.emotion_service = emotion_service or EmotionService()

        # フェーズ別の不在チェックインメッセージ
        self._absence_messages_by_phase = {
            RelationshipPhase.STRANGER: [
                "お話しできる時がありましたら、いつでもどうぞ。",
                "何かあれば、気軽にご連絡ください。",
            ],
            RelationshipPhase.ACQUAINTANCE: [
                "最近いかがですか？",
                "お元気ですか？何かあればいつでもどうぞ。",
                "しばらく経ちましたね。調子はいかがでしょう？",
            ],
            RelationshipPhase.FAMILIAR: [
                "最近どう？元気にしてる？",
                "久しぶり！何か変わったことあった？",
                "ちょっと気になって。調子はどう？",
            ],
            RelationshipPhase.TRUSTED: [
                "久しぶりだね。元気？",
                "最近どうしてるかなって思って。",
                "連絡なかったから、ちょっと気になってた。",
            ],
        }

        # フェーズ別のセンチメント悪化時メッセージ
        self._sentiment_messages_by_phase = {
            RelationshipPhase.STRANGER: [
                "最近いろいろあるようでしたら、お話しください。",
                "何かお力になれることがあれば、いつでもどうぞ。",
            ],
            RelationshipPhase.ACQUAINTANCE: [
                "最近いろいろあるようですね。話したいことがあればいつでもどうぞ。",
                "大変な時期が続いているようですが、少しでも力になれたら嬉しいです。",
            ],
            RelationshipPhase.FAMILIAR: [
                "最近大変そうだったから、気になってた。話したかったら聞くよ。",
                "無理しないでね。いつでも話聞くから。",
            ],
            RelationshipPhase.TRUSTED: [
                "最近つらそうだったから心配してた。話したくなったらいつでも。",
                "大丈夫？無理しないで、いつでも話そう。",
            ],
        }

        # フェーズ別のフォローアップテンプレート
        self._follow_up_templates_by_phase = {
            RelationshipPhase.STRANGER: {
                "career": "お仕事の件、その後いかがでしょうか？",
                "relationship": "対人関係のこと、その後いかがですか？",
                "family": "ご家族のこと、その後いかがでしょうか？",
                "health": "体調はいかがですか？",
                "general_support": "前回のこと、その後いかがですか？",
            },
            RelationshipPhase.ACQUAINTANCE: {
                "career": "お仕事の件、その後どうですか？",
                "relationship": "恋愛のこと、その後進展はありましたか？",
                "family": "ご家族のこと、その後いかがですか？",
                "health": "体調はいかがですか？良くなっていると嬉しいのですが。",
                "general_support": "前回お話しした件、その後どうですか？",
            },
            RelationshipPhase.FAMILIAR: {
                "career": "仕事の件、どうなった？",
                "relationship": "あの人との関係、その後どう？",
                "family": "家族のこと、落ち着いた？",
                "health": "体調良くなった？心配してたんだ。",
                "general_support": "前に話してたこと、その後どう？",
            },
            RelationshipPhase.TRUSTED: {
                "career": "仕事の件、どうなったか気になってた。",
                "relationship": "あの人とのこと、どうなった？",
                "family": "家族のこと、大丈夫だった？",
                "health": "体調、良くなった？ずっと気になってた。",
                "general_support": "この前のこと、その後どう？",
            },
        }

        # フェーズ別のマイルストーンメッセージ
        self._milestone_messages_by_phase = {
            RelationshipPhase.STRANGER: {
                30: "お話しし始めて1ヶ月ですね。いつでもお気軽にどうぞ。",
                100: "100回お話ししましたね。ありがとうございます。",
                365: "1年が経ちましたね。これからもよろしくお願いします。",
            },
            RelationshipPhase.ACQUAINTANCE: {
                30: "お話しし始めて1ヶ月ですね。いつもありがとうございます。",
                100: "100回目の会話ですね！いつも話してくれてありがとう。",
                365: "1年間のお付き合いですね。これからもよろしくお願いします。",
            },
            RelationshipPhase.FAMILIAR: {
                30: "1ヶ月だね！いつも話してくれてありがとう。",
                100: "100回目！すごいね、いつもありがとう。",
                365: "1年間ありがとう！これからもよろしくね。",
            },
            RelationshipPhase.TRUSTED: {
                30: "1ヶ月か〜。いつも話してくれて嬉しいよ。",
                100: "100回目だね！いつもありがとう、これからもよろしく。",
                365: "もう1年になるんだね。いつもありがとう。",
            },
        }

    async def analyze_user_patterns(self, user_id: str) -> OutreachDecision:
        """
        ユーザーのパターンを分析してチェックインが必要か判断

        Args:
            user_id: ユーザーID

        Returns:
            OutreachDecision: チェックイン判断結果
        """
        user = await self.storage.load_user(user_id)
        if user is None:
            return OutreachDecision(should_reach_out=False)

        # プロアクティブが無効なら何もしない
        if not user.proactive.enabled:
            return OutreachDecision(should_reach_out=False)

        # 各種チェックを優先度順に実行
        decisions = []

        # 0. 危機後フォローアップ（最優先）
        crisis_decision = self._check_crisis_follow_up(user)
        if crisis_decision.should_reach_out:
            decisions.append(crisis_decision)

        # 1. センチメント悪化チェック（危機予防）
        if user.proactive.sentiment_check_enabled:
            sentiment_decision = self._check_sentiment_decline(user)
            if sentiment_decision.should_reach_out:
                decisions.append(sentiment_decision)

        # 2. 不在チェック
        if user.proactive.absence_check_enabled:
            absence_decision = self._check_absence(user)
            if absence_decision.should_reach_out:
                decisions.append(absence_decision)

        # 3. フォローアップチェック
        if user.proactive.follow_up_enabled:
            follow_up_decision = self._check_follow_up(user)
            if follow_up_decision.should_reach_out:
                decisions.append(follow_up_decision)

        # 4. マイルストーンチェック
        milestone_decision = self._check_milestone(user)
        if milestone_decision.should_reach_out:
            decisions.append(milestone_decision)

        # 最も優先度の高い判断を返す
        if decisions:
            decisions.sort(key=lambda d: d.priority, reverse=True)
            best = decisions[0]
            best.user_id = user_id
            return best

        return OutreachDecision(should_reach_out=False, user_id=user_id)

    def _check_crisis_follow_up(self, user: UserState) -> OutreachDecision:
        """危機後のフォローアップをチェック"""
        # 最近のエピソードで危機があったか確認
        recent_episodes = user.get_recent_episodes(3)
        for episode in recent_episodes:
            # エピソードのトピックに "crisis" が含まれているか
            if "crisis" in episode.topics or episode.importance_score >= 0.9:
                days_since = (datetime.now() - episode.created_at).days

                # 危機から1日〜3日以内ならフォローアップ
                if 1 <= days_since <= 3:
                    message = self._get_personalized_crisis_follow_up(user)
                    return OutreachDecision(
                        should_reach_out=True,
                        reason=OutreachReason.CRISIS_FOLLOW_UP,
                        message=message,
                        priority=10,  # 最高優先度
                    )

        return OutreachDecision(should_reach_out=False)

    def _get_personalized_crisis_follow_up(self, user: UserState) -> str:
        """パーソナライズされた危機フォローアップメッセージ"""
        phase = user.phase
        name = user.display_name

        if phase in [RelationshipPhase.TRUSTED, RelationshipPhase.FAMILIAR]:
            if name:
                messages = [
                    f"{name}、前回のこと心配してた。今は大丈夫？",
                    f"{name}、その後どう？少しでも落ち着いたかな。",
                ]
            else:
                messages = [
                    "前回のこと心配してた。今は大丈夫？",
                    "その後どう？少しでも落ち着いたかな。",
                ]
        else:
            messages = [
                "前回のこと、気になっていました。その後いかがですか？",
                "少しでも落ち着かれましたか？何かあればいつでもどうぞ。",
            ]

        return random.choice(messages)

    def _check_absence(self, user: UserState) -> OutreachDecision:
        """不在パターンをチェック（パーソナライズ版）"""
        days_since_last = (datetime.now() - user.last_interaction).days
        threshold = user.proactive.absence_threshold_days

        if days_since_last >= threshold:
            message = self._get_personalized_absence_message(user, days_since_last)

            return OutreachDecision(
                should_reach_out=True,
                reason=OutreachReason.ABSENCE,
                message=message,
                priority=8,
            )

        return OutreachDecision(should_reach_out=False)

    def _get_personalized_absence_message(self, user: UserState, days: int) -> str:
        """パーソナライズされた不在メッセージ"""
        phase = user.phase
        messages = self._absence_messages_by_phase.get(
            phase, self._absence_messages_by_phase[RelationshipPhase.ACQUAINTANCE]
        )

        # 名前がある場合は追加
        message = random.choice(messages)
        if user.display_name and phase in [RelationshipPhase.FAMILIAR, RelationshipPhase.TRUSTED]:
            message = f"{user.display_name}、{message}"

        return message

    def _check_sentiment_decline(self, user: UserState) -> OutreachDecision:
        """センチメント悪化をチェック（パーソナライズ版）"""
        patterns = user.emotional_patterns
        if not patterns:
            return OutreachDecision(should_reach_out=False)

        total = sum(patterns.values())
        if total < 3:  # 最低3回の会話が必要
            return OutreachDecision(should_reach_out=False)

        # ネガティブ感情の割合を計算
        negative_count = sum(
            patterns.get(e.value, 0) for e in NEGATIVE_EMOTIONS
        )
        negative_ratio = negative_count / total

        if negative_ratio > 0.6:
            message = self._get_personalized_sentiment_message(user)

            return OutreachDecision(
                should_reach_out=True,
                reason=OutreachReason.SENTIMENT_DECLINE,
                message=message,
                priority=9,  # 高優先度（危機予防）
            )

        return OutreachDecision(should_reach_out=False)

    def _get_personalized_sentiment_message(self, user: UserState) -> str:
        """パーソナライズされたセンチメントメッセージ"""
        phase = user.phase
        messages = self._sentiment_messages_by_phase.get(
            phase, self._sentiment_messages_by_phase[RelationshipPhase.ACQUAINTANCE]
        )

        message = random.choice(messages)
        if user.display_name and phase in [RelationshipPhase.FAMILIAR, RelationshipPhase.TRUSTED]:
            message = f"{user.display_name}、{message}"

        return message

    def _check_follow_up(self, user: UserState) -> OutreachDecision:
        """フォローアップが必要かチェック（パーソナライズ版）"""
        recent_episodes = user.get_recent_episodes(5)
        if not recent_episodes:
            return OutreachDecision(should_reach_out=False)

        # 最後のエピソードから3日以上経過している場合
        last_episode = recent_episodes[0]
        days_since_episode = (datetime.now() - last_episode.created_at).days

        if days_since_episode >= 3:
            topic = last_episode.topics[0] if last_episode.topics else "general_support"
            message = self._get_personalized_follow_up_message(user, topic)

            return OutreachDecision(
                should_reach_out=True,
                reason=OutreachReason.FOLLOW_UP,
                message=message,
                priority=5,
            )

        return OutreachDecision(should_reach_out=False)

    def _get_personalized_follow_up_message(self, user: UserState, topic: str) -> str:
        """パーソナライズされたフォローアップメッセージ"""
        phase = user.phase
        templates = self._follow_up_templates_by_phase.get(
            phase, self._follow_up_templates_by_phase[RelationshipPhase.ACQUAINTANCE]
        )

        message = templates.get(topic, templates["general_support"])

        if user.display_name and phase in [RelationshipPhase.FAMILIAR, RelationshipPhase.TRUSTED]:
            message = f"{user.display_name}、{message}"

        return message

    def _check_milestone(self, user: UserState) -> OutreachDecision:
        """マイルストーン（記念日など）をチェック（パーソナライズ版）"""
        days_since_first = (datetime.now() - user.first_interaction).days
        phase = user.phase
        milestones = self._milestone_messages_by_phase.get(
            phase, self._milestone_messages_by_phase[RelationshipPhase.ACQUAINTANCE]
        )

        for milestone_days, message in milestones.items():
            if abs(days_since_first - milestone_days) <= 1:
                if user.display_name and phase in [RelationshipPhase.FAMILIAR, RelationshipPhase.TRUSTED]:
                    message = f"{user.display_name}、{message}"

                return OutreachDecision(
                    should_reach_out=True,
                    reason=OutreachReason.MILESTONE,
                    message=message,
                    priority=3,
                )

        # インタラクション数のマイルストーン
        interactions = user.total_interactions
        if interactions in [10, 50, 100, 500, 1000]:
            if phase in [RelationshipPhase.TRUSTED, RelationshipPhase.FAMILIAR]:
                message = f"{interactions}回目だね！いつもありがとう。"
            else:
                message = f"{interactions}回目の会話ですね！ありがとうございます。"

            if user.display_name and phase in [RelationshipPhase.FAMILIAR, RelationshipPhase.TRUSTED]:
                message = f"{user.display_name}、{message}"

            return OutreachDecision(
                should_reach_out=True,
                reason=OutreachReason.MILESTONE,
                message=message,
                priority=3,
            )

        return OutreachDecision(should_reach_out=False)

    async def get_users_needing_outreach(self) -> List[OutreachDecision]:
        """
        チェックインが必要なすべてのユーザーを取得

        Returns:
            List[OutreachDecision]: チェックインが必要なユーザーのリスト
        """
        all_users = await self.storage.list_users()
        decisions = []

        for user_id in all_users:
            decision = await self.analyze_user_patterns(user_id)
            if decision.should_reach_out:
                decisions.append(decision)

        # 優先度順にソート
        decisions.sort(key=lambda d: d.priority, reverse=True)
        return decisions

    async def execute_outreach(
        self,
        user_id: str,
        decision: OutreachDecision,
        platform_sender: callable,
    ) -> bool:
        """
        アウトリーチを実行

        Args:
            user_id: ユーザーID
            decision: チェックイン判断結果
            platform_sender: プラットフォーム固有の送信関数

        Returns:
            bool: 成功したかどうか
        """
        if not decision.should_reach_out or not decision.message:
            return False

        try:
            # プラットフォーム経由でメッセージ送信
            await platform_sender(user_id, decision.message)

            # ユーザーのプロアクティブ設定を更新
            user = await self.storage.load_user(user_id)
            if user:
                user.proactive.last_outreach = datetime.now()
                await self.storage.save_user(user)

            return True

        except Exception:
            return False

    async def update_outreach_settings(
        self,
        user_id: str,
        enabled: Optional[bool] = None,
        frequency: Optional[str] = None,
        preferred_time: Optional[str] = None,
    ) -> bool:
        """
        ユーザーのプロアクティブ設定を更新

        Args:
            user_id: ユーザーID
            enabled: 有効/無効
            frequency: 頻度 ("daily", "weekly", "never")
            preferred_time: 希望時間 ("09:00" 形式)

        Returns:
            bool: 成功したかどうか
        """
        user = await self.storage.load_user(user_id)
        if user is None:
            return False

        if enabled is not None:
            user.proactive.enabled = enabled
        if frequency is not None:
            user.proactive.frequency = frequency
        if preferred_time is not None:
            user.proactive.preferred_time = preferred_time

        await self.storage.save_user(user)
        return True
