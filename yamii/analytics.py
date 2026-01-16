"""
分析・統計システム
ユーザーエンゲージメント分析、トピック分析、推奨事項生成
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from .conversation_summary import ConversationSummary, ConversationSummaryStore, SentimentType
from .user_learning import EnhancedUserProfile, UserLearningManager


class RecommendationType(Enum):
    """推奨タイプ"""
    ENGAGEMENT = "engagement"        # エンゲージメント向上
    TOPIC_EXPANSION = "topic_expansion"  # トピック拡大
    EMOTIONAL_SUPPORT = "emotional_support"  # 感情サポート
    ACTIVITY = "activity"            # アクティビティ提案


@dataclass
class TopicAnalysis:
    """トピック分析"""
    topic: str
    mention_count: int
    average_sentiment: float  # -1.0 to 1.0
    trend: str  # "increasing", "stable", "decreasing"
    last_discussed: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "mention_count": self.mention_count,
            "average_sentiment": self.average_sentiment,
            "trend": self.trend,
            "last_discussed": self.last_discussed.isoformat() if self.last_discussed else None
        }


@dataclass
class SentimentAnalysis:
    """センチメント分析"""
    overall_sentiment: float  # -1.0 to 1.0
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float
    trend: str  # "improving", "stable", "declining"
    recent_history: List[Tuple[datetime, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_sentiment": self.overall_sentiment,
            "positive_ratio": self.positive_ratio,
            "neutral_ratio": self.neutral_ratio,
            "negative_ratio": self.negative_ratio,
            "trend": self.trend,
            "recent_history": [(d.isoformat(), s) for d, s in self.recent_history[-10:]]
        }


@dataclass
class ActivityPattern:
    """活動パターン"""
    most_active_hours: List[int]
    most_active_days: List[str]
    average_session_length: float  # 分
    average_messages_per_session: float
    interaction_frequency: str  # "daily", "weekly", "occasional"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "most_active_hours": self.most_active_hours,
            "most_active_days": self.most_active_days,
            "average_session_length": self.average_session_length,
            "average_messages_per_session": self.average_messages_per_session,
            "interaction_frequency": self.interaction_frequency
        }


@dataclass
class Recommendation:
    """推奨事項"""
    type: RecommendationType
    title: str
    description: str
    priority: int  # 1-5 (5が最高)
    action_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "action_items": self.action_items
        }


@dataclass
class UserAnalytics:
    """ユーザー分析"""
    user_id: str
    engagement_score: float  # 0.0 - 1.0
    topic_analysis: List[TopicAnalysis]
    sentiment_analysis: SentimentAnalysis
    activity_pattern: ActivityPattern
    recommendations: List[Recommendation]
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "engagement_score": self.engagement_score,
            "topic_analysis": [t.to_dict() for t in self.topic_analysis],
            "sentiment_analysis": self.sentiment_analysis.to_dict(),
            "activity_pattern": self.activity_pattern.to_dict(),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "generated_at": self.generated_at.isoformat()
        }


@dataclass
class GlobalAnalytics:
    """グローバル分析"""
    total_users: int
    active_users: int  # 過去7日間
    average_engagement: float
    popular_topics: List[Tuple[str, int]]
    overall_sentiment_distribution: Dict[str, float]
    system_health_score: float  # 0.0 - 1.0
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_users": self.total_users,
            "active_users": self.active_users,
            "average_engagement": self.average_engagement,
            "popular_topics": self.popular_topics,
            "overall_sentiment_distribution": self.overall_sentiment_distribution,
            "system_health_score": self.system_health_score,
            "generated_at": self.generated_at.isoformat()
        }


class AnalyticsEngine:
    """分析エンジン"""

    def __init__(
        self,
        summary_store: ConversationSummaryStore,
        learning_manager: UserLearningManager
    ):
        self.summary_store = summary_store
        self.learning_manager = learning_manager

    def analyze_user(self, user_id: str) -> UserAnalytics:
        """
        ユーザー分析を実行

        Args:
            user_id: ユーザーID

        Returns:
            UserAnalytics
        """
        # サマリーを取得
        summaries = self.summary_store.get_user_summaries(user_id, limit=50)

        # プロファイルを取得
        profile = self.learning_manager.get_or_create_profile(user_id)

        # エンゲージメントスコア計算
        engagement_score = self._calculate_engagement_score(profile, summaries)

        # トピック分析
        topic_analysis = self._analyze_topics(summaries)

        # センチメント分析
        sentiment_analysis = self._analyze_sentiment(summaries)

        # 活動パターン分析
        activity_pattern = self._analyze_activity_pattern(profile, summaries)

        # 推奨事項生成
        recommendations = self._generate_recommendations(
            engagement_score, topic_analysis, sentiment_analysis, activity_pattern
        )

        return UserAnalytics(
            user_id=user_id,
            engagement_score=engagement_score,
            topic_analysis=topic_analysis,
            sentiment_analysis=sentiment_analysis,
            activity_pattern=activity_pattern,
            recommendations=recommendations
        )

    def _calculate_engagement_score(
        self,
        profile: EnhancedUserProfile,
        summaries: List[ConversationSummary]
    ) -> float:
        """エンゲージメントスコアを計算"""
        score = 0.0

        # インタラクション頻度（最大0.3）
        # 10回の交流で最大スコア
        interaction_score = min(profile.interaction_count / 10, 0.3)
        score += interaction_score

        # 会話深度（最大0.2）
        if summaries:
            avg_depth = sum(s.message_count for s in summaries) / len(summaries)
            depth_score = min(avg_depth / 10, 0.2)
            score += depth_score

        # トピック多様性（最大0.3）
        unique_topics = set()
        for summary in summaries:
            unique_topics.update(summary.topics)
        diversity_score = min(len(unique_topics) / 10, 0.3)
        score += diversity_score

        # 最近のアクティビティ（最大0.2）
        if profile.last_interaction:
            days_since_last = (datetime.now() - profile.last_interaction).days
            if days_since_last <= 7:
                score += 0.2
            elif days_since_last <= 14:
                score += 0.1
            elif days_since_last <= 30:
                score += 0.05

        return min(score, 1.0)

    def _analyze_topics(self, summaries: List[ConversationSummary]) -> List[TopicAnalysis]:
        """トピック分析"""
        topic_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "sentiments": [], "timestamps": []}
        )

        for summary in summaries:
            sentiment_value = {
                SentimentType.POSITIVE: 1.0,
                SentimentType.NEUTRAL: 0.0,
                SentimentType.NEGATIVE: -1.0
            }.get(summary.sentiment, 0.0)

            for topic in summary.topics:
                topic_data[topic]["count"] += 1
                topic_data[topic]["sentiments"].append(sentiment_value)
                topic_data[topic]["timestamps"].append(summary.end_time)

        analyses = []
        for topic, data in topic_data.items():
            # 平均センチメント
            avg_sentiment = sum(data["sentiments"]) / len(data["sentiments"]) if data["sentiments"] else 0.0

            # トレンド判定（最近vs過去）
            timestamps = sorted(data["timestamps"])
            if len(timestamps) >= 3:
                mid_point = len(timestamps) // 2
                recent_count = len([t for t in timestamps[mid_point:]])
                past_count = len([t for t in timestamps[:mid_point]])
                if recent_count > past_count * 1.5:
                    trend = "increasing"
                elif past_count > recent_count * 1.5:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            analyses.append(TopicAnalysis(
                topic=topic,
                mention_count=data["count"],
                average_sentiment=avg_sentiment,
                trend=trend,
                last_discussed=max(data["timestamps"]) if data["timestamps"] else None
            ))

        # 言及回数でソート
        analyses.sort(key=lambda x: x.mention_count, reverse=True)
        return analyses[:10]  # 上位10トピック

    def _analyze_sentiment(self, summaries: List[ConversationSummary]) -> SentimentAnalysis:
        """センチメント分析"""
        if not summaries:
            return SentimentAnalysis(
                overall_sentiment=0.0,
                positive_ratio=0.0,
                neutral_ratio=1.0,
                negative_ratio=0.0,
                trend="stable"
            )

        counts = {"positive": 0, "neutral": 0, "negative": 0}
        recent_history = []

        for summary in summaries:
            counts[summary.sentiment.value] += 1
            recent_history.append((summary.end_time, summary.sentiment.value))

        total = len(summaries)
        positive_ratio = counts["positive"] / total
        neutral_ratio = counts["neutral"] / total
        negative_ratio = counts["negative"] / total

        # 全体センチメント（-1.0 to 1.0）
        overall = (counts["positive"] - counts["negative"]) / total

        # トレンド判定
        if len(summaries) >= 4:
            mid = len(summaries) // 2
            recent_summaries = summaries[:mid]
            past_summaries = summaries[mid:]

            recent_positive = sum(1 for s in recent_summaries if s.sentiment == SentimentType.POSITIVE)
            past_positive = sum(1 for s in past_summaries if s.sentiment == SentimentType.POSITIVE)

            recent_rate = recent_positive / len(recent_summaries) if recent_summaries else 0
            past_rate = past_positive / len(past_summaries) if past_summaries else 0

            if recent_rate > past_rate + 0.1:
                trend = "improving"
            elif past_rate > recent_rate + 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return SentimentAnalysis(
            overall_sentiment=overall,
            positive_ratio=positive_ratio,
            neutral_ratio=neutral_ratio,
            negative_ratio=negative_ratio,
            trend=trend,
            recent_history=recent_history[-10:]
        )

    def _analyze_activity_pattern(
        self,
        profile: EnhancedUserProfile,
        summaries: List[ConversationSummary]
    ) -> ActivityPattern:
        """活動パターン分析"""
        stats = profile.learning_data.interaction_stats

        # セッション長計算
        session_lengths = []
        for summary in summaries:
            duration = (summary.end_time - summary.start_time).total_seconds() / 60
            if duration > 0:
                session_lengths.append(duration)

        avg_session_length = sum(session_lengths) / len(session_lengths) if session_lengths else 0

        # セッションあたりのメッセージ数
        avg_messages = sum(s.message_count for s in summaries) / len(summaries) if summaries else 0

        # インタラクション頻度
        if profile.interaction_count > 0:
            days_active = (datetime.now() - profile.first_seen).days + 1
            interactions_per_day = profile.interaction_count / days_active

            if interactions_per_day >= 1:
                frequency = "daily"
            elif interactions_per_day >= 0.14:  # 週1回以上
                frequency = "weekly"
            else:
                frequency = "occasional"
        else:
            frequency = "occasional"

        return ActivityPattern(
            most_active_hours=stats.most_active_hours[:5],
            most_active_days=stats.most_active_days[:3],
            average_session_length=avg_session_length,
            average_messages_per_session=avg_messages,
            interaction_frequency=frequency
        )

    def _generate_recommendations(
        self,
        engagement_score: float,
        topic_analysis: List[TopicAnalysis],
        sentiment_analysis: SentimentAnalysis,
        activity_pattern: ActivityPattern
    ) -> List[Recommendation]:
        """推奨事項を生成"""
        recommendations = []

        # エンゲージメント向上
        if engagement_score < 0.3:
            recommendations.append(Recommendation(
                type=RecommendationType.ENGAGEMENT,
                title="もっとお話しませんか？",
                description="最近の会話が少ないようです。気軽に相談してください。",
                priority=4,
                action_items=[
                    "日常の小さな悩みでも大丈夫です",
                    "新しい話題を試してみませんか？"
                ]
            ))

        # 感情サポート
        if sentiment_analysis.negative_ratio > 0.5:
            recommendations.append(Recommendation(
                type=RecommendationType.EMOTIONAL_SUPPORT,
                title="サポートが必要ですか？",
                description="最近、大変なことが多いようですね。",
                priority=5,
                action_items=[
                    "専門家への相談も検討してみてください",
                    "気持ちを話すだけでも楽になることがあります"
                ]
            ))

        # トピック拡大
        if len(topic_analysis) < 3:
            recommendations.append(Recommendation(
                type=RecommendationType.TOPIC_EXPANSION,
                title="新しい話題を試してみませんか？",
                description="様々なトピックについてお話しすることで、新しい視点が得られるかもしれません。",
                priority=2,
                action_items=[
                    "趣味や興味について教えてください",
                    "将来の夢や目標についてお話ししませんか？"
                ]
            ))

        # アクティビティ提案
        if activity_pattern.interaction_frequency == "occasional":
            recommendations.append(Recommendation(
                type=RecommendationType.ACTIVITY,
                title="定期的にお話ししませんか？",
                description="継続的な対話で、より深いサポートが可能になります。",
                priority=3,
                action_items=[
                    "週に1回、近況を教えてください",
                    "気になることがあればいつでもどうぞ"
                ]
            ))

        # 優先度でソート
        recommendations.sort(key=lambda x: x.priority, reverse=True)
        return recommendations

    def analyze_global(self) -> GlobalAnalytics:
        """
        グローバル分析を実行

        Returns:
            GlobalAnalytics
        """
        all_users = self.learning_manager.list_all_users()
        total_users = len(all_users)

        # アクティブユーザー数
        active_users = 0
        engagement_scores = []
        all_topics: Dict[str, int] = defaultdict(int)
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        total_summaries = 0

        for user_id in all_users:
            profile = self.learning_manager.get_or_create_profile(user_id)

            # 過去7日間にアクティブか
            if (datetime.now() - profile.last_interaction).days <= 7:
                active_users += 1

            # サマリー分析
            summaries = self.summary_store.get_user_summaries(user_id, limit=20)
            for summary in summaries:
                for topic in summary.topics:
                    all_topics[topic] += 1
                sentiment_counts[summary.sentiment.value] += 1
                total_summaries += 1

            # エンゲージメントスコア
            user_analytics = self.analyze_user(user_id)
            engagement_scores.append(user_analytics.engagement_score)

        # 平均エンゲージメント
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0

        # 人気トピック
        popular_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:10]

        # センチメント分布
        total_sentiment = sum(sentiment_counts.values()) or 1
        sentiment_distribution = {
            k: v / total_sentiment for k, v in sentiment_counts.items()
        }

        # システムヘルススコア
        health_score = self._calculate_system_health(
            total_users, active_users, avg_engagement, sentiment_distribution
        )

        return GlobalAnalytics(
            total_users=total_users,
            active_users=active_users,
            average_engagement=avg_engagement,
            popular_topics=popular_topics,
            overall_sentiment_distribution=sentiment_distribution,
            system_health_score=health_score
        )

    def _calculate_system_health(
        self,
        total_users: int,
        active_users: int,
        avg_engagement: float,
        sentiment_distribution: Dict[str, float]
    ) -> float:
        """システムヘルススコアを計算"""
        score = 0.0

        # アクティブユーザー比率（最大0.3）
        if total_users > 0:
            active_ratio = active_users / total_users
            score += min(active_ratio, 0.3)

        # 平均エンゲージメント（最大0.3）
        score += avg_engagement * 0.3

        # センチメントバランス（最大0.4）
        positive_ratio = sentiment_distribution.get("positive", 0)
        negative_ratio = sentiment_distribution.get("negative", 0)

        # ポジティブが多いほど良い、ネガティブが多いほど悪い
        sentiment_score = (positive_ratio - negative_ratio + 1) / 2  # 0-1に正規化
        score += sentiment_score * 0.4

        return min(score, 1.0)

    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """
        ユーザーインサイトを取得（簡易版）

        Args:
            user_id: ユーザーID

        Returns:
            Dict with key insights
        """
        analytics = self.analyze_user(user_id)

        insights = {
            "engagement_level": "高" if analytics.engagement_score > 0.6 else "中" if analytics.engagement_score > 0.3 else "低",
            "top_interests": [t.topic for t in analytics.topic_analysis[:3]],
            "emotional_trend": analytics.sentiment_analysis.trend,
            "activity_frequency": analytics.activity_pattern.interaction_frequency,
            "key_recommendations": [r.title for r in analytics.recommendations[:2]]
        }

        return insights
