"""
コンテキスト認識システム
感情状態・トピック遷移・未解決質問を追跡し、文脈を意識した応答を生成
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class EmotionalState(Enum):
    """感情状態"""
    EXCITED = "excited"      # 興奮
    POSITIVE = "positive"    # ポジティブ
    NEUTRAL = "neutral"      # ニュートラル
    NEGATIVE = "negative"    # ネガティブ
    CALM = "calm"            # 落ち着き


class ConversationPhase(Enum):
    """会話フェーズ"""
    GREETING = "greeting"    # 挨拶
    MAIN = "main"            # メイン会話
    CLOSING = "closing"      # 終了


class TopicTransitionReason(Enum):
    """トピック遷移理由"""
    USER_INITIATED = "user_initiated"    # ユーザー主導
    NATURAL_FLOW = "natural_flow"        # 自然な流れ
    BOT_SUGGESTED = "bot_suggested"      # ボット提案


class ThreadStatus(Enum):
    """スレッド状態"""
    ACTIVE = "active"        # アクティブ
    PAUSED = "paused"        # 一時停止
    COMPLETED = "completed"  # 完了


@dataclass
class EmotionalStateInfo:
    """感情状態情報"""
    state: EmotionalState
    intensity: float  # 0.0 - 1.0
    stability: float  # 0.0 - 1.0（感情の安定性）
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "intensity": self.intensity,
            "stability": self.stability,
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmotionalStateInfo":
        return cls(
            state=EmotionalState(data["state"]),
            intensity=data["intensity"],
            stability=data["stability"],
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        )


@dataclass
class TopicTransition:
    """トピック遷移記録"""
    from_topic: str
    to_topic: str
    reason: TopicTransitionReason
    smoothness: float  # 0.5 - 1.0（遷移のスムーズさ）
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_topic": self.from_topic,
            "to_topic": self.to_topic,
            "reason": self.reason.value,
            "smoothness": self.smoothness,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TopicTransition":
        return cls(
            from_topic=data["from_topic"],
            to_topic=data["to_topic"],
            reason=TopicTransitionReason(data["reason"]),
            smoothness=data["smoothness"],
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
        )


@dataclass
class ConversationThread:
    """会話スレッド"""
    id: str
    topic: str
    start_time: datetime
    messages: List[Dict[str, Any]] = field(default_factory=list)
    status: ThreadStatus = ThreadStatus.ACTIVE
    depth: int = 0  # 会話の深さ

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "start_time": self.start_time.isoformat(),
            "messages": self.messages,
            "status": self.status.value,
            "depth": self.depth
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationThread":
        return cls(
            id=data["id"],
            topic=data["topic"],
            start_time=datetime.fromisoformat(data["start_time"]),
            messages=data.get("messages", []),
            status=ThreadStatus(data.get("status", "active")),
            depth=data.get("depth", 0)
        )

    def add_message(self, role: str, content: str) -> None:
        """メッセージを追加"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.depth += 1


@dataclass
class ContinuityInfo:
    """会話継続性情報"""
    topic_transitions: List[TopicTransition] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)
    pending_follow_ups: List[str] = field(default_factory=list)
    threads: Dict[str, ConversationThread] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_transitions": [t.to_dict() for t in self.topic_transitions],
            "unresolved_questions": self.unresolved_questions,
            "pending_follow_ups": self.pending_follow_ups,
            "threads": {k: v.to_dict() for k, v in self.threads.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContinuityInfo":
        return cls(
            topic_transitions=[TopicTransition.from_dict(t) for t in data.get("topic_transitions", [])],
            unresolved_questions=data.get("unresolved_questions", []),
            pending_follow_ups=data.get("pending_follow_ups", []),
            threads={k: ConversationThread.from_dict(v) for k, v in data.get("threads", {}).items()}
        )


@dataclass
class ConversationContext:
    """会話コンテキスト"""
    user_id: str
    current_topic: str = ""
    emotional_state: EmotionalStateInfo = field(
        default_factory=lambda: EmotionalStateInfo(EmotionalState.NEUTRAL, 0.5, 0.8)
    )
    phase: ConversationPhase = ConversationPhase.GREETING
    continuity: ContinuityInfo = field(default_factory=ContinuityInfo)
    last_interaction: datetime = field(default_factory=datetime.now)

    # 追加のコンテキスト情報
    topic_depth: int = 0  # 現在のトピックの深さ
    active_threads: int = 0  # アクティブなスレッド数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "current_topic": self.current_topic,
            "emotional_state": self.emotional_state.to_dict(),
            "phase": self.phase.value,
            "continuity": self.continuity.to_dict(),
            "last_interaction": self.last_interaction.isoformat(),
            "topic_depth": self.topic_depth,
            "active_threads": self.active_threads
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationContext":
        return cls(
            user_id=data["user_id"],
            current_topic=data.get("current_topic", ""),
            emotional_state=EmotionalStateInfo.from_dict(data.get("emotional_state", {})),
            phase=ConversationPhase(data.get("phase", "greeting")),
            continuity=ContinuityInfo.from_dict(data.get("continuity", {})),
            last_interaction=datetime.fromisoformat(data.get("last_interaction", datetime.now().isoformat())),
            topic_depth=data.get("topic_depth", 0),
            active_threads=data.get("active_threads", 0)
        )


@dataclass
class ContextAwareResponse:
    """コンテキスト認識応答"""
    response: str
    emotional_tone: str
    topic_depth: int
    suggested_follow_ups: List[str]
    context_summary: str


class ContextAwareResponseGenerator:
    """コンテキスト認識応答生成器"""

    def __init__(self):
        self._user_contexts: Dict[str, ConversationContext] = {}

        # 感情キーワード
        self._emotion_keywords = {
            EmotionalState.EXCITED: ["すごい", "最高", "やった", "嬉しい", "楽しみ"],
            EmotionalState.POSITIVE: ["良い", "好き", "ありがとう", "嬉しい", "楽しい"],
            EmotionalState.NEUTRAL: [],
            EmotionalState.NEGATIVE: ["悲しい", "辛い", "困った", "不安", "心配"],
            EmotionalState.CALM: ["そうですね", "なるほど", "分かりました", "了解"]
        }

        # トピックキーワード（会話サマリーと共通）
        self._topic_keywords = {
            "仕事": ["仕事", "職場", "会社", "上司", "同僚", "転職", "キャリア"],
            "恋愛": ["恋愛", "彼氏", "彼女", "パートナー", "デート", "告白"],
            "家族": ["家族", "親", "父", "母", "兄弟", "子供", "育児"],
            "友人関係": ["友達", "友人", "人間関係", "仲間"],
            "健康": ["健康", "病気", "体調", "病院", "治療", "メンタル"],
            "将来": ["将来", "夢", "目標", "進路", "人生"],
        }

    def get_or_create_context(self, user_id: str) -> ConversationContext:
        """ユーザーのコンテキストを取得または作成"""
        if user_id not in self._user_contexts:
            self._user_contexts[user_id] = ConversationContext(user_id=user_id)
        return self._user_contexts[user_id]

    def analyze_message(self, message: str) -> Dict[str, Any]:
        """
        メッセージを分析

        Returns:
            {
                "emotional_state": EmotionalState,
                "detected_topics": List[str],
                "has_question": bool,
                "question_text": Optional[str]
            }
        """
        # 感情状態の検出
        emotional_state = self._detect_emotion(message)

        # トピック検出
        detected_topics = self._detect_topics(message)

        # 質問検出
        has_question = "?" in message or "？" in message
        question_text = message if has_question else None

        return {
            "emotional_state": emotional_state,
            "detected_topics": detected_topics,
            "has_question": has_question,
            "question_text": question_text
        }

    def _detect_emotion(self, message: str) -> EmotionalState:
        """感情を検出"""
        message_lower = message.lower()

        # キーワードマッチングでスコア計算
        scores = {state: 0 for state in EmotionalState}

        for state, keywords in self._emotion_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    scores[state] += 1

        # 最高スコアの感情を返す
        max_state = max(scores, key=scores.get)
        if scores[max_state] > 0:
            return max_state
        return EmotionalState.NEUTRAL

    def _detect_topics(self, message: str) -> List[str]:
        """トピックを検出"""
        detected = []
        message_lower = message.lower()

        for topic, keywords in self._topic_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    if topic not in detected:
                        detected.append(topic)
                    break

        return detected

    def update_context(
        self,
        user_id: str,
        message: str,
        analysis: Dict[str, Any]
    ) -> ConversationContext:
        """コンテキストを更新"""
        context = self.get_or_create_context(user_id)

        # 感情状態の更新
        new_emotion = analysis["emotional_state"]
        old_emotion = context.emotional_state.state

        # 感情の安定性を計算
        if new_emotion == old_emotion:
            stability = min(context.emotional_state.stability + 0.1, 1.0)
        else:
            stability = max(context.emotional_state.stability - 0.2, 0.3)

        context.emotional_state = EmotionalStateInfo(
            state=new_emotion,
            intensity=0.7 if new_emotion != EmotionalState.NEUTRAL else 0.5,
            stability=stability
        )

        # トピック遷移の記録
        detected_topics = analysis["detected_topics"]
        if detected_topics and detected_topics[0] != context.current_topic:
            if context.current_topic:
                transition = TopicTransition(
                    from_topic=context.current_topic,
                    to_topic=detected_topics[0],
                    reason=TopicTransitionReason.USER_INITIATED,
                    smoothness=0.8
                )
                context.continuity.topic_transitions.append(transition)

            context.current_topic = detected_topics[0]
            context.topic_depth = 1
        else:
            context.topic_depth += 1

        # 質問の追跡
        if analysis["has_question"] and analysis["question_text"]:
            context.continuity.unresolved_questions.append(analysis["question_text"][:100])

        # 会話フェーズの更新
        context.phase = self._determine_phase(message, context)

        # 最終インタラクション時刻の更新
        context.last_interaction = datetime.now()

        return context

    def _determine_phase(self, message: str, context: ConversationContext) -> ConversationPhase:
        """会話フェーズを判定"""
        greeting_words = ["こんにちは", "おはよう", "こんばんは", "初めまして", "よろしく"]
        closing_words = ["ありがとう", "さようなら", "またね", "じゃあね", "バイバイ"]

        message_lower = message.lower()

        for word in greeting_words:
            if word in message_lower:
                return ConversationPhase.GREETING

        for word in closing_words:
            if word in message_lower:
                return ConversationPhase.CLOSING

        return ConversationPhase.MAIN

    def build_context_prompt(self, context: ConversationContext) -> str:
        """コンテキストに基づくプロンプトを構築"""
        parts = []

        # 感情的連続性
        emotion_text = {
            EmotionalState.EXCITED: "興奮気味",
            EmotionalState.POSITIVE: "前向き",
            EmotionalState.NEUTRAL: "通常",
            EmotionalState.NEGATIVE: "悩んでいる様子",
            EmotionalState.CALM: "落ち着いている"
        }
        parts.append(f"ユーザーの状態: {emotion_text[context.emotional_state.state]}")
        parts.append(f"感情の安定性: {context.emotional_state.stability:.1f}")

        # トピック情報
        if context.current_topic:
            parts.append(f"現在の話題: {context.current_topic}")
            parts.append(f"話題の深さ: {context.topic_depth}回目のやり取り")

        # トピック遷移履歴
        if context.continuity.topic_transitions:
            recent_transitions = context.continuity.topic_transitions[-3:]
            transition_text = " → ".join([t.to_topic for t in recent_transitions])
            parts.append(f"最近の話題遷移: {transition_text}")

        # 未解決の質問
        if context.continuity.unresolved_questions:
            parts.append(f"未解決の質問: {len(context.continuity.unresolved_questions)}件")

        # 会話フェーズ
        phase_text = {
            ConversationPhase.GREETING: "挨拶段階",
            ConversationPhase.MAIN: "本題",
            ConversationPhase.CLOSING: "終了段階"
        }
        parts.append(f"会話フェーズ: {phase_text[context.phase]}")

        return "\n".join(parts)

    def generate_response(
        self,
        user_id: str,
        message: str,
        base_response: str
    ) -> ContextAwareResponse:
        """
        コンテキストを考慮した応答を生成

        Args:
            user_id: ユーザーID
            message: ユーザーメッセージ
            base_response: 基本応答（LLMからの応答）

        Returns:
            ContextAwareResponse
        """
        # メッセージ分析
        analysis = self.analyze_message(message)

        # コンテキスト更新
        context = self.update_context(user_id, message, analysis)

        # フォローアップ提案の生成
        follow_ups = self._generate_follow_ups(context, analysis)

        # 質問が解決されたかチェック
        self._check_resolved_questions(context, base_response)

        # 感情トーンの決定
        emotional_tone = self._determine_response_tone(context)

        # コンテキストサマリーの生成
        context_summary = self.build_context_prompt(context)

        return ContextAwareResponse(
            response=base_response,
            emotional_tone=emotional_tone,
            topic_depth=context.topic_depth,
            suggested_follow_ups=follow_ups,
            context_summary=context_summary
        )

    def _generate_follow_ups(
        self,
        context: ConversationContext,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """フォローアップ提案を生成"""
        follow_ups = []

        # トピックに基づくフォローアップ
        topic_follow_ups = {
            "仕事": ["具体的にどのような状況ですか？", "上司や同僚との関係はいかがですか？"],
            "恋愛": ["お相手との関係性を教えてください", "どのくらいお付き合いされていますか？"],
            "家族": ["ご家族との関係について詳しく教えてください", "この状況はいつ頃からですか？"],
            "健康": ["体調の変化はいつ頃からですか？", "専門家に相談されましたか？"],
        }

        if context.current_topic in topic_follow_ups:
            follow_ups.extend(topic_follow_ups[context.current_topic][:2])

        # 感情状態に基づくフォローアップ
        if context.emotional_state.state == EmotionalState.NEGATIVE:
            follow_ups.append("無理しないでくださいね")

        return follow_ups[:3]

    def _check_resolved_questions(self, context: ConversationContext, response: str) -> None:
        """解決された質問をチェック"""
        resolved = []
        for question in context.continuity.unresolved_questions:
            # 簡易的な解決チェック（応答に質問のキーワードが含まれているか）
            keywords = question[:20].split()
            for keyword in keywords:
                if keyword in response:
                    resolved.append(question)
                    break

        for q in resolved:
            if q in context.continuity.unresolved_questions:
                context.continuity.unresolved_questions.remove(q)

    def _determine_response_tone(self, context: ConversationContext) -> str:
        """応答のトーンを決定"""
        tone_map = {
            EmotionalState.EXCITED: "enthusiastic",
            EmotionalState.POSITIVE: "warm",
            EmotionalState.NEUTRAL: "balanced",
            EmotionalState.NEGATIVE: "empathetic",
            EmotionalState.CALM: "composed"
        }
        return tone_map[context.emotional_state.state]

    def mark_question_resolved(self, user_id: str, question: str) -> None:
        """質問を解決済みとしてマーク"""
        context = self.get_or_create_context(user_id)
        if question in context.continuity.unresolved_questions:
            context.continuity.unresolved_questions.remove(question)

    def get_context_summary(self, user_id: str) -> Optional[str]:
        """ユーザーのコンテキストサマリーを取得"""
        if user_id not in self._user_contexts:
            return None
        return self.build_context_prompt(self._user_contexts[user_id])

    def clear_user_context(self, user_id: str) -> None:
        """ユーザーのコンテキストをクリア"""
        if user_id in self._user_contexts:
            del self._user_contexts[user_id]

    def get_all_contexts_dict(self) -> Dict[str, Dict[str, Any]]:
        """全コンテキストを辞書形式で取得"""
        return {
            user_id: context.to_dict()
            for user_id, context in self._user_contexts.items()
        }

    def load_from_dict(self, data: Dict[str, Dict[str, Any]]) -> None:
        """辞書からコンテキストを読み込み"""
        for user_id, context_data in data.items():
            self._user_contexts[user_id] = ConversationContext.from_dict(context_data)
