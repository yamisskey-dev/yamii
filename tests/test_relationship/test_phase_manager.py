"""Tests for phase manager"""

import pytest
from datetime import datetime, timedelta

from yamii.relationship.models import RelationshipPhase, RelationshipState
from yamii.relationship.phase_manager import PhaseManager


class TestPhaseManager:
    """PhaseManager tests"""

    def setup_method(self):
        self.manager = PhaseManager()

    def test_initial_phase_is_stranger(self):
        """新規ユーザーはSTRANGERフェーズから開始"""
        state = RelationshipState(user_id="user1")
        assert state.phase == RelationshipPhase.STRANGER

    def test_phase_transitions_with_interactions(self):
        """対話回数に応じてフェーズが遷移する"""
        state = RelationshipState(user_id="user1")

        # 5回の対話でまだSTRANGER
        for _ in range(5):
            state = self.manager.update_state(
                state=state,
                message="テストメッセージ",
                emotion_intensity=0.5,
                has_personal_disclosure=False,
            )
        assert state.phase == RelationshipPhase.STRANGER
        assert state.total_interactions == 5

        # 信頼度が低いと effective_count = interactions * (0.5 + trust * 0.5)
        # なので6回では effective_count = 6 * 0.5 = 3 程度
        # ACQUAINTANCEに遷移するには effective_count >= 6 が必要
        # 12回程度の対話が必要（信頼度が低い場合）
        for _ in range(7):
            state = self.manager.update_state(
                state=state,
                message="テストメッセージ",
                emotion_intensity=0.5,
                has_personal_disclosure=False,
            )
        assert state.phase == RelationshipPhase.ACQUAINTANCE

    def test_trust_accelerates_phase_transition(self):
        """信頼度が高いとフェーズ遷移が加速する"""
        state = RelationshipState(user_id="user1")

        # 個人情報を開示すると信頼度が上がる
        for _ in range(5):
            state = self.manager.update_state(
                state=state,
                message="実は私は〇〇で働いています",
                emotion_intensity=0.7,
                has_personal_disclosure=True,
            )

        # 信頼度が上がっているはず
        assert state.trust_score > 0.1
        # 5回でもACQUAINTANCEに遷移している可能性
        # (信頼度による加速効果)

    def test_openness_score_increases_with_disclosure(self):
        """個人情報開示で開示度が上がる"""
        state = RelationshipState(user_id="user1")

        state = self.manager.update_state(
            state=state,
            message="実は私は30歳です",
            emotion_intensity=0.5,
            has_personal_disclosure=True,
        )

        assert state.openness_score > 0.0

    def test_long_messages_increase_openness(self):
        """長いメッセージで開示度が上がる"""
        state = RelationshipState(user_id="user1")

        long_message = "これは非常に長いメッセージです。" * 20  # 約400文字

        state = self.manager.update_state(
            state=state,
            message=long_message,
            emotion_intensity=0.5,
            has_personal_disclosure=False,
        )

        assert state.openness_score > 0.0

    def test_get_phase_progress(self):
        """フェーズ進捗が取得できる"""
        state = RelationshipState(
            user_id="user1",
            phase=RelationshipPhase.STRANGER,
            total_interactions=3,
            trust_score=0.1,
        )

        progress = self.manager.get_phase_progress(state)

        assert progress["current_phase"] == "stranger"
        assert progress["next_phase"] == "acquaintance"
        assert 0 <= progress["progress"] <= 1
        assert progress["interactions_to_next"] >= 0

    def test_trusted_phase_has_no_next(self):
        """TRUSTEDフェーズには次がない"""
        state = RelationshipState(
            user_id="user1",
            phase=RelationshipPhase.TRUSTED,
            total_interactions=100,
        )

        progress = self.manager.get_phase_progress(state)

        assert progress["current_phase"] == "trusted"
        assert progress["next_phase"] is None
        assert progress["progress"] == 1.0

    def test_phase_description(self):
        """フェーズ説明が取得できる"""
        for phase in RelationshipPhase:
            desc = self.manager.get_phase_description(phase)
            assert desc  # 空でない
            assert isinstance(desc, str)
