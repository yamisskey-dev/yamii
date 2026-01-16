"""Tests for episode manager"""

import pytest
from datetime import datetime

from yamii.relationship.models import Episode, EpisodeType
from yamii.relationship.episode_manager import EpisodeManager


class TestEpisodeManager:
    """EpisodeManager tests"""

    def setup_method(self):
        self.manager = EpisodeManager()

    def test_normal_message_not_create_episode(self):
        """通常のメッセージではエピソードを作成しない"""
        episode = self.manager.maybe_create_episode(
            user_id="user1",
            message="こんにちは",
            topics=[],
            emotion="neutral",
            emotion_intensity=0.3,
            is_crisis=False,
            user_shared_info=[],
            known_topics=set(),
        )

        assert episode is None

    def test_crisis_creates_episode(self):
        """危機的状況ではエピソードを作成する"""
        episode = self.manager.maybe_create_episode(
            user_id="user1",
            message="もう限界です。死にたいと思うことがあります。",
            topics=["ストレス"],
            emotion="depression",
            emotion_intensity=0.9,
            is_crisis=True,
            user_shared_info=[],
            known_topics=set(),
        )

        assert episode is not None
        assert episode.episode_type == EpisodeType.CRISIS
        assert episode.importance_score >= 0.5

    def test_personal_disclosure_creates_episode(self):
        """個人情報の開示でエピソードを作成する"""
        episode = self.manager.maybe_create_episode(
            user_id="user1",
            message="実は誰にも言ってないんですけど、転職を考えています",
            topics=["仕事"],
            emotion="anxiety",
            emotion_intensity=0.7,
            is_crisis=False,
            user_shared_info=["転職を考えている"],
            known_topics=set(),
        )

        assert episode is not None
        assert episode.episode_type == EpisodeType.DISCLOSURE
        assert "転職を考えている" in episode.user_shared

    def test_new_topic_increases_importance(self):
        """新しいトピックは重要度を上げる"""
        episode1 = self.manager.maybe_create_episode(
            user_id="user1",
            message="仕事でストレスを感じています。実は上司と合わなくて...",
            topics=["仕事", "ストレス"],
            emotion="stress",
            emotion_intensity=0.7,
            is_crisis=False,
            user_shared_info=["上司と合わない"],
            known_topics=set(),  # 新しいトピック
        )

        episode2 = self.manager.maybe_create_episode(
            user_id="user1",
            message="仕事でストレスを感じています。実は上司と合わなくて...",
            topics=["仕事", "ストレス"],
            emotion="stress",
            emotion_intensity=0.7,
            is_crisis=False,
            user_shared_info=["上司と合わない"],
            known_topics={"仕事", "ストレス"},  # 既知のトピック
        )

        if episode1 and episode2:
            assert episode1.importance_score >= episode2.importance_score

    def test_insight_keyword_creates_insight_episode(self):
        """洞察キーワードでINSIGHTエピソードを作成"""
        episode = self.manager.maybe_create_episode(
            user_id="user1",
            message="なるほど、そう考えると気づいたことがあります。自分は完璧を求めすぎていたんですね。",
            topics=["自己肯定感"],
            emotion="hope",
            emotion_intensity=0.6,
            is_crisis=False,
            user_shared_info=[],
            known_topics=set(),
        )

        assert episode is not None
        assert episode.episode_type == EpisodeType.INSIGHT

    def test_search_episodes_by_topic(self):
        """トピックでエピソードを検索できる"""
        episodes = [
            Episode(
                id="ep_1",
                user_id="user1",
                created_at=datetime.now(),
                summary="仕事の悩み",
                topics=["仕事", "ストレス"],
                keywords=["上司", "残業"],
            ),
            Episode(
                id="ep_2",
                user_id="user1",
                created_at=datetime.now(),
                summary="家族の話",
                topics=["家族"],
                keywords=["親", "介護"],
            ),
        ]

        results = self.manager.search_episodes(
            episodes=episodes,
            query="仕事",
            limit=5,
        )

        assert len(results) == 1
        assert results[0].id == "ep_1"

    def test_search_episodes_by_keyword(self):
        """キーワードでエピソードを検索できる"""
        episodes = [
            Episode(
                id="ep_1",
                user_id="user1",
                created_at=datetime.now(),
                summary="上司との関係",
                topics=["仕事"],
                keywords=["上司", "パワハラ"],
            ),
        ]

        results = self.manager.search_episodes(
            episodes=episodes,
            query="パワハラ",
            limit=5,
        )

        assert len(results) == 1

    def test_get_important_episodes(self):
        """重要なエピソードを取得できる"""
        episodes = [
            Episode(
                id="ep_1",
                user_id="user1",
                created_at=datetime.now(),
                summary="普通の話",
                importance_score=0.3,
            ),
            Episode(
                id="ep_2",
                user_id="user1",
                created_at=datetime.now(),
                summary="重要な話",
                importance_score=0.8,
            ),
        ]

        important = self.manager.get_important_episodes(
            episodes=episodes,
            min_importance=0.6,
        )

        assert len(important) == 1
        assert important[0].id == "ep_2"

    def test_get_recent_episodes(self):
        """最近のエピソードを取得できる"""
        episodes = [
            Episode(
                id="ep_1",
                user_id="user1",
                created_at=datetime(2024, 1, 1),
                summary="古い話",
            ),
            Episode(
                id="ep_2",
                user_id="user1",
                created_at=datetime(2024, 12, 1),
                summary="新しい話",
            ),
        ]

        recent = self.manager.get_recent_episodes(episodes=episodes, limit=1)

        assert len(recent) == 1
        assert recent[0].id == "ep_2"
