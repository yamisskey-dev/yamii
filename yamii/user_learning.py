"""
ユーザー学習データシステム
トピック関心度、会話スタイル、センチメント履歴を蓄積・学習
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from pathlib import Path


class CommunicationStyle(Enum):
    """コミュニケーションスタイル"""
    FORMAL = "formal"          # フォーマル
    CASUAL = "casual"          # カジュアル
    BALANCED = "balanced"      # バランス型


class ResponseLength(Enum):
    """応答長の好み"""
    SHORT = "short"            # 短い
    NORMAL = "normal"          # 通常
    DETAILED = "detailed"      # 詳細


class TechnicalLevel(Enum):
    """技術レベル"""
    BEGINNER = "beginner"      # 初級
    INTERMEDIATE = "intermediate"  # 中級
    ADVANCED = "advanced"      # 上級


@dataclass
class UserPreferences:
    """ユーザー設定"""
    communication_style: CommunicationStyle = CommunicationStyle.BALANCED
    response_length: ResponseLength = ResponseLength.NORMAL
    technical_level: TechnicalLevel = TechnicalLevel.INTERMEDIATE
    language: str = "ja"
    timezone: str = "Asia/Tokyo"
    use_emoji: bool = False
    custom_instructions: str = ""
    theme_list: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "communication_style": self.communication_style.value,
            "response_length": self.response_length.value,
            "technical_level": self.technical_level.value,
            "language": self.language,
            "timezone": self.timezone,
            "use_emoji": self.use_emoji,
            "custom_instructions": self.custom_instructions,
            "theme_list": self.theme_list
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        return cls(
            communication_style=CommunicationStyle(data.get("communication_style", "balanced")),
            response_length=ResponseLength(data.get("response_length", "normal")),
            technical_level=TechnicalLevel(data.get("technical_level", "intermediate")),
            language=data.get("language", "ja"),
            timezone=data.get("timezone", "Asia/Tokyo"),
            use_emoji=data.get("use_emoji", False),
            custom_instructions=data.get("custom_instructions", ""),
            theme_list=data.get("theme_list", [])
        )


@dataclass
class TopicInterest:
    """トピック関心度"""
    topic: str
    score: float  # 0.0 - 1.0
    mention_count: int = 0
    last_mentioned: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "score": self.score,
            "mention_count": self.mention_count,
            "last_mentioned": self.last_mentioned.isoformat() if self.last_mentioned else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TopicInterest":
        return cls(
            topic=data["topic"],
            score=data["score"],
            mention_count=data.get("mention_count", 0),
            last_mentioned=datetime.fromisoformat(data["last_mentioned"]) if data.get("last_mentioned") else None
        )


@dataclass
class SentimentRecord:
    """センチメント記録"""
    positive: float = 0.0
    neutral: float = 0.0
    negative: float = 0.0
    recorded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "positive": self.positive,
            "neutral": self.neutral,
            "negative": self.negative,
            "recorded_at": self.recorded_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SentimentRecord":
        return cls(
            positive=data.get("positive", 0.0),
            neutral=data.get("neutral", 0.0),
            negative=data.get("negative", 0.0),
            recorded_at=datetime.fromisoformat(data.get("recorded_at", datetime.now().isoformat()))
        )


@dataclass
class InteractionStats:
    """インタラクション統計"""
    total_interactions: int = 0
    total_messages: int = 0
    average_message_length: float = 0.0
    average_response_satisfaction: float = 0.5  # 0.0 - 1.0
    most_active_hours: List[int] = field(default_factory=list)  # 0-23
    most_active_days: List[str] = field(default_factory=list)  # 曜日

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_interactions": self.total_interactions,
            "total_messages": self.total_messages,
            "average_message_length": self.average_message_length,
            "average_response_satisfaction": self.average_response_satisfaction,
            "most_active_hours": self.most_active_hours,
            "most_active_days": self.most_active_days
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteractionStats":
        return cls(
            total_interactions=data.get("total_interactions", 0),
            total_messages=data.get("total_messages", 0),
            average_message_length=data.get("average_message_length", 0.0),
            average_response_satisfaction=data.get("average_response_satisfaction", 0.5),
            most_active_hours=data.get("most_active_hours", []),
            most_active_days=data.get("most_active_days", [])
        )


@dataclass
class UserLearningData:
    """ユーザー学習データ"""
    topic_interests: Dict[str, TopicInterest] = field(default_factory=dict)
    conversation_style_patterns: Dict[str, int] = field(default_factory=dict)
    sentiment_history: List[SentimentRecord] = field(default_factory=list)
    vocabulary_level: float = 0.5  # 0.0 - 1.0
    response_patterns: Dict[str, int] = field(default_factory=dict)
    interaction_stats: InteractionStats = field(default_factory=InteractionStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_interests": {k: v.to_dict() for k, v in self.topic_interests.items()},
            "conversation_style_patterns": self.conversation_style_patterns,
            "sentiment_history": [s.to_dict() for s in self.sentiment_history[-50:]],  # 最新50件
            "vocabulary_level": self.vocabulary_level,
            "response_patterns": self.response_patterns,
            "interaction_stats": self.interaction_stats.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserLearningData":
        return cls(
            topic_interests={k: TopicInterest.from_dict(v) for k, v in data.get("topic_interests", {}).items()},
            conversation_style_patterns=data.get("conversation_style_patterns", {}),
            sentiment_history=[SentimentRecord.from_dict(s) for s in data.get("sentiment_history", [])],
            vocabulary_level=data.get("vocabulary_level", 0.5),
            response_patterns=data.get("response_patterns", {}),
            interaction_stats=InteractionStats.from_dict(data.get("interaction_stats", {}))
        )


@dataclass
class EnhancedUserProfile:
    """拡張ユーザープロファイル"""
    id: str
    user_id: str
    username: str
    display_name: str = ""

    # 時系列情報
    first_seen: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    interaction_count: int = 0

    # 設定とデータ
    preferences: UserPreferences = field(default_factory=UserPreferences)
    learning_data: UserLearningData = field(default_factory=UserLearningData)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "first_seen": self.first_seen.isoformat(),
            "last_interaction": self.last_interaction.isoformat(),
            "interaction_count": self.interaction_count,
            "preferences": self.preferences.to_dict(),
            "learning_data": self.learning_data.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnhancedUserProfile":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            username=data["username"],
            display_name=data.get("display_name", ""),
            first_seen=datetime.fromisoformat(data.get("first_seen", datetime.now().isoformat())),
            last_interaction=datetime.fromisoformat(data.get("last_interaction", datetime.now().isoformat())),
            interaction_count=data.get("interaction_count", 0),
            preferences=UserPreferences.from_dict(data.get("preferences", {})),
            learning_data=UserLearningData.from_dict(data.get("learning_data", {}))
        )

    def add_topic_interest(self, topic: str, score_delta: float = 0.1) -> None:
        """トピック関心度を追加・更新"""
        if topic in self.learning_data.topic_interests:
            interest = self.learning_data.topic_interests[topic]
            interest.score = min(interest.score + score_delta, 1.0)
            interest.mention_count += 1
            interest.last_mentioned = datetime.now()
        else:
            self.learning_data.topic_interests[topic] = TopicInterest(
                topic=topic,
                score=score_delta,
                mention_count=1,
                last_mentioned=datetime.now()
            )

    def get_top_topics(self, n: int = 5) -> List[TopicInterest]:
        """上位Nトピックを取得"""
        sorted_topics = sorted(
            self.learning_data.topic_interests.values(),
            key=lambda x: x.score,
            reverse=True
        )
        return sorted_topics[:n]

    def should_learn(self) -> bool:
        """学習すべきかどうか"""
        # 新規ユーザーまたは非アクティブユーザー
        if self.interaction_count < 3:
            return True

        # 最後のインタラクションから30日以上経過
        days_since_last = (datetime.now() - self.last_interaction).days
        if days_since_last > 30:
            return True

        return False

    def record_interaction(self, message_length: int) -> None:
        """インタラクションを記録"""
        self.interaction_count += 1
        self.last_interaction = datetime.now()

        stats = self.learning_data.interaction_stats
        stats.total_interactions += 1
        stats.total_messages += 1

        # 平均メッセージ長の更新
        total_length = stats.average_message_length * (stats.total_messages - 1)
        stats.average_message_length = (total_length + message_length) / stats.total_messages

        # アクティブ時間の記録
        current_hour = datetime.now().hour
        if current_hour not in stats.most_active_hours:
            stats.most_active_hours.append(current_hour)
            stats.most_active_hours = sorted(stats.most_active_hours)[-5:]  # 上位5時間

        # アクティブ曜日の記録
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        current_day = weekdays[datetime.now().weekday()]
        if current_day not in stats.most_active_days:
            stats.most_active_days.append(current_day)


class UserLearningManager:
    """ユーザー学習マネージャー"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.profiles_file = self.data_dir / "enhanced_user_profiles.json"
        self.data_dir.mkdir(exist_ok=True)

        self._profiles: Dict[str, EnhancedUserProfile] = {}
        self._load_profiles()

    def _load_profiles(self) -> None:
        """プロファイルを読み込み"""
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, profile_data in data.get("profiles", {}).items():
                        self._profiles[user_id] = EnhancedUserProfile.from_dict(profile_data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"プロファイル読み込みエラー: {e}")

    def _save_profiles(self) -> None:
        """プロファイルを保存"""
        data = {
            "profiles": {uid: p.to_dict() for uid, p in self._profiles.items()},
            "updated_at": datetime.now().isoformat()
        }
        with open(self.profiles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_or_create_profile(self, user_id: str, username: str = "") -> EnhancedUserProfile:
        """プロファイルを取得または作成"""
        if user_id not in self._profiles:
            self._profiles[user_id] = EnhancedUserProfile(
                id=f"profile_{user_id}",
                user_id=user_id,
                username=username or user_id
            )
            self._save_profiles()
        return self._profiles[user_id]

    def update_from_message(
        self,
        user_id: str,
        message: str,
        topics: List[str],
        sentiment: str
    ) -> EnhancedUserProfile:
        """メッセージから学習データを更新"""
        profile = self.get_or_create_profile(user_id)

        # インタラクション記録
        profile.record_interaction(len(message))

        # トピック関心度の更新
        for topic in topics:
            profile.add_topic_interest(topic)

        # センチメント履歴の更新
        sentiment_record = SentimentRecord()
        if sentiment == "positive":
            sentiment_record.positive = 1.0
        elif sentiment == "negative":
            sentiment_record.negative = 1.0
        else:
            sentiment_record.neutral = 1.0
        profile.learning_data.sentiment_history.append(sentiment_record)

        # 会話スタイルパターンの更新
        if len(message) < 50:
            style = "short"
        elif len(message) > 200:
            style = "long"
        else:
            style = "medium"
        profile.learning_data.conversation_style_patterns[style] = \
            profile.learning_data.conversation_style_patterns.get(style, 0) + 1

        # 語彙レベルの更新（簡易版）
        avg_word_length = len(message) / max(message.count(" ") + 1, 1)
        profile.learning_data.vocabulary_level = min(
            profile.learning_data.vocabulary_level * 0.9 + (avg_word_length / 10) * 0.1,
            1.0
        )

        self._save_profiles()
        return profile

    def get_personalization_context(self, user_id: str) -> str:
        """個人化コンテキストを取得"""
        if user_id not in self._profiles:
            return ""

        profile = self._profiles[user_id]
        parts = []

        # 基本情報
        if profile.display_name:
            parts.append(f"ユーザー名: {profile.display_name}")

        # トップトピック
        top_topics = profile.get_top_topics(3)
        if top_topics:
            topics_text = ", ".join([t.topic for t in top_topics])
            parts.append(f"関心のあるトピック: {topics_text}")

        # コミュニケーションスタイル
        style = profile.preferences.communication_style
        style_text = {
            CommunicationStyle.FORMAL: "フォーマル",
            CommunicationStyle.CASUAL: "カジュアル",
            CommunicationStyle.BALANCED: "バランス型"
        }
        parts.append(f"好みのスタイル: {style_text[style]}")

        # 応答長の好み
        length = profile.preferences.response_length
        length_text = {
            ResponseLength.SHORT: "短い応答を好む",
            ResponseLength.NORMAL: "通常の長さ",
            ResponseLength.DETAILED: "詳細な説明を好む"
        }
        parts.append(f"応答長: {length_text[length]}")

        # 最近のセンチメント傾向
        recent_sentiment = profile.learning_data.sentiment_history[-10:]
        if recent_sentiment:
            pos = sum(s.positive for s in recent_sentiment) / len(recent_sentiment)
            neg = sum(s.negative for s in recent_sentiment) / len(recent_sentiment)
            if pos > 0.5:
                parts.append("最近の傾向: ポジティブ")
            elif neg > 0.5:
                parts.append("最近の傾向: サポートが必要")
            else:
                parts.append("最近の傾向: 安定")

        # カスタム指示
        if profile.preferences.custom_instructions:
            parts.append(f"カスタム指示: {profile.preferences.custom_instructions}")

        return "\n".join(parts)

    def update_preferences(
        self,
        user_id: str,
        communication_style: Optional[str] = None,
        response_length: Optional[str] = None,
        use_emoji: Optional[bool] = None,
        custom_instructions: Optional[str] = None
    ) -> EnhancedUserProfile:
        """ユーザー設定を更新"""
        profile = self.get_or_create_profile(user_id)

        if communication_style:
            profile.preferences.communication_style = CommunicationStyle(communication_style)
        if response_length:
            profile.preferences.response_length = ResponseLength(response_length)
        if use_emoji is not None:
            profile.preferences.use_emoji = use_emoji
        if custom_instructions is not None:
            profile.preferences.custom_instructions = custom_instructions

        self._save_profiles()
        return profile

    def get_profile_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """プロファイル統計を取得"""
        if user_id not in self._profiles:
            return None

        profile = self._profiles[user_id]
        return {
            "user_id": user_id,
            "interaction_count": profile.interaction_count,
            "days_since_first_seen": (datetime.now() - profile.first_seen).days,
            "top_topics": [t.to_dict() for t in profile.get_top_topics(5)],
            "average_message_length": profile.learning_data.interaction_stats.average_message_length,
            "most_active_hours": profile.learning_data.interaction_stats.most_active_hours,
            "vocabulary_level": profile.learning_data.vocabulary_level
        }

    def delete_profile(self, user_id: str) -> bool:
        """プロファイルを削除"""
        if user_id in self._profiles:
            del self._profiles[user_id]
            self._save_profiles()
            return True
        return False

    def export_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーデータをエクスポート（プライバシー対応）"""
        if user_id not in self._profiles:
            return None

        profile = self._profiles[user_id]
        return profile.to_dict()

    def list_all_users(self) -> List[str]:
        """全ユーザーIDを取得"""
        return list(self._profiles.keys())
