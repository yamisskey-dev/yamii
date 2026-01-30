"""
統合感情分析サービス
複数の感情分析システムを統合した単一サービス（最適化版）
LLM併用で婉曲表現も検出可能
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from ..models.emotion import (
    NEGATIVE_EMOTIONS,
    POSITIVE_EMOTIONS,
    EmotionAnalysis,
    EmotionType,
)
from ..models.user import UserState

if TYPE_CHECKING:
    from ..ports.ai_port import IAIProvider


class EmotionService:
    """
    統合感情分析サービス

    パフォーマンス最適化:
    - 正規表現パターンを事前コンパイル
    - 危機キーワードの早期検出
    - キーワードセットによる高速マッチング

    LLM併用機能:
    - キーワード分析が曖昧なケースでLLMに依頼
    - 婉曲表現（「もういいかな」等）を検出
    """

    def __init__(self, ai_provider: IAIProvider | None = None):
        # LLM併用のためのAIプロバイダー（オプション）
        self._ai_provider = ai_provider

        # 婉曲表現パターン（LLM分析のトリガー）
        self._euphemism_patterns: list[re.Pattern] = [
            re.compile(r"もういい(かな|や|よね|のかな)"),
            re.compile(r"疲れた(かな|な|ね|よ)"),
            re.compile(r"(どうでも|何も|全部)いい"),
            re.compile(r"(意味|価値)(ない|がない|なんて)"),
            re.compile(r"(誰も|何も)(わかって|理解して)くれない"),
            re.compile(r"(いなく|消えて)(なりたい|しまいたい)"),
            re.compile(r"楽になりたい"),
            re.compile(r"(もう|全部)(終わり|おしまい)"),
            re.compile(r"(生きて|いて)(も|て)(意味|仕方)"),
            re.compile(r"(休み|眠り)たい(?!.*仕事|.*疲れ)"),  # 仕事疲れ以外の文脈
        ]

        # LLM分析用プロンプト
        self._llm_analysis_prompt = """あなたは感情分析の専門家です。以下のメッセージの感情を分析してください。

特に以下の婉曲表現に注意してください:
- 「もういいかな」「疲れた」→ 絶望や危機的状況を示唆する可能性
- 「どうでもいい」「意味がない」→ 無気力や抑うつの兆候
- 「楽になりたい」「消えたい」→ 自傷・自殺念慮の可能性

JSON形式で回答してください:
{
  "primary_emotion": "happiness|sadness|anxiety|anger|loneliness|depression|stress|confusion|hope|neutral",
  "intensity": 0.0-1.0,
  "is_crisis": true/false,
  "reasoning": "判断理由（日本語で簡潔に）"
}

メッセージ: """

        # 感情キーワード辞書（拡張版）
        self._emotion_keywords = {
            EmotionType.HAPPINESS: {
                "keywords": [
                    "嬉しい",
                    "楽しい",
                    "幸せ",
                    "最高",
                    "素晴らしい",
                    "感動",
                    "感激",
                    "興奮",
                    "ワクワク",
                    "ドキドキ",
                    "やったー",
                    "よっしゃ",
                    "やった",
                    "成功",
                    "達成",
                    "感謝",
                    "ありがとう",
                    "愛してる",
                    "大好き",
                    "完璧",
                    "理想",
                ],
                "weight": 2.0,
            },
            EmotionType.SADNESS: {
                "keywords": [
                    "悲しい",
                    "辛い",
                    "苦しい",
                    "切ない",
                    "寂しい",
                    "孤独",
                    "絶望",
                    "失望",
                    "落ち込む",
                    "凹む",
                    "しんどい",
                    "終わり",
                    "諦める",
                    "無理",
                    "ダメ",
                    "失敗",
                    "後悔",
                    "申し訳ない",
                    "ごめん",
                ],
                "weight": 3.0,
            },
            EmotionType.ANXIETY: {
                "keywords": [
                    "不安",
                    "心配",
                    "怖い",
                    "恐い",
                    "緊張",
                    "ハラハラ",
                    "焦る",
                    "急ぐ",
                    "間に合わない",
                    "やばい",
                    "まずい",
                    "危険",
                    "大変",
                    "困る",
                    "どうしよう",
                    "助けて",
                    "助け",
                    "救い",
                ],
                "weight": 2.5,
            },
            EmotionType.ANGER: {
                "keywords": [
                    "怒り",
                    "イライラ",
                    "腹立つ",
                    "ムカつく",
                    "キレる",
                    "許せない",
                    "最悪",
                    "うざい",
                    "うるさい",
                    "しつこい",
                    "めんどくさい",
                    "やだ",
                    "嫌い",
                    "大嫌い",
                ],
                "weight": 3.0,
            },
            EmotionType.LONELINESS: {
                "keywords": [
                    "寂しい",
                    "孤独",
                    "ひとり",
                    "一人",
                    "孤立",
                    "誰もいない",
                    "ひとりぼっち",
                    "仲間がいない",
                    "理解されない",
                    "孤独感",
                ],
                "weight": 2.5,
            },
            EmotionType.DEPRESSION: {
                "keywords": [
                    "死にたい",
                    "消えたい",
                    "生きる意味",
                    "無気力",
                    "やる気がない",
                    "生きていく意味",
                    "もう限界",
                    "生きるのが辛い",
                    "自分を傷つけ",
                ],
                "weight": 5.0,  # 最高重要度
            },
            EmotionType.STRESS: {
                "keywords": [
                    "疲れた",
                    "しんどい",
                    "限界",
                    "プレッシャー",
                    "ストレス",
                    "忙しい",
                    "余裕がない",
                    "追い詰められ",
                    "パンク",
                ],
                "weight": 2.0,
            },
            EmotionType.CONFUSION: {
                "keywords": [
                    "わからない",
                    "迷っている",
                    "どうしたら",
                    "困っている",
                    "混乱",
                    "判断できない",
                    "決められない",
                    "迷子",
                ],
                "weight": 1.5,
            },
            EmotionType.HOPE: {
                "keywords": [
                    "頑張りたい",
                    "変わりたい",
                    "希望",
                    "前向き",
                    "未来",
                    "目標",
                    "夢",
                    "可能性",
                    "チャンス",
                    "成長",
                ],
                "weight": 2.0,
            },
        }

        # 危機キーワード（セットで高速検索）
        self._crisis_keywords: set[str] = {
            "死にたい",
            "消えたい",
            "自殺",
            "生きる意味がない",
            "もう限界",
            "自分を傷つけ",
            "生きていく意味",
            "死んだ方がマシ",
            "終わりにしたい",
        }

        # 強調語・修飾語（セットで高速検索）
        self._emphasis_words: set[str] = {
            "すごく",
            "とても",
            "めちゃくちゃ",
            "超",
            "激",
            "死ぬほど",
            "マジで",
        }
        self._negation_words: set[str] = {
            "ない",
            "ません",
            "じゃない",
            "ではない",
            "違う",
            "ちがう",
        }

        # 事前コンパイル済みパターン
        self._compiled_patterns: dict[EmotionType, list[tuple[re.Pattern, float]]] = {}
        for emotion_type, emotion_data in self._emotion_keywords.items():
            weight = emotion_data["weight"]
            patterns = [
                (re.compile(re.escape(kw)), weight) for kw in emotion_data["keywords"]
            ]
            self._compiled_patterns[emotion_type] = patterns

        # 危機キーワードの結合パターン（一度の検索で全チェック）
        crisis_pattern = "|".join(re.escape(kw) for kw in self._crisis_keywords)
        self._crisis_pattern = re.compile(crisis_pattern)

    def analyze(self, message: str) -> EmotionAnalysis:
        """
        メッセージの感情を分析（同期版・キーワードベースのみ）

        Args:
            message: 分析するメッセージ

        Returns:
            EmotionAnalysis: 分析結果
        """
        return self._analyze_keyword_based(message)

    async def analyze_with_llm(self, message: str) -> EmotionAnalysis:
        """
        メッセージの感情を分析（LLM併用版）

        キーワード分析で信頼度が低いまたは婉曲表現を検出した場合、
        LLMに依頼してより深い分析を行う。

        Args:
            message: 分析するメッセージ

        Returns:
            EmotionAnalysis: 分析結果
        """
        # まずキーワードベースの高速分析
        keyword_result = self._analyze_keyword_based(message)

        # LLMが設定されていない場合はキーワード分析のみ
        if self._ai_provider is None:
            return keyword_result

        # LLM分析が必要かどうか判定
        needs_llm = self._needs_llm_analysis(message, keyword_result)

        if not needs_llm:
            return keyword_result

        # LLMで深い分析を実行
        llm_result = await self._analyze_with_llm(message, keyword_result)
        return llm_result

    def _analyze_keyword_based(self, message: str) -> EmotionAnalysis:
        """キーワードベースの感情分析（内部用）"""
        if not message or not message.strip():
            return EmotionAnalysis.neutral()

        message = message.strip()
        message_lower = message.lower()

        # 危機状況の早期検出（最優先）
        is_crisis = self._detect_crisis_fast(message_lower)

        # 各感情のスコアを計算（最適化版）
        emotion_scores = self._calculate_emotion_scores_fast(message_lower)

        # 修飾語の影響を計算
        emotion_scores = self._apply_modifiers_fast(message, emotion_scores)

        # 主要感情を特定
        primary_emotion, intensity = self._determine_primary_emotion(emotion_scores)

        # うつ病感情の高スコアも危機として扱う
        if not is_crisis and emotion_scores.get(EmotionType.DEPRESSION, 0) > 0:
            is_crisis = True

        # 安定性を計算
        stability = self._calculate_stability(emotion_scores)

        # 信頼度を計算
        confidence = self._calculate_confidence(emotion_scores, message)

        return EmotionAnalysis(
            primary_emotion=primary_emotion,
            intensity=intensity,
            stability=stability,
            is_crisis=is_crisis,
            all_emotions={k.value: v for k, v in emotion_scores.items()},
            confidence=confidence,
        )

    def _needs_llm_analysis(self, message: str, keyword_result: EmotionAnalysis) -> bool:
        """LLM分析が必要かどうか判定"""
        # 1. 婉曲表現パターンにマッチした場合
        for pattern in self._euphemism_patterns:
            if pattern.search(message):
                return True

        # 2. キーワード分析の信頼度が低い場合
        if keyword_result.confidence < 0.3:
            return True

        # 3. 中性だが一定の長さがある場合（感情が隠れている可能性）
        if (
            keyword_result.primary_emotion == EmotionType.NEUTRAL
            and len(message) > 30
        ):
            return True

        return False

    async def _analyze_with_llm(
        self, message: str, keyword_result: EmotionAnalysis
    ) -> EmotionAnalysis:
        """LLMを使った深い感情分析"""
        try:
            prompt = self._llm_analysis_prompt + message

            response = await self._ai_provider.generate(
                message=prompt,
                system_prompt="あなたは感情分析AIです。JSON形式のみで回答してください。",
                max_tokens=200,
            )

            # JSONをパース
            llm_analysis = self._parse_llm_response(response)

            if llm_analysis is None:
                # パース失敗時はキーワード分析を返す
                return keyword_result

            # LLM結果とキーワード結果を統合
            return self._merge_analyses(keyword_result, llm_analysis)

        except Exception:
            # エラー時はキーワード分析を返す
            return keyword_result

    def _parse_llm_response(self, response: str) -> dict | None:
        """LLMレスポンスからJSONをパース"""
        try:
            # JSON部分を抽出（マークダウンコードブロック対応）
            response = response.strip()
            if response.startswith("```"):
                # ```json ... ``` を除去
                lines = response.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```"):
                        in_json = not in_json
                        continue
                    if in_json:
                        json_lines.append(line)
                response = "\n".join(json_lines)

            return json.loads(response)
        except (json.JSONDecodeError, ValueError):
            return None

    def _merge_analyses(
        self, keyword_result: EmotionAnalysis, llm_analysis: dict
    ) -> EmotionAnalysis:
        """キーワード分析とLLM分析を統合"""
        # LLMの感情タイプを取得
        llm_emotion_str = llm_analysis.get("primary_emotion", "neutral")
        try:
            llm_emotion = EmotionType(llm_emotion_str)
        except ValueError:
            llm_emotion = EmotionType.NEUTRAL

        llm_intensity = float(llm_analysis.get("intensity", 0.5))
        llm_is_crisis = bool(llm_analysis.get("is_crisis", False))

        # 危機判定: どちらかがTrueならTrue
        merged_is_crisis = keyword_result.is_crisis or llm_is_crisis

        # LLMが危機を検出した場合はLLMの判断を優先
        if llm_is_crisis:
            return EmotionAnalysis(
                primary_emotion=llm_emotion,
                intensity=max(llm_intensity, keyword_result.intensity),
                stability=keyword_result.stability,
                is_crisis=True,
                all_emotions=keyword_result.all_emotions,
                confidence=0.8,  # LLM分析は高信頼度
            )

        # キーワード分析が何も検出していない場合はLLMを優先
        if keyword_result.primary_emotion == EmotionType.NEUTRAL:
            return EmotionAnalysis(
                primary_emotion=llm_emotion,
                intensity=llm_intensity,
                stability=keyword_result.stability,
                is_crisis=merged_is_crisis,
                all_emotions=keyword_result.all_emotions,
                confidence=0.7,
            )

        # それ以外はキーワード分析を基本として信頼度を上げる
        return EmotionAnalysis(
            primary_emotion=keyword_result.primary_emotion,
            intensity=keyword_result.intensity,
            stability=keyword_result.stability,
            is_crisis=merged_is_crisis,
            all_emotions=keyword_result.all_emotions,
            confidence=min(keyword_result.confidence + 0.2, 1.0),
        )

    def _detect_crisis_fast(self, message_lower: str) -> bool:
        """危機状況の高速検出（一度のマッチで全キーワードチェック）"""
        return bool(self._crisis_pattern.search(message_lower))

    def _calculate_emotion_scores_fast(
        self, message_lower: str
    ) -> dict[EmotionType, float]:
        """各感情のスコアを高速計算（事前コンパイル済みパターン使用）"""
        scores = {emotion: 0.0 for emotion in EmotionType}

        for emotion_type, patterns in self._compiled_patterns.items():
            score = 0.0
            for pattern, weight in patterns:
                matches = pattern.findall(message_lower)
                score += len(matches) * weight
            scores[emotion_type] = score

        return scores

    def _apply_modifiers_fast(
        self, message: str, scores: dict[EmotionType, float]
    ) -> dict[EmotionType, float]:
        """修飾語による感情スコアの高速調整"""
        modified_scores = scores.copy()

        # 否定語の検出（単語単位でセット比較）
        message_words = set(message.split())
        has_negation = bool(self._negation_words & message_words)
        if has_negation:
            modified_scores[EmotionType.HAPPINESS] = max(
                0, modified_scores[EmotionType.HAPPINESS] - 2
            )
            modified_scores[EmotionType.SADNESS] += 1
            modified_scores[EmotionType.ANXIETY] += 1

        # 強調語の検出（単語単位でセット比較）
        has_emphasis = bool(self._emphasis_words & message_words)
        if has_emphasis:
            for emotion in modified_scores:
                if emotion != EmotionType.NEUTRAL:
                    modified_scores[emotion] *= 1.5

        return modified_scores

    def update_user_patterns(self, user: UserState, analysis: EmotionAnalysis) -> None:
        """
        ユーザーの感情パターンを更新

        Args:
            user: ユーザー状態
            analysis: 感情分析結果
        """
        emotion_str = analysis.primary_emotion.value
        user.update_emotional_pattern(emotion_str)

    def get_sentiment_trend(self, user: UserState) -> str:
        """
        ユーザーのセンチメントトレンドを分析

        Args:
            user: ユーザー状態

        Returns:
            str: "improving", "stable", "declining"
        """
        patterns = user.emotional_patterns
        if not patterns:
            return "stable"

        total = sum(patterns.values())
        if total == 0:
            return "stable"

        positive_count = sum(patterns.get(e.value, 0) for e in POSITIVE_EMOTIONS)
        negative_count = sum(patterns.get(e.value, 0) for e in NEGATIVE_EMOTIONS)

        positive_ratio = positive_count / total
        negative_ratio = negative_count / total

        if positive_ratio > 0.6:
            return "improving"
        elif negative_ratio > 0.6:
            return "declining"
        return "stable"

    def _determine_primary_emotion(
        self, scores: dict[EmotionType, float]
    ) -> tuple[EmotionType, float]:
        """主要感情と強度を決定"""
        max_score = max(scores.values()) if scores.values() else 0

        if max_score == 0:
            return EmotionType.NEUTRAL, 0.0

        # 最高スコアの感情を特定
        primary_emotions = [
            emotion for emotion, score in scores.items() if score == max_score
        ]

        # 複数の感情が同じスコアの場合、優先度順で選択
        priority_order = [
            EmotionType.DEPRESSION,
            EmotionType.ANXIETY,
            EmotionType.SADNESS,
            EmotionType.ANGER,
            EmotionType.STRESS,
            EmotionType.LONELINESS,
            EmotionType.CONFUSION,
            EmotionType.HAPPINESS,
            EmotionType.HOPE,
        ]

        for emotion_type in priority_order:
            if emotion_type in primary_emotions:
                # 強度を0.0-1.0に正規化
                intensity = min(max_score / 10.0, 1.0)
                return emotion_type, intensity

        return EmotionType.NEUTRAL, 0.0

    def _calculate_stability(self, scores: dict[EmotionType, float]) -> float:
        """感情の安定性を計算"""
        non_zero_scores = [s for s in scores.values() if s > 0]
        if len(non_zero_scores) <= 1:
            return 1.0  # 単一または無感情は安定

        # 感情が分散しているほど不安定
        max_score = max(non_zero_scores)
        total_score = sum(non_zero_scores)
        if total_score == 0:
            return 1.0

        concentration = max_score / total_score
        return concentration

    def _calculate_confidence(
        self, scores: dict[EmotionType, float], message: str
    ) -> float:
        """分析の信頼度を計算"""
        total_score = sum(scores.values())
        max_score = max(scores.values()) if scores.values() else 0

        # 基本信頼度（最大スコアの割合）
        base_confidence = (max_score / max(total_score, 1)) if total_score > 0 else 0.0

        # メッセージ長による調整
        length_factor = min(len(message) / 50, 1.0)

        # 感情キーワード密度による調整
        word_count = max(len(message.split()), 1)
        emotion_density = total_score / word_count
        density_factor = min(emotion_density / 2.0, 1.0)

        confidence = (base_confidence + length_factor + density_factor) / 3.0
        return min(confidence, 1.0)
