"""Tests for relationship models"""

import pytest
from datetime import datetime

from yamii.relationship.models import (
    RelationshipPhase,
    EpisodeType,
    ToneLevel,
    DepthLevel,
    RelationshipState,
    Episode,
    AdaptiveProfile,
    TopicAffinity,
    PhaseTransition,
    UserRelationshipData,
)


class TestRelationshipState:
    """RelationshipState tests"""

    def test_default_values(self):
        """新規ユーザーはSTRANGERフェーズから開始"""
        state = RelationshipState(user_id="user1")
        assert state.phase == RelationshipPhase.STRANGER
        assert state.total_interactions == 0
        assert state.trust_score == 0.0
        assert state.openness_score == 0.0
        assert state.rapport_score == 0.0
        assert state.known_facts == []
        assert state.known_topics == []

    def test_serialization(self):
        """シリアライズ/デシリアライズが正常に動作する"""
        state = RelationshipState(
            user_id="user1",
            phase=RelationshipPhase.ACQUAINTANCE,
            total_interactions=10,
            trust_score=0.5,
            known_facts=["東京在住"],
            known_topics=["仕事", "健康"],
        )

        data = state.to_dict()
        restored = RelationshipState.from_dict(data)

        assert restored.user_id == state.user_id
        assert restored.phase == state.phase
        assert restored.total_interactions == state.total_interactions
        assert restored.trust_score == state.trust_score
        assert restored.known_facts == state.known_facts
        assert restored.known_topics == state.known_topics


class TestEpisode:
    """Episode tests"""

    def test_default_values(self):
        """エピソードの初期値が正しい"""
        episode = Episode(
            id="ep_123",
            user_id="user1",
            created_at=datetime.now(),
            summary="仕事の悩みについて相談",
        )
        assert episode.episode_type == EpisodeType.GENERAL
        assert episode.importance_score == 0.5
        assert episode.topics == []
        assert episode.user_shared == []

    def test_serialization(self):
        """シリアライズ/デシリアライズが正常に動作する"""
        episode = Episode(
            id="ep_456",
            user_id="user1",
            created_at=datetime.now(),
            summary="重要な相談",
            topics=["仕事", "ストレス"],
            importance_score=0.8,
            episode_type=EpisodeType.DISCLOSURE,
            user_shared=["実は転職を考えている"],
        )

        data = episode.to_dict()
        restored = Episode.from_dict(data)

        assert restored.id == episode.id
        assert restored.summary == episode.summary
        assert restored.topics == episode.topics
        assert restored.importance_score == episode.importance_score
        assert restored.episode_type == episode.episode_type
        assert restored.user_shared == episode.user_shared


class TestAdaptiveProfile:
    """AdaptiveProfile tests"""

    def test_default_values(self):
        """プロファイルの初期値が正しい"""
        profile = AdaptiveProfile(user_id="user1")
        assert profile.preferred_tone == ToneLevel.BALANCED
        assert profile.preferred_depth == DepthLevel.MEDIUM
        assert profile.likes_empathy == 0.7
        assert profile.confidence_score == 0.0

    def test_serialization(self):
        """シリアライズ/デシリアライズが正常に動作する"""
        profile = AdaptiveProfile(
            user_id="user1",
            preferred_tone=ToneLevel.WARM,
            preferred_depth=DepthLevel.DEEP,
            likes_questions=0.8,
            likes_advice=0.3,
            confidence_score=0.5,
        )
        profile.frequent_topics["仕事"] = TopicAffinity(
            topic="仕事",
            affinity_score=0.8,
            mention_count=5,
        )

        data = profile.to_dict()
        restored = AdaptiveProfile.from_dict(data)

        assert restored.user_id == profile.user_id
        assert restored.preferred_tone == profile.preferred_tone
        assert restored.preferred_depth == profile.preferred_depth
        assert restored.likes_questions == profile.likes_questions
        assert "仕事" in restored.frequent_topics
        assert restored.frequent_topics["仕事"].affinity_score == 0.8


class TestPhaseTransition:
    """PhaseTransition tests"""

    def test_serialization(self):
        """フェーズ遷移のシリアライズが正常に動作する"""
        transition = PhaseTransition(
            from_phase=RelationshipPhase.STRANGER,
            to_phase=RelationshipPhase.ACQUAINTANCE,
            transitioned_at=datetime.now(),
            interaction_count=6,
            trigger="interaction_milestone",
        )

        data = transition.to_dict()
        restored = PhaseTransition.from_dict(data)

        assert restored.from_phase == transition.from_phase
        assert restored.to_phase == transition.to_phase
        assert restored.interaction_count == transition.interaction_count


class TestUserRelationshipData:
    """UserRelationshipData tests"""

    def test_full_serialization(self):
        """全データのシリアライズが正常に動作する"""
        user_data = UserRelationshipData(
            user_id="user1",
            state=RelationshipState(
                user_id="user1",
                phase=RelationshipPhase.FAMILIAR,
                total_interactions=30,
            ),
            profile=AdaptiveProfile(
                user_id="user1",
                preferred_tone=ToneLevel.CASUAL,
            ),
            episodes=[
                Episode(
                    id="ep_1",
                    user_id="user1",
                    created_at=datetime.now(),
                    summary="Test episode",
                )
            ],
        )

        data = user_data.to_dict()
        restored = UserRelationshipData.from_dict(data)

        assert restored.user_id == user_data.user_id
        assert restored.state.phase == RelationshipPhase.FAMILIAR
        assert restored.profile.preferred_tone == ToneLevel.CASUAL
        assert len(restored.episodes) == 1
