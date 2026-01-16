"""
会話モデル
エピソード（長期記憶）、メッセージ、会話コンテキストを定義
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .emotion import EmotionType


class EpisodeType(Enum):
    """エピソードタイプ"""
    GENERAL = "general"             # 一般的な会話
    DISCLOSURE = "disclosure"       # 個人情報の開示
    CRISIS = "crisis"               # 危機的状況
    MILESTONE = "milestone"         # 関係性のマイルストーン
    INSIGHT = "insight"             # 気づき・洞察


class ConversationPhase(Enum):
    """会話フェーズ"""
    GREETING = "greeting"    # 挨拶
    MAIN = "main"            # メイン会話
    CLOSING = "closing"      # 終了


@dataclass
class Message:
    """個別メッセージ"""
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    emotion: EmotionType | None = None
    emotion_intensity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "emotion": self.emotion.value if self.emotion else None,
            "emotion_intensity": self.emotion_intensity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        return cls(
            id=data["id"],
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            emotion=EmotionType(data["emotion"]) if data.get("emotion") else None,
            emotion_intensity=data.get("emotion_intensity", 0.0),
        )


@dataclass
class Episode:
    """
    エピソード記憶（長期記憶）
    重要な会話やマイルストーンを保存
    """
    id: str
    user_id: str
    created_at: datetime

    # コンテンツ
    summary: str                              # 会話の要約
    user_shared: list[str] = field(default_factory=list)  # ユーザーが共有した情報
    emotional_context: str = ""               # 感情的文脈
    topics: list[str] = field(default_factory=list)

    # メタデータ
    importance_score: float = 0.5             # 重要度 (0.0-1.0)
    emotional_intensity: float = 0.5          # 感情の強さ (0.0-1.0)
    episode_type: EpisodeType = EpisodeType.GENERAL
    emotion: EmotionType = EmotionType.NEUTRAL

    # 検索用
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "summary": self.summary,
            "user_shared": self.user_shared,
            "emotional_context": self.emotional_context,
            "topics": self.topics,
            "importance_score": self.importance_score,
            "emotional_intensity": self.emotional_intensity,
            "episode_type": self.episode_type.value,
            "emotion": self.emotion.value,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            summary=data.get("summary", ""),
            user_shared=data.get("user_shared", []),
            emotional_context=data.get("emotional_context", ""),
            topics=data.get("topics", []),
            importance_score=data.get("importance_score", 0.5),
            emotional_intensity=data.get("emotional_intensity", 0.5),
            episode_type=EpisodeType(data.get("episode_type", "general")),
            emotion=EmotionType(data.get("emotion", "neutral")),
            keywords=data.get("keywords", []),
        )


@dataclass
class ConversationContext:
    """
    会話コンテキスト（短期記憶）
    現在進行中のセッション状態を管理
    """
    user_id: str
    session_id: str

    # 現在の状態
    current_topic: str | None = None
    topic_depth: int = 0  # 同じトピックでの会話回数
    phase: ConversationPhase = ConversationPhase.GREETING

    # 感情状態
    current_emotion: EmotionType = EmotionType.NEUTRAL
    emotion_intensity: float = 0.0
    emotion_stability: float = 1.0

    # 履歴（直近N件）
    recent_messages: list[Message] = field(default_factory=list)

    # 継続性
    unresolved_questions: list[str] = field(default_factory=list)
    pending_follow_ups: list[str] = field(default_factory=list)

    # タイムスタンプ
    started_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime = field(default_factory=datetime.now)

    def add_message(self, message: Message) -> None:
        """メッセージを追加"""
        self.recent_messages.append(message)
        self.last_message_at = datetime.now()
        # 最新20件を保持
        if len(self.recent_messages) > 20:
            self.recent_messages = self.recent_messages[-20:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "current_topic": self.current_topic,
            "topic_depth": self.topic_depth,
            "phase": self.phase.value,
            "current_emotion": self.current_emotion.value,
            "emotion_intensity": self.emotion_intensity,
            "emotion_stability": self.emotion_stability,
            "recent_messages": [m.to_dict() for m in self.recent_messages],
            "unresolved_questions": self.unresolved_questions,
            "pending_follow_ups": self.pending_follow_ups,
            "started_at": self.started_at.isoformat(),
            "last_message_at": self.last_message_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationContext":
        return cls(
            user_id=data["user_id"],
            session_id=data["session_id"],
            current_topic=data.get("current_topic"),
            topic_depth=data.get("topic_depth", 0),
            phase=ConversationPhase(data.get("phase", "greeting")),
            current_emotion=EmotionType(data.get("current_emotion", "neutral")),
            emotion_intensity=data.get("emotion_intensity", 0.0),
            emotion_stability=data.get("emotion_stability", 1.0),
            recent_messages=[Message.from_dict(m) for m in data.get("recent_messages", [])],
            unresolved_questions=data.get("unresolved_questions", []),
            pending_follow_ups=data.get("pending_follow_ups", []),
            started_at=datetime.fromisoformat(data.get("started_at", datetime.now().isoformat())),
            last_message_at=datetime.fromisoformat(data.get("last_message_at", datetime.now().isoformat())),
        )
