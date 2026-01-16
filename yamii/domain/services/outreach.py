"""
プロアクティブアウトリーチサービス
Bot APIならではの機能 - ユーザーに先にチェックインする

ChatGPT/Claude/Gemini WebUIやAwarefy/Ubieが提供できない
独自の価値を提供する核心機能
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..models.user import UserState
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


@dataclass
class OutreachDecision:
    """アウトリーチ判断結果"""
    should_reach_out: bool
    reason: Optional[OutreachReason] = None
    message: Optional[str] = None
    priority: int = 0  # 0-10, 高いほど優先

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_reach_out": self.should_reach_out,
            "reason": self.reason.value if self.reason else None,
            "message": self.message,
            "priority": self.priority,
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
    """

    def __init__(
        self,
        storage: IStorage,
        emotion_service: Optional[EmotionService] = None,
    ):
        self.storage = storage
        self.emotion_service = emotion_service or EmotionService()

        # チェックインメッセージテンプレート
        self._absence_messages = [
            "最近お話ししていませんね。調子はいかがですか？",
            "しばらく連絡がありませんでしたが、お元気ですか？",
            "久しぶりですね。何か変わったことはありましたか？",
        ]

        self._sentiment_messages = [
            "最近いろいろあるようですね。話したいことがあればいつでもどうぞ。",
            "大変な時期が続いているようですが、少しでも力になれたら嬉しいです。",
            "無理しないでくださいね。いつでも聞きますよ。",
        ]

        self._follow_up_templates = {
            "career": "お仕事の件、その後どうですか？",
            "relationship": "恋愛のこと、その後進展はありましたか？",
            "family": "ご家族のこと、その後いかがですか？",
            "health": "体調はいかがですか？良くなっていると嬉しいのですが。",
            "general_support": "前回お話しした件、その後どうですか？",
        }

        self._milestone_messages = {
            30: "お話しし始めて1ヶ月ですね。いつもありがとうございます。",
            100: "100回目の会話ですね！いつも話してくれてありがとう。",
            365: "1年間のお付き合いですね。これからもよろしくお願いします。",
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

        # 1. 不在チェック（最優先）
        if user.proactive.absence_check_enabled:
            absence_decision = self._check_absence(user)
            if absence_decision.should_reach_out:
                decisions.append(absence_decision)

        # 2. センチメント悪化チェック
        if user.proactive.sentiment_check_enabled:
            sentiment_decision = self._check_sentiment_decline(user)
            if sentiment_decision.should_reach_out:
                decisions.append(sentiment_decision)

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
            return decisions[0]

        return OutreachDecision(should_reach_out=False)

    def _check_absence(self, user: UserState) -> OutreachDecision:
        """不在パターンをチェック"""
        days_since_last = (datetime.now() - user.last_interaction).days
        threshold = user.proactive.absence_threshold_days

        if days_since_last >= threshold:
            # 不在期間に応じてメッセージを選択
            message_index = min(days_since_last // threshold, len(self._absence_messages) - 1)
            message = self._absence_messages[message_index]

            return OutreachDecision(
                should_reach_out=True,
                reason=OutreachReason.ABSENCE,
                message=message,
                priority=8,  # 高優先度
            )

        return OutreachDecision(should_reach_out=False)

    def _check_sentiment_decline(self, user: UserState) -> OutreachDecision:
        """センチメント悪化をチェック"""
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
            import random
            message = random.choice(self._sentiment_messages)

            return OutreachDecision(
                should_reach_out=True,
                reason=OutreachReason.SENTIMENT_DECLINE,
                message=message,
                priority=9,  # 最高優先度（危機予防）
            )

        return OutreachDecision(should_reach_out=False)

    def _check_follow_up(self, user: UserState) -> OutreachDecision:
        """フォローアップが必要かチェック"""
        # 最近のエピソードを確認
        recent_episodes = user.get_recent_episodes(5)
        if not recent_episodes:
            return OutreachDecision(should_reach_out=False)

        # 最後のエピソードから3日以上経過している場合
        last_episode = recent_episodes[0]
        days_since_episode = (datetime.now() - last_episode.created_at).days

        if days_since_episode >= 3:
            # トピックに基づいたフォローアップメッセージ
            topic = last_episode.topics[0] if last_episode.topics else "general_support"
            message = self._follow_up_templates.get(
                topic,
                self._follow_up_templates["general_support"]
            )

            return OutreachDecision(
                should_reach_out=True,
                reason=OutreachReason.FOLLOW_UP,
                message=message,
                priority=5,
            )

        return OutreachDecision(should_reach_out=False)

    def _check_milestone(self, user: UserState) -> OutreachDecision:
        """マイルストーン（記念日など）をチェック"""
        # 会話開始からの日数
        days_since_first = (datetime.now() - user.first_interaction).days

        for milestone_days, message in self._milestone_messages.items():
            # マイルストーン日の前後1日以内
            if abs(days_since_first - milestone_days) <= 1:
                return OutreachDecision(
                    should_reach_out=True,
                    reason=OutreachReason.MILESTONE,
                    message=message,
                    priority=3,
                )

        # インタラクション数のマイルストーン
        interactions = user.total_interactions
        if interactions in [10, 50, 100, 500, 1000]:
            message = f"{interactions}回目の会話ですね！いつもありがとうございます。"
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
                # user_idを追加情報として保持
                decision_with_user = OutreachDecision(
                    should_reach_out=True,
                    reason=decision.reason,
                    message=f"[{user_id}] {decision.message}",
                    priority=decision.priority,
                )
                decisions.append(decision_with_user)

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
