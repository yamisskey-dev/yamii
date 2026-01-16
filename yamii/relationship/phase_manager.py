"""
関係性フェーズマネージャー
対話を通じて関係性フェーズを管理・遷移
"""

from datetime import datetime

from .models import RelationshipPhase, RelationshipState


class PhaseManager:
    """
    関係性フェーズマネージャー

    ユーザーとの関係性フェーズを管理し、対話に応じて遷移させる。

    フェーズ:
    - STRANGER (0-5回): 初対面、丁寧な対応
    - ACQUAINTANCE (6-20回): 顔見知り、過去の話題を参照
    - FAMILIAR (21-50回): 親しい関係、エピソードを覚えている
    - TRUSTED (51回以上): 信頼関係、深い理解
    """

    # フェーズ遷移の閾値
    PHASE_THRESHOLDS = {
        RelationshipPhase.STRANGER: 0,
        RelationshipPhase.ACQUAINTANCE: 6,
        RelationshipPhase.FAMILIAR: 21,
        RelationshipPhase.TRUSTED: 51,
    }

    def __init__(self):
        pass

    def update_state(
        self,
        state: RelationshipState,
        message: str,
        emotion_intensity: float,
        has_personal_disclosure: bool,
    ) -> RelationshipState:
        """
        対話から関係性状態を更新

        Args:
            state: 現在の関係性状態
            message: ユーザーメッセージ
            emotion_intensity: 感情の強さ (0.0-1.0)
            has_personal_disclosure: 個人情報の開示があったか

        Returns:
            更新された関係性状態
        """
        # インタラクション記録
        state.total_interactions += 1
        state.last_interaction = datetime.now()

        # 信頼度を更新
        state.trust_score = self._update_trust_score(
            current=state.trust_score,
            message=message,
            emotion_intensity=emotion_intensity,
            has_personal_disclosure=has_personal_disclosure,
            last_interaction=state.last_interaction,
        )

        # 開示度を更新
        state.openness_score = self._update_openness_score(
            current=state.openness_score,
            message=message,
            has_personal_disclosure=has_personal_disclosure,
        )

        # 親密度を更新
        state.rapport_score = self._update_rapport_score(
            current=state.rapport_score,
            trust=state.trust_score,
            openness=state.openness_score,
            interactions=state.total_interactions,
        )

        # フェーズを更新
        state.phase = self._calculate_phase(state)

        return state

    def _update_trust_score(
        self,
        current: float,
        message: str,
        emotion_intensity: float,
        has_personal_disclosure: bool,
        last_interaction: datetime,
    ) -> float:
        """信頼度スコアを更新"""
        score = current

        # ポジティブ要因
        if has_personal_disclosure:
            score += 0.02  # 個人的な話をしてくれた

        if emotion_intensity > 0.7:
            score += 0.01  # 深い感情を共有

        if len(message) > 200:
            score += 0.005  # 長い会話を続けてくれた

        # 継続的な対話で少しずつ信頼が積み重なる
        score += 0.005

        # 時間経過による緩やかな減衰
        days_since_last = (datetime.now() - last_interaction).days
        if days_since_last > 7:
            decay = 0.01 * (days_since_last // 7)
            score -= min(decay, 0.1)  # 最大0.1の減衰

        return max(0.0, min(1.0, score))

    def _update_openness_score(
        self,
        current: float,
        message: str,
        has_personal_disclosure: bool,
    ) -> float:
        """開示度スコアを更新"""
        score = current

        # 個人情報の開示
        if has_personal_disclosure:
            score += 0.05

        # メッセージの長さ（長いほど開示が多い傾向）
        if len(message) > 300:
            score += 0.02
        elif len(message) > 150:
            score += 0.01

        # 感情的なキーワード
        emotional_keywords = [
            "嬉しい", "悲しい", "辛い", "不安", "怒り",
            "寂しい", "嫌", "好き", "怖い", "心配",
        ]
        if any(kw in message for kw in emotional_keywords):
            score += 0.01

        # 緩やかな減衰（開示がない場合）
        if not has_personal_disclosure and len(message) < 50:
            score -= 0.005

        return max(0.0, min(1.0, score))

    def _update_rapport_score(
        self,
        current: float,
        trust: float,
        openness: float,
        interactions: int,
    ) -> float:
        """親密度スコアを更新"""
        # 親密度は信頼度と開示度の加重平均 + 対話回数ボーナス
        base_score = (trust * 0.4 + openness * 0.4)

        # 対話回数ボーナス（最大0.2）
        interaction_bonus = min(interactions / 100, 0.2)

        score = base_score + interaction_bonus

        # 急激な変化を避けるため、現在値との平均を取る
        smoothed = (current * 0.7 + score * 0.3)

        return max(0.0, min(1.0, smoothed))

    def _calculate_phase(self, state: RelationshipState) -> RelationshipPhase:
        """関係性フェーズを計算"""
        # 基本は対話回数ベース、信頼度で加速/減速
        effective_count = state.total_interactions * (0.5 + state.trust_score * 0.5)

        if effective_count >= self.PHASE_THRESHOLDS[RelationshipPhase.TRUSTED]:
            return RelationshipPhase.TRUSTED
        elif effective_count >= self.PHASE_THRESHOLDS[RelationshipPhase.FAMILIAR]:
            return RelationshipPhase.FAMILIAR
        elif effective_count >= self.PHASE_THRESHOLDS[RelationshipPhase.ACQUAINTANCE]:
            return RelationshipPhase.ACQUAINTANCE
        else:
            return RelationshipPhase.STRANGER

    def get_phase_description(self, phase: RelationshipPhase) -> str:
        """フェーズの説明を取得"""
        descriptions = {
            RelationshipPhase.STRANGER: (
                "初対面の段階です。丁寧で探索的な対応を心がけ、"
                "相手のことを少しずつ知っていきましょう。"
            ),
            RelationshipPhase.ACQUAINTANCE: (
                "顔見知りの段階です。過去の会話を参照しながら、"
                "少しカジュアルな対応ができるようになります。"
            ),
            RelationshipPhase.FAMILIAR: (
                "親しい関係の段階です。相手のことをよく知っており、"
                "重要なエピソードを覚えています。"
            ),
            RelationshipPhase.TRUSTED: (
                "信頼関係が築けた段階です。深い理解に基づいた"
                "長期的な視点でのサポートが可能です。"
            ),
        }
        return descriptions.get(phase, "")

    def get_phase_progress(self, state: RelationshipState) -> dict:
        """フェーズ進捗を取得"""
        current_phase = state.phase
        effective_count = state.total_interactions * (0.5 + state.trust_score * 0.5)

        # 次のフェーズまでの進捗を計算
        phase_order = [
            RelationshipPhase.STRANGER,
            RelationshipPhase.ACQUAINTANCE,
            RelationshipPhase.FAMILIAR,
            RelationshipPhase.TRUSTED,
        ]

        current_idx = phase_order.index(current_phase)
        if current_idx >= len(phase_order) - 1:
            # 最高フェーズに到達済み
            return {
                "current_phase": current_phase.value,
                "next_phase": None,
                "progress": 1.0,
                "interactions_to_next": 0,
            }

        next_phase = phase_order[current_idx + 1]
        current_threshold = self.PHASE_THRESHOLDS[current_phase]
        next_threshold = self.PHASE_THRESHOLDS[next_phase]

        range_size = next_threshold - current_threshold
        progress_in_range = effective_count - current_threshold
        progress = min(1.0, max(0.0, progress_in_range / range_size))

        # 次のフェーズまでの対話回数（概算）
        remaining = next_threshold - effective_count
        interactions_to_next = int(remaining / (0.5 + state.trust_score * 0.5))

        return {
            "current_phase": current_phase.value,
            "next_phase": next_phase.value,
            "progress": progress,
            "interactions_to_next": max(0, interactions_to_next),
        }
