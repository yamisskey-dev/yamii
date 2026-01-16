"""
会話サマリーシステム
長期記憶として会話を自動要約し、トピック・キーワード・重要度を抽出
"""

import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class SentimentType(Enum):
    """センチメントタイプ"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class MentionType(Enum):
    """ユーザー言及タイプ"""
    FACT = "fact"           # 事実情報
    PREFERENCE = "preference"  # 好み
    HABIT = "habit"         # 習慣
    OPINION = "opinion"     # 意見
    EXPERIENCE = "experience"  # 経験


@dataclass
class UserMention:
    """ユーザー言及情報"""
    mention_type: MentionType
    content: str
    confidence: float  # 0.0 - 1.0
    context: str
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mention_type": self.mention_type.value,
            "content": self.content,
            "confidence": self.confidence,
            "context": self.context,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserMention":
        return cls(
            mention_type=MentionType(data["mention_type"]),
            content=data["content"],
            confidence=data["confidence"],
            context=data["context"],
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        )


@dataclass
class ConversationSummary:
    """会話サマリー"""
    id: str
    user_id: str
    session_id: str
    start_time: datetime
    end_time: datetime
    message_count: int

    # サマリーデータ
    topics: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    main_questions: List[str] = field(default_factory=list)
    user_mentions: List[UserMention] = field(default_factory=list)

    # 検索・分析データ
    keywords: List[str] = field(default_factory=list)
    sentiment: SentimentType = SentimentType.NEUTRAL
    importance_score: float = 0.5  # 0.0 - 1.0

    # サマリーテキスト
    short_summary: str = ""  # 1-2行の要約
    detailed_summary: str = ""  # 詳細な説明

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "message_count": self.message_count,
            "topics": self.topics,
            "key_points": self.key_points,
            "main_questions": self.main_questions,
            "user_mentions": [m.to_dict() for m in self.user_mentions],
            "keywords": self.keywords,
            "sentiment": self.sentiment.value,
            "importance_score": self.importance_score,
            "short_summary": self.short_summary,
            "detailed_summary": self.detailed_summary
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSummary":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            message_count=data["message_count"],
            topics=data.get("topics", []),
            key_points=data.get("key_points", []),
            main_questions=data.get("main_questions", []),
            user_mentions=[UserMention.from_dict(m) for m in data.get("user_mentions", [])],
            keywords=data.get("keywords", []),
            sentiment=SentimentType(data.get("sentiment", "neutral")),
            importance_score=data.get("importance_score", 0.5),
            short_summary=data.get("short_summary", ""),
            detailed_summary=data.get("detailed_summary", "")
        )

    def add_topic(self, topic: str) -> None:
        """トピックを追加"""
        if topic and topic not in self.topics:
            self.topics.append(topic)

    def add_keyword(self, keyword: str) -> None:
        """キーワードを追加"""
        if keyword and keyword not in self.keywords:
            self.keywords.append(keyword)

    def add_user_mention(self, mention: UserMention) -> None:
        """ユーザー言及を追加"""
        self.user_mentions.append(mention)

    def is_empty(self) -> bool:
        """サマリーが空かどうか"""
        return not self.topics and not self.keywords and not self.short_summary


class ConversationSummarizer:
    """会話サマリー生成器"""

    def __init__(self):
        # トピック検出キーワード
        self._topic_keywords = {
            "仕事": ["仕事", "職場", "会社", "上司", "同僚", "転職", "キャリア", "残業"],
            "恋愛": ["恋愛", "彼氏", "彼女", "パートナー", "デート", "告白", "失恋"],
            "家族": ["家族", "親", "父", "母", "兄弟", "子供", "育児", "介護"],
            "友人関係": ["友達", "友人", "人間関係", "仲間", "付き合い"],
            "健康": ["健康", "病気", "体調", "病院", "治療", "メンタル", "うつ"],
            "お金": ["お金", "給料", "貯金", "借金", "投資", "節約"],
            "将来": ["将来", "夢", "目標", "進路", "人生設計"],
            "趣味": ["趣味", "ゲーム", "音楽", "映画", "旅行", "スポーツ"],
            "学業": ["勉強", "学校", "大学", "受験", "テスト", "成績"],
        }

        # 質問パターン
        self._question_patterns = [
            r".*[？?]$",
            r".*どう(すれば|したら|思い?ます?).*",
            r".*何(を|が|か).*",
            r".*教えて.*",
            r".*アドバイス.*",
        ]

    def summarize_conversation(
        self,
        user_id: str,
        session_id: str,
        messages: List[Dict[str, Any]],
        llm_summarize_func: Optional[callable] = None
    ) -> ConversationSummary:
        """
        会話を要約する

        Args:
            user_id: ユーザーID
            session_id: セッションID
            messages: 会話メッセージリスト [{"role": "user/assistant", "content": "..."}]
            llm_summarize_func: LLMを使った要約関数（オプション）

        Returns:
            ConversationSummary: 生成されたサマリー
        """
        if not messages:
            return self._create_empty_summary(user_id, session_id)

        # 基本情報の抽出
        start_time = self._get_message_time(messages[0])
        end_time = self._get_message_time(messages[-1])

        # ユーザーメッセージのみ抽出
        user_messages = [m["content"] for m in messages if m.get("role") == "user"]
        all_text = " ".join(user_messages)

        # トピック抽出
        topics = self._extract_topics(all_text)

        # キーワード抽出
        keywords = self._extract_keywords(all_text)

        # 質問抽出
        questions = self._extract_questions(user_messages)

        # センチメント分析
        sentiment = self._analyze_sentiment(all_text)

        # 重要度計算
        importance = self._calculate_importance(messages, topics, questions)

        # ユーザー言及抽出
        user_mentions = self._extract_user_mentions(user_messages)

        # 短い要約生成
        short_summary = self._generate_short_summary(topics, questions, sentiment)

        # 詳細要約生成（LLM使用時）
        detailed_summary = ""
        if llm_summarize_func:
            detailed_summary = llm_summarize_func(all_text)

        summary = ConversationSummary(
            id=f"summary_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            message_count=len(messages),
            topics=topics,
            key_points=[],  # LLMで抽出可能
            main_questions=questions,
            user_mentions=user_mentions,
            keywords=keywords,
            sentiment=sentiment,
            importance_score=importance,
            short_summary=short_summary,
            detailed_summary=detailed_summary
        )

        return summary

    def _create_empty_summary(self, user_id: str, session_id: str) -> ConversationSummary:
        """空のサマリーを作成"""
        now = datetime.now()
        return ConversationSummary(
            id=f"summary_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            session_id=session_id,
            start_time=now,
            end_time=now,
            message_count=0
        )

    def _get_message_time(self, message: Dict[str, Any]) -> datetime:
        """メッセージから時刻を取得"""
        if "timestamp" in message:
            if isinstance(message["timestamp"], datetime):
                return message["timestamp"]
            elif isinstance(message["timestamp"], (int, float)):
                return datetime.fromtimestamp(message["timestamp"])
            elif isinstance(message["timestamp"], str):
                return datetime.fromisoformat(message["timestamp"])
        return datetime.now()

    def _extract_topics(self, text: str) -> List[str]:
        """トピックを抽出"""
        detected_topics = []
        text_lower = text.lower()

        for topic, keywords in self._topic_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if topic not in detected_topics:
                        detected_topics.append(topic)
                    break

        return detected_topics

    def _extract_keywords(self, text: str) -> List[str]:
        """キーワードを抽出（簡易版）"""
        # 日本語の名詞を簡易抽出
        keywords = []

        # 重要そうな単語パターン
        important_patterns = [
            r"[一-龯]{2,}",  # 漢字2文字以上
        ]

        for pattern in important_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) >= 2 and match not in keywords:
                    keywords.append(match)
                    if len(keywords) >= 10:
                        break

        return keywords[:10]

    def _extract_questions(self, messages: List[str]) -> List[str]:
        """質問を抽出"""
        questions = []

        for message in messages:
            for pattern in self._question_patterns:
                if re.match(pattern, message):
                    questions.append(message[:100])  # 100文字まで
                    break

        return questions[:5]  # 最大5つ

    def _analyze_sentiment(self, text: str) -> SentimentType:
        """センチメント分析（簡易版）"""
        positive_words = ["嬉しい", "楽しい", "幸せ", "感謝", "良い", "最高", "素晴らしい"]
        negative_words = ["悲しい", "辛い", "苦しい", "困って", "不安", "心配", "嫌", "最悪"]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        if positive_count > negative_count:
            return SentimentType.POSITIVE
        elif negative_count > positive_count:
            return SentimentType.NEGATIVE
        return SentimentType.NEUTRAL

    def _calculate_importance(
        self,
        messages: List[Dict[str, Any]],
        topics: List[str],
        questions: List[str]
    ) -> float:
        """重要度を計算"""
        score = 0.0

        # メッセージ数に基づくスコア（最大0.3）
        message_score = min(len(messages) / 20, 0.3)
        score += message_score

        # トピック数に基づくスコア（最大0.3）
        topic_score = min(len(topics) / 5, 0.3)
        score += topic_score

        # 質問数に基づくスコア（最大0.4）
        question_score = min(len(questions) / 3, 0.4)
        score += question_score

        return min(score, 1.0)

    def _extract_user_mentions(self, messages: List[str]) -> List[UserMention]:
        """ユーザー言及を抽出"""
        mentions = []

        # 好みパターン
        preference_patterns = [
            (r"(.+)が好き", MentionType.PREFERENCE),
            (r"(.+)が嫌い", MentionType.PREFERENCE),
            (r"(.+)したい", MentionType.PREFERENCE),
        ]

        # 事実パターン
        fact_patterns = [
            (r"私は(.+)です", MentionType.FACT),
            (r"(.+)歳です", MentionType.FACT),
            (r"(.+)に住んで", MentionType.FACT),
            (r"(.+)で働いて", MentionType.FACT),
        ]

        all_patterns = preference_patterns + fact_patterns

        for message in messages:
            for pattern, mention_type in all_patterns:
                match = re.search(pattern, message)
                if match:
                    mentions.append(UserMention(
                        mention_type=mention_type,
                        content=match.group(0),
                        confidence=0.7,
                        context=message[:50]
                    ))

        return mentions[:10]  # 最大10個

    def _generate_short_summary(
        self,
        topics: List[str],
        questions: List[str],
        sentiment: SentimentType
    ) -> str:
        """短い要約を生成"""
        parts = []

        if topics:
            parts.append(f"話題: {', '.join(topics[:3])}")

        if questions:
            parts.append(f"質問{len(questions)}件")

        sentiment_text = {
            SentimentType.POSITIVE: "前向き",
            SentimentType.NEUTRAL: "通常",
            SentimentType.NEGATIVE: "悩み相談"
        }
        parts.append(f"雰囲気: {sentiment_text[sentiment]}")

        return " / ".join(parts) if parts else "一般的な会話"


class ConversationSummaryStore:
    """会話サマリーストア"""

    def __init__(self):
        self._summaries: Dict[str, List[ConversationSummary]] = {}  # user_id -> summaries

    def save_summary(self, summary: ConversationSummary) -> None:
        """サマリーを保存"""
        if summary.user_id not in self._summaries:
            self._summaries[summary.user_id] = []
        self._summaries[summary.user_id].append(summary)

    def get_user_summaries(
        self,
        user_id: str,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[ConversationSummary]:
        """ユーザーのサマリーを取得"""
        summaries = self._summaries.get(user_id, [])

        # 重要度フィルタ
        filtered = [s for s in summaries if s.importance_score >= min_importance]

        # 時間順でソート（新しい順）
        filtered.sort(key=lambda s: s.end_time, reverse=True)

        return filtered[:limit]

    def search_summaries(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[ConversationSummary]:
        """キーワードでサマリーを検索"""
        summaries = self._summaries.get(user_id, [])
        results = []

        query_lower = query.lower()

        for summary in summaries:
            score = 0

            # トピックマッチ
            for topic in summary.topics:
                if query_lower in topic.lower():
                    score += 3

            # キーワードマッチ
            for keyword in summary.keywords:
                if query_lower in keyword.lower():
                    score += 2

            # サマリーテキストマッチ
            if query_lower in summary.short_summary.lower():
                score += 1

            if score > 0:
                results.append((summary, score))

        # スコア順でソート
        results.sort(key=lambda x: x[1], reverse=True)

        return [r[0] for r in results[:limit]]

    def get_all_summaries_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """全サマリーを辞書形式で取得"""
        return {
            user_id: [s.to_dict() for s in summaries]
            for user_id, summaries in self._summaries.items()
        }

    def load_from_dict(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """辞書からサマリーを読み込み"""
        for user_id, summaries_data in data.items():
            self._summaries[user_id] = [
                ConversationSummary.from_dict(s) for s in summaries_data
            ]
