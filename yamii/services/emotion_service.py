"""
感情分析サービス
aichat.pyとcounseling_service.pyの重複ロジックを統一
"""

import re
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from ..core.logging import get_logger
from ..core.exceptions import ValidationError


class EmotionType(Enum):
    """感情タイプ列挙型"""
    HAPPINESS = "happiness"
    SADNESS = "sadness" 
    ANXIETY = "anxiety"
    ANGER = "anger"
    LONELINESS = "loneliness"
    DEPRESSION = "depression"
    STRESS = "stress"
    CONFUSION = "confusion"
    HOPE = "hope"
    NEUTRAL = "neutral"


@dataclass
class EmotionAnalysis:
    """感情分析結果"""
    primary_emotion: EmotionType
    intensity: int  # 0-10
    is_crisis: bool
    all_emotions: Dict[str, int]
    confidence: float  # 0.0-1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "primary_emotion": self.primary_emotion.value,
            "intensity": self.intensity,
            "is_crisis": self.is_crisis,
            "all_emotions": self.all_emotions,
            "confidence": self.confidence
        }


class EmotionAnalysisService:
    """感情分析サービス"""
    
    def __init__(self):
        self.logger = get_logger("emotion_service")
        
        # 感情キーワード辞書（拡張版）
        self._emotion_keywords = {
            EmotionType.HAPPINESS.value: {
                "keywords": [
                    "嬉しい", "楽しい", "幸せ", "最高", "素晴らしい", "感動", "感激", "興奮",
                    "ワクワク", "ドキドキ", "やったー", "よっしゃ", "やった", "成功", "達成",
                    "感謝", "ありがとう", "愛してる", "大好き", "完璧", "理想"
                ],
                "emojis": [":smile:", ":grin:", ":laughing:", ":joy:", ":heart:", 
                          ":heart_eyes:", ":blush:", ":wink:", ":ok_hand:", ":thumbsup:",
                          ":clap:", ":tada:", ":sparkles:", ":star:", ":rainbow:", ":sunny:"],
                "weight": 2.0
            },
            EmotionType.SADNESS.value: {
                "keywords": [
                    "悲しい", "辛い", "苦しい", "切ない", "寂しい", "孤独", "絶望", "失望",
                    "落ち込む", "凹む", "しんどい", "疲れた", "終わり", "諦める", 
                    "無理", "ダメ", "失敗", "後悔", "申し訳ない", "ごめん"
                ],
                "emojis": [":cry:", ":sob:", ":broken_heart:", ":disappointed:"],
                "weight": 3.0
            },
            EmotionType.ANXIETY.value: {
                "keywords": [
                    "不安", "心配", "怖い", "恐い", "緊張", "ハラハラ", "焦る", "急ぐ",
                    "間に合わない", "やばい", "まずい", "危険", "大変", "困る", 
                    "どうしよう", "助けて", "助け", "救い"
                ],
                "emojis": [":fearful:", ":worried:", ":cold_sweat:", ":sweat:"],
                "weight": 2.5
            },
            EmotionType.ANGER.value: {
                "keywords": [
                    "怒り", "イライラ", "腹立つ", "ムカつく", "キレる", "許せない", "最悪",
                    "クソ", "うざい", "うるさい", "しつこい", "めんどくさい", "やだ",
                    "嫌い", "大嫌い", "消えろ", "殴る"
                ],
                "emojis": [":rage:", ":angry:", ":punch:", ":middle_finger:"],
                "weight": 3.0
            },
            EmotionType.LONELINESS.value: {
                "keywords": [
                    "寂しい", "孤独", "ひとり", "一人", "孤立", "誰もいない", "ひとりぼっち",
                    "仲間がいない", "理解されない", "孤独感"
                ],
                "emojis": [],
                "weight": 2.5
            },
            EmotionType.DEPRESSION.value: {
                "keywords": [
                    "死にたい", "消えたい", "生きる意味", "無気力", "やる気がない",
                    "生きていく意味", "もう限界", "生きるのが辛い", "自分を傷つけ"
                ],
                "emojis": [],
                "weight": 5.0  # 最高重要度
            },
            EmotionType.STRESS.value: {
                "keywords": [
                    "疲れた", "しんどい", "限界", "プレッシャー", "ストレス", "忙しい",
                    "余裕がない", "追い詰められ", "パンク"
                ],
                "emojis": [],
                "weight": 2.0
            },
            EmotionType.CONFUSION.value: {
                "keywords": [
                    "わからない", "迷っている", "どうしたら", "困っている", "混乱",
                    "判断できない", "決められない", "迷子"
                ],
                "emojis": [":thinking:", ":neutral_face:", ":expressionless:"],
                "weight": 1.5
            },
            EmotionType.HOPE.value: {
                "keywords": [
                    "頑張りたい", "変わりたい", "希望", "前向き", "未来", "目標",
                    "夢", "可能性", "チャンス", "成長"
                ],
                "emojis": [],
                "weight": 2.0
            }
        }
        
        # 危機キーワード
        self._crisis_keywords = [
            "死にたい", "消えたい", "自殺", "生きる意味がない", "もう限界",
            "自分を傷つけ", "生きていく意味", "死んだ方がマシ", "終わりにしたい"
        ]
        
        # 強調語・修飾語
        self._emphasis_words = ["すごく", "とても", "めちゃくちゃ", "超", "激", "死ぬほど", "マジで"]
        self._negation_words = ["ない", "ません", "じゃない", "ではない", "違う", "ちがう"]
    
    def analyze_emotion(self, message: str) -> EmotionAnalysis:
        """メッセージの感情を分析"""
        if not message or not message.strip():
            raise ValidationError("分析するメッセージが空です", field="message")
        
        message = message.strip()
        self.logger.info(f"Analyzing emotion for message (length: {len(message)})")
        
        # 各感情のスコアを計算
        emotion_scores = self._calculate_emotion_scores(message)
        
        # 修飾語の影響を計算
        emotion_scores = self._apply_modifiers(message, emotion_scores)
        
        # 主要感情を特定
        primary_emotion, intensity = self._determine_primary_emotion(emotion_scores)
        
        # 危機状況の判定
        is_crisis = self._detect_crisis(message, emotion_scores)
        
        # 信頼度を計算
        confidence = self._calculate_confidence(emotion_scores, message)
        
        analysis = EmotionAnalysis(
            primary_emotion=primary_emotion,
            intensity=intensity,
            is_crisis=is_crisis,
            all_emotions=emotion_scores,
            confidence=confidence
        )
        
        self.logger.info(f"Emotion analysis result: {primary_emotion.value} (intensity: {intensity}, crisis: {is_crisis})")
        
        return analysis
    
    def _calculate_emotion_scores(self, message: str) -> Dict[str, int]:
        """各感情のスコアを計算"""
        scores = {}
        message_lower = message.lower()
        
        for emotion_name, emotion_data in self._emotion_keywords.items():
            score = 0
            
            # キーワードマッチング
            for keyword in emotion_data["keywords"]:
                count = len(re.findall(re.escape(keyword), message_lower))
                score += count * emotion_data["weight"]
            
            # 絵文字マッチング
            for emoji in emotion_data["emojis"]:
                count = message.count(emoji)
                score += count * emotion_data["weight"]
            
            scores[emotion_name] = int(score)
        
        return scores
    
    def _apply_modifiers(self, message: str, scores: Dict[str, int]) -> Dict[str, int]:
        """修飾語による感情スコアの調整"""
        modified_scores = scores.copy()
        
        # 否定語の検出
        has_negation = any(word in message for word in self._negation_words)
        if has_negation:
            # ポジティブな感情を減らし、ネガティブな感情を増やす
            modified_scores[EmotionType.HAPPINESS.value] = max(0, 
                modified_scores[EmotionType.HAPPINESS.value] - 2)
            modified_scores[EmotionType.SADNESS.value] += 1
            modified_scores[EmotionType.ANXIETY.value] += 1
        
        # 強調語の検出
        has_emphasis = any(word in message for word in self._emphasis_words)
        if has_emphasis:
            # すべての感情を1.5倍に
            for emotion in modified_scores:
                if emotion != EmotionType.NEUTRAL.value:
                    modified_scores[emotion] = int(modified_scores[emotion] * 1.5)
        
        return modified_scores
    
    def _determine_primary_emotion(self, scores: Dict[str, int]) -> tuple[EmotionType, int]:
        """主要感情と強度を決定"""
        max_score = max(scores.values()) if scores.values() else 0
        
        if max_score == 0:
            return EmotionType.NEUTRAL, 0
        
        # 最高スコアの感情を特定
        primary_emotions = [emotion for emotion, score in scores.items() 
                          if score == max_score]
        
        # 複数の感情が同じスコアの場合、優先度順で選択
        priority_order = [
            EmotionType.DEPRESSION.value,
            EmotionType.ANXIETY.value,
            EmotionType.SADNESS.value,
            EmotionType.ANGER.value,
            EmotionType.STRESS.value,
            EmotionType.LONELINESS.value,
            EmotionType.CONFUSION.value,
            EmotionType.HAPPINESS.value,
            EmotionType.HOPE.value
        ]
        
        for emotion_name in priority_order:
            if emotion_name in primary_emotions:
                emotion_type = EmotionType(emotion_name)
                intensity = min(max_score, 10)  # 最大10に制限
                return emotion_type, intensity
        
        return EmotionType.NEUTRAL, 0
    
    def _detect_crisis(self, message: str, scores: Dict[str, int]) -> bool:
        """危機状況の検出"""
        # 危機キーワードの直接チェック
        message_lower = message.lower()
        for keyword in self._crisis_keywords:
            if keyword in message_lower:
                return True
        
        # うつ病感情の高スコア
        if scores.get(EmotionType.DEPRESSION.value, 0) > 0:
            return True
        
        # 複数のネガティブ感情の組み合わせ
        negative_emotions = [
            EmotionType.SADNESS.value,
            EmotionType.ANXIETY.value, 
            EmotionType.STRESS.value,
            EmotionType.LONELINESS.value
        ]
        
        active_negative_emotions = sum(1 for emotion in negative_emotions 
                                     if scores.get(emotion, 0) > 3)
        
        if active_negative_emotions >= 3:
            return True
        
        return False
    
    def _calculate_confidence(self, scores: Dict[str, int], message: str) -> float:
        """分析の信頼度を計算"""
        total_score = sum(scores.values())
        max_score = max(scores.values()) if scores.values() else 0
        
        # 基本信頼度（最大スコアの割合）
        base_confidence = (max_score / max(total_score, 1)) if total_score > 0 else 0.0
        
        # メッセージ長による調整
        length_factor = min(len(message) / 50, 1.0)  # 50文字で最大
        
        # 感情キーワード密度による調整
        emotion_density = total_score / max(len(message.split()), 1)
        density_factor = min(emotion_density / 2.0, 1.0)
        
        confidence = (base_confidence + length_factor + density_factor) / 3.0
        return min(confidence, 1.0)
    
    def get_emotion_description(self, emotion_type: EmotionType) -> str:
        """感情タイプの説明を取得"""
        descriptions = {
            EmotionType.HAPPINESS: "喜び・幸福感",
            EmotionType.SADNESS: "悲しみ・落胆",
            EmotionType.ANXIETY: "不安・心配",
            EmotionType.ANGER: "怒り・イライラ",
            EmotionType.LONELINESS: "孤独感・寂しさ",
            EmotionType.DEPRESSION: "うつ・絶望感",
            EmotionType.STRESS: "ストレス・疲労",
            EmotionType.CONFUSION: "混乱・迷い",
            EmotionType.HOPE: "希望・前向きさ",
            EmotionType.NEUTRAL: "中性・平常"
        }
        return descriptions.get(emotion_type, "不明")