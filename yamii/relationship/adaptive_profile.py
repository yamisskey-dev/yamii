"""
適応プロファイルマネージャー
対話からユーザーの好みを学習し、応答スタイルを適応
"""

from datetime import datetime
from typing import List

from .models import AdaptiveProfile, ToneLevel, DepthLevel, TopicAffinity


class AdaptiveProfileManager:
    """
    適応プロファイルマネージャー

    対話からユーザーの好みを学習し、応答スタイルを適応させる。
    シェイプシフター的に相手に合わせて変化していく。
    """

    # トピック検出キーワード
    TOPIC_KEYWORDS = {
        "仕事": ["仕事", "職場", "会社", "上司", "同僚", "転職", "キャリア", "残業"],
        "恋愛": ["恋愛", "彼氏", "彼女", "パートナー", "デート", "告白", "失恋", "結婚"],
        "家族": ["家族", "親", "父", "母", "兄弟", "子供", "育児", "介護"],
        "友人関係": ["友達", "友人", "人間関係", "仲間", "付き合い"],
        "健康": ["健康", "病気", "体調", "病院", "治療", "メンタル", "うつ", "睡眠"],
        "お金": ["お金", "給料", "貯金", "借金", "投資", "節約"],
        "将来": ["将来", "夢", "目標", "進路", "人生設計", "未来"],
        "趣味": ["趣味", "ゲーム", "音楽", "映画", "旅行", "スポーツ", "読書"],
        "学業": ["勉強", "学校", "大学", "受験", "テスト", "成績"],
        "ストレス": ["ストレス", "プレッシャー", "不安", "心配", "疲れ"],
        "自己肯定感": ["自信", "自己肯定", "価値", "存在意義", "自分らしさ"],
    }

    # 感情カテゴリ
    NEGATIVE_EMOTIONS = {
        "sadness", "anxiety", "anger", "loneliness",
        "depression", "stress", "confusion",
    }
    POSITIVE_EMOTIONS = {"happiness", "hope"}

    def __init__(self):
        pass

    def update_from_interaction(
        self,
        profile: AdaptiveProfile,
        message: str,
        topics: List[str],
        emotion: str,
        emotion_intensity: float,
    ) -> AdaptiveProfile:
        """
        対話から適応プロファイルを更新

        Args:
            profile: 現在のプロファイル
            message: ユーザーメッセージ
            topics: 検出されたトピック
            emotion: 感情
            emotion_intensity: 感情の強さ (0.0-1.0)

        Returns:
            更新されたプロファイル
        """
        # トピック関心度を更新
        profile = self._update_topic_affinities(profile, message, topics)

        # 感情パターンを記録
        profile = self._update_emotional_patterns(profile, emotion)

        # コミュニケーション好みを学習
        profile = self._learn_communication_preferences(
            profile, message, emotion, emotion_intensity
        )

        # トーンとデプスを調整
        profile = self._adjust_tone_and_depth(profile, emotion, emotion_intensity)

        # 確信度を更新
        profile = self._update_confidence(profile)

        profile.last_updated = datetime.now()

        return profile

    def _update_topic_affinities(
        self,
        profile: AdaptiveProfile,
        message: str,
        topics: List[str],
    ) -> AdaptiveProfile:
        """トピック関心度を更新"""
        # 既存トピックの更新
        for topic in topics:
            if topic in profile.frequent_topics:
                affinity = profile.frequent_topics[topic]
                affinity.mention_count += 1
                affinity.last_mentioned = datetime.now()
                # 関心度を少し上げる
                affinity.affinity_score = min(1.0, affinity.affinity_score + 0.05)
            else:
                profile.frequent_topics[topic] = TopicAffinity(
                    topic=topic,
                    affinity_score=0.2,
                    mention_count=1,
                    last_mentioned=datetime.now(),
                )

        # メッセージからも追加トピックを検出
        message_lower = message.lower()
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if topic not in topics and any(kw in message_lower for kw in keywords):
                if topic in profile.frequent_topics:
                    affinity = profile.frequent_topics[topic]
                    affinity.mention_count += 1
                    affinity.affinity_score = min(1.0, affinity.affinity_score + 0.02)
                else:
                    profile.frequent_topics[topic] = TopicAffinity(
                        topic=topic,
                        affinity_score=0.1,
                        mention_count=1,
                        last_mentioned=datetime.now(),
                    )

        # 古いトピックの関心度を緩やかに減衰
        now = datetime.now()
        for topic, affinity in profile.frequent_topics.items():
            if affinity.last_mentioned:
                days_since = (now - affinity.last_mentioned).days
                if days_since > 30:
                    affinity.affinity_score = max(0.0, affinity.affinity_score - 0.01)

        return profile

    def _update_emotional_patterns(
        self,
        profile: AdaptiveProfile,
        emotion: str,
    ) -> AdaptiveProfile:
        """感情パターンを記録"""
        profile.emotional_patterns[emotion] = (
            profile.emotional_patterns.get(emotion, 0) + 1
        )
        return profile

    def _learn_communication_preferences(
        self,
        profile: AdaptiveProfile,
        message: str,
        emotion: str,
        emotion_intensity: float,
    ) -> AdaptiveProfile:
        """コミュニケーション好みを学習"""
        msg_len = len(message)
        adjustment = 0.02  # 調整幅

        # メッセージ長から詳細さの好みを学習
        if msg_len > 300:
            profile.likes_detail = min(1.0, profile.likes_detail + adjustment)
        elif msg_len < 50:
            profile.likes_detail = max(0.0, profile.likes_detail - adjustment)

        # 質問形式のメッセージがあるか
        if "?" in message or "？" in message:
            # 質問している = アドバイスを求めている可能性
            profile.likes_advice = min(1.0, profile.likes_advice + adjustment * 0.5)

        # 感情的な内容 = 共感を重視する可能性
        if emotion in self.NEGATIVE_EMOTIONS or emotion_intensity > 0.6:
            profile.likes_empathy = min(1.0, profile.likes_empathy + adjustment)

        # 「なんで」「どうして」などの質問 = 質問を好む可能性
        question_keywords = ["なんで", "どうして", "なぜ", "どうすれば", "どうしたら"]
        if any(kw in message for kw in question_keywords):
            profile.likes_questions = min(1.0, profile.likes_questions + adjustment)

        return profile

    def _adjust_tone_and_depth(
        self,
        profile: AdaptiveProfile,
        emotion: str,
        emotion_intensity: float,
    ) -> AdaptiveProfile:
        """トーンとデプスを調整"""
        # ネガティブな感情が多い場合は温かいトーンに
        negative_count = sum(
            profile.emotional_patterns.get(e, 0)
            for e in self.NEGATIVE_EMOTIONS
        )
        positive_count = sum(
            profile.emotional_patterns.get(e, 0)
            for e in self.POSITIVE_EMOTIONS
        )
        total_count = sum(profile.emotional_patterns.values()) or 1

        negative_ratio = negative_count / total_count

        if negative_ratio > 0.6:
            profile.preferred_tone = ToneLevel.WARM
        elif negative_ratio < 0.3 and positive_count > negative_count:
            profile.preferred_tone = ToneLevel.CASUAL
        else:
            profile.preferred_tone = ToneLevel.BALANCED

        # 詳細さの好みに応じてデプスを調整
        if profile.likes_detail > 0.7:
            profile.preferred_depth = DepthLevel.DEEP
        elif profile.likes_detail < 0.3:
            profile.preferred_depth = DepthLevel.SHALLOW
        else:
            profile.preferred_depth = DepthLevel.MEDIUM

        return profile

    def _update_confidence(self, profile: AdaptiveProfile) -> AdaptiveProfile:
        """確信度を更新"""
        # トピック数と感情パターン数から確信度を計算
        topic_count = len(profile.frequent_topics)
        emotion_count = sum(profile.emotional_patterns.values())

        # 確信度は対話量に応じて増加（最大1.0）
        profile.confidence_score = min(
            1.0,
            (topic_count * 0.05) + (emotion_count * 0.01),
        )

        return profile

    def get_top_topics(
        self, profile: AdaptiveProfile, n: int = 5
    ) -> List[TopicAffinity]:
        """上位トピックを取得"""
        sorted_topics = sorted(
            profile.frequent_topics.values(),
            key=lambda t: t.affinity_score,
            reverse=True,
        )
        return sorted_topics[:n]

    def get_dominant_emotion(self, profile: AdaptiveProfile) -> str:
        """支配的な感情を取得"""
        if not profile.emotional_patterns:
            return "neutral"

        return max(profile.emotional_patterns, key=profile.emotional_patterns.get)

    def get_communication_style_summary(self, profile: AdaptiveProfile) -> dict:
        """コミュニケーションスタイルのサマリーを取得"""
        return {
            "tone": profile.preferred_tone.value,
            "depth": profile.preferred_depth.value,
            "likes_questions": profile.likes_questions,
            "likes_advice": profile.likes_advice,
            "likes_empathy": profile.likes_empathy,
            "likes_detail": profile.likes_detail,
            "confidence": profile.confidence_score,
        }

    def should_ask_question(self, profile: AdaptiveProfile) -> bool:
        """質問を投げかけるべきか"""
        return profile.likes_questions > 0.5

    def should_give_advice(self, profile: AdaptiveProfile) -> bool:
        """アドバイスを提供すべきか"""
        return profile.likes_advice > 0.5

    def should_emphasize_empathy(self, profile: AdaptiveProfile) -> bool:
        """共感を強調すべきか"""
        return profile.likes_empathy > 0.6
