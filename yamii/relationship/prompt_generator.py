"""
関係性考慮プロンプト生成器
関係性フェーズと適応プロファイルに基づいてシステムプロンプトを生成
"""

from typing import List

from .models import (
    RelationshipPhase,
    RelationshipState,
    AdaptiveProfile,
    Episode,
    ToneLevel,
    DepthLevel,
)


class RelationshipPromptGenerator:
    """
    関係性考慮プロンプト生成器

    関係性フェーズ、適応プロファイル、エピソード記憶を
    統合してシステムプロンプトを生成する。
    """

    # ベースとなる指示（シンプル・中性的）
    BASE_INSTRUCTION = """あなたは相談者の話に寄り添う相談相手です。
まず気持ちを受け止め、必要に応じて一緒に考えます。
危機的状況では専門機関への相談を案内します。"""

    # フェーズ別の指示（シンプル）
    PHASE_INSTRUCTIONS = {
        RelationshipPhase.STRANGER: """
初対面。丁寧な対応を心がける。""",

        RelationshipPhase.ACQUAINTANCE: """
顔見知り。過去の会話を参照してよい。""",

        RelationshipPhase.FAMILIAR: """
親しい関係。自然な会話ができる。""",

        RelationshipPhase.TRUSTED: """
信頼関係。率直なやり取りができる。""",
    }

    # トーン別の指示
    TONE_INSTRUCTIONS = {
        ToneLevel.WARM: "温かみのある、励ましを含んだ応答を心がける",
        ToneLevel.PROFESSIONAL: "落ち着いた、専門的な応答を心がける",
        ToneLevel.CASUAL: "親しみやすく、カジュアルな応答を心がける",
        ToneLevel.BALANCED: "バランスの取れた応答を心がける",
    }

    # デプス別の指示
    DEPTH_INSTRUCTIONS = {
        DepthLevel.SHALLOW: "簡潔な応答を心がける（短めに）",
        DepthLevel.MEDIUM: "適度な詳しさで応答する",
        DepthLevel.DEEP: "詳細な説明や具体例を含める",
    }

    def __init__(self):
        pass

    def generate(
        self,
        state: RelationshipState,
        profile: AdaptiveProfile,
        recent_episodes: List[Episode],
    ) -> str:
        """
        システムプロンプトを生成

        Args:
            state: 関係性状態
            profile: 適応プロファイル
            recent_episodes: 最近のエピソード

        Returns:
            システムプロンプト
        """
        parts = [self.BASE_INSTRUCTION]

        # フェーズ別の指示を追加
        phase_instruction = self.PHASE_INSTRUCTIONS.get(state.phase, "")
        if phase_instruction:
            parts.append(phase_instruction)

        # 適応情報を追加（確信度が一定以上の場合）
        if profile.confidence_score > 0.2:
            adaptation_section = self._generate_adaptation_section(profile)
            if adaptation_section:
                parts.append(adaptation_section)

        # 既知の情報を追加
        known_info_section = self._generate_known_info_section(state)
        if known_info_section:
            parts.append(known_info_section)

        # エピソード記憶を追加（親しい関係以上）
        if state.phase in [RelationshipPhase.FAMILIAR, RelationshipPhase.TRUSTED]:
            episode_section = self._generate_episode_section(recent_episodes)
            if episode_section:
                parts.append(episode_section)

        return "\n".join(parts)

    def _generate_adaptation_section(self, profile: AdaptiveProfile) -> str:
        """適応情報セクションを生成"""
        lines = ["\n**このユーザーへの対応ガイド:**"]

        # トーンの調整
        tone_instruction = self.TONE_INSTRUCTIONS.get(profile.preferred_tone)
        if tone_instruction:
            lines.append(f"- {tone_instruction}")

        # デプスの調整
        depth_instruction = self.DEPTH_INSTRUCTIONS.get(profile.preferred_depth)
        if depth_instruction:
            lines.append(f"- {depth_instruction}")

        # 共感重視
        if profile.likes_empathy > 0.7:
            lines.append("- 共感を特に重視し、相手の気持ちに寄り添う")

        # 質問頻度
        if profile.likes_questions > 0.6:
            lines.append("- 質問を通じて相手の考えを引き出す")
        elif profile.likes_questions < 0.3:
            lines.append("- 質問は控えめにする")

        # アドバイス傾向
        if profile.likes_advice > 0.6:
            lines.append("- 具体的なアドバイスや提案を積極的に行う")
        elif profile.likes_advice < 0.3:
            lines.append("- アドバイスより傾聴を重視する")

        # 関心のあるトピック
        if profile.frequent_topics:
            top_topics = sorted(
                profile.frequent_topics.values(),
                key=lambda t: t.affinity_score,
                reverse=True,
            )[:3]
            if top_topics:
                topics_text = ", ".join(t.topic for t in top_topics)
                lines.append(f"- 関心のあるテーマ: {topics_text}")

        if len(lines) > 1:
            return "\n".join(lines)
        return ""

    def _generate_known_info_section(self, state: RelationshipState) -> str:
        """既知情報セクションを生成"""
        lines = []

        # 既知の事実（最大5件）
        if state.known_facts:
            facts = state.known_facts[-5:]
            lines.append("\n**相談者について知っていること:**")
            for fact in facts:
                lines.append(f"- {fact}")

        # 最近話したトピック（最大3件）
        if state.known_topics:
            recent_topics = state.known_topics[-3:]
            if recent_topics:
                lines.append(f"- 最近話したトピック: {', '.join(recent_topics)}")

        return "\n".join(lines) if lines else ""

    def _generate_episode_section(self, episodes: List[Episode]) -> str:
        """エピソード記憶セクションを生成"""
        if not episodes:
            return ""

        # 重要なエピソードを選択
        important_episodes = [e for e in episodes if e.importance_score >= 0.5]
        if not important_episodes:
            return ""

        lines = ["\n**覚えている重要なエピソード:**"]

        for episode in important_episodes[:3]:
            # エピソードの要約を生成
            summary_parts = []

            if episode.topics:
                summary_parts.append(f"話題: {', '.join(episode.topics[:2])}")

            if episode.user_shared:
                shared_text = episode.user_shared[0][:50]
                summary_parts.append(f"共有された情報: {shared_text}")

            if episode.emotional_context:
                summary_parts.append(f"感情: {episode.emotional_context}")

            if summary_parts:
                date_str = episode.created_at.strftime("%m/%d")
                lines.append(f"- [{date_str}] {' / '.join(summary_parts)}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def generate_crisis_addendum(self) -> str:
        """危機対応の追加指示を生成"""
        return """
⚠️ **重要: 危機的状況の可能性があります**
- 安全の確保を最優先とする
- 専門機関への相談を強く推奨する
  - いのちの電話: 0570-783-556
  - よりそいホットライン: 0120-279-338
- 「あなたは一人ではない」というメッセージを伝える
- 具体的な行動計画の確認（今日一日を安全に過ごす方法など）"""

    def generate_context_addendum(
        self,
        emotion: str,
        emotion_intensity: float,
        topics: List[str],
        user_name: str = "",
    ) -> str:
        """現在のコンテキスト情報を生成"""
        from datetime import datetime

        now = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        parts = [
            "---",
            f"現在日時: {now}",
        ]

        if user_name:
            parts.append(f"相談者: {user_name}")

        parts.append(f"感情: {emotion}（強度: {int(emotion_intensity * 10)}/10）")

        if topics:
            parts.append(f"トピック: {', '.join(topics)}")

        return "\n".join(parts)
