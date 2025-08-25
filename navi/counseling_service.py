"""
Counseling Service - 人生相談に特化したAIサービス
独立したAPIサーバーとして設計
"""

import asyncio
import aiohttp
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import base64
import logging
from .markdown_prompt_loader import get_prompt_loader, get_prompt_text

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CounselingRequest:
    """人生相談リクエスト"""
    def __init__(self, message: str, user_id: str, session_id: Optional[str] = None,
                 user_name: Optional[str] = None, context: Optional[Dict] = None,
                 custom_prompt_id: Optional[str] = None, prompt_id: Optional[str] = None):
        self.message = message
        self.user_id = user_id
        self.session_id = session_id
        self.user_name = user_name
        self.context = context or {}
        self.custom_prompt_id = custom_prompt_id
        self.prompt_id = prompt_id


class CounselingResponse:
    """人生相談レスポンス"""
    def __init__(self, response: str, session_id: str, emotion_analysis: Dict,
                 advice_type: str, follow_up_questions: List[str] = None):
        self.response = response
        self.session_id = session_id
        self.emotion_analysis = emotion_analysis
        self.advice_type = advice_type
        self.follow_up_questions = follow_up_questions or []


class CounselingService:
    """人生相談サービス"""
    
    def __init__(self, gemini_api_key: str, custom_prompt_manager=None,
                 user_profile_manager=None, default_prompt_id: str = "default_counselor"):
        self.gemini_api_key = gemini_api_key
        self.gemini_model = "gemini-2.0-flash-exp"
        self.gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        self.custom_prompt_manager = custom_prompt_manager
        self.user_profile_manager = user_profile_manager
        self.default_prompt_id = default_prompt_id
        self.prompt_loader = get_prompt_loader()
    
    def analyze_emotion(self, message: str) -> Dict[str, Any]:
        """感情分析"""
        emotions = {
            'sadness': 0,
            'anxiety': 0,
            'anger': 0,
            'loneliness': 0,
            'depression': 0,
            'stress': 0,
            'confusion': 0,
            'hope': 0
        }
        
        # 感情キーワード分析
        emotion_keywords = {
            'sadness': ['悲しい', '辛い', '泣きたい', '憂鬱', 'つらい', '切ない', '悲しみ'],
            'anxiety': ['不安', '心配', '怖い', '恐い', 'やばい', 'ドキドキ', '緊張'],
            'anger': ['怒り', 'イライラ', '腹立つ', 'ムカつく', '許せない', 'うざい'],
            'loneliness': ['寂しい', '孤独', 'ひとり', '一人', '孤立', '誰もいない'],
            'depression': ['死にたい', '消えたい', '生きる意味', '無気力', 'やる気がない'],
            'stress': ['疲れた', 'しんどい', '限界', 'プレッシャー', 'ストレス'],
            'confusion': ['わからない', '迷っている', 'どうしたら', '困っている'],
            'hope': ['頑張りたい', '変わりたい', '希望', '前向き', '未来', '目標']
        }
        
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in message:
                    emotions[emotion] += 1
        
        # 主要感情を特定
        primary_emotion = max(emotions, key=emotions.get)
        emotion_intensity = emotions[primary_emotion]
        
        return {
            'primary_emotion': primary_emotion,
            'intensity': emotion_intensity,
            'all_emotions': emotions,
            'is_crisis': emotions['depression'] > 0 or '死' in message
        }
    
    def determine_advice_type(self, emotion_analysis: Dict, message: str) -> str:
        """アドバイスタイプを決定"""
        if emotion_analysis['is_crisis']:
            return 'crisis_support'
        elif emotion_analysis['primary_emotion'] == 'depression':
            return 'mental_health'
        elif '恋愛' in message or '恋人' in message or '彼氏' in message or '彼女' in message:
            return 'relationship'
        elif '仕事' in message or '職場' in message or '転職' in message:
            return 'career'
        elif '家族' in message or '親' in message:
            return 'family'
        elif '友達' in message or '友人' in message:
            return 'friendship'
        elif '勉強' in message or '学校' in message:
            return 'education'
        else:
            return 'general_support'
    
    def generate_follow_up_questions(self, advice_type: str, emotion_analysis: Dict) -> List[str]:
        """フォローアップ質問を生成"""
        follow_ups = {
            'crisis_support': [
                '今、誰か信頼できる人はそばにいますか？',
                '専門のカウンセラーに相談することを考えてみませんか？'
            ],
            'mental_health': [
                'この状況はいつ頃から続いていますか？',
                '今まで試してみた対処法はありますか？'
            ],
            'relationship': [
                'お相手とはどのくらいお付き合いされているのですか？',
                'この問題について話し合ったことはありますか？'
            ],
            'career': [
                '現在の職場環境についてもう少し教えてください',
                '理想的な働き方はどのようなものですか？'
            ],
            'general_support': [
                'このことで一番困っていることは何ですか？',
                '理想的な状況はどのようなものでしょうか？'
            ]
        }
        
        return follow_ups.get(advice_type, follow_ups['general_support'])
    
    async def generate_counseling_response(self, request: CounselingRequest) -> CounselingResponse:
        """人生相談レスポンスを生成"""
        try:
            # 感情分析
            emotion_analysis = self.analyze_emotion(request.message)
            advice_type = self.determine_advice_type(emotion_analysis, request.message)
            
            # 現在時刻
            now = datetime.now().strftime('%Y年%m月%d日 %H:%M')
            
            # カスタムプロンプト取得
            custom_prompt = self._get_prompt_for_request(request)
            
            # プロンプト構築
            system_instruction = f"""
{custom_prompt}

現在日時: {now}
相談者: {request.user_name or request.user_id}
感情分析結果: {emotion_analysis['primary_emotion']}（強度: {emotion_analysis['intensity']}）
相談タイプ: {advice_type}

以下の点を考慮して回答してください:
- 相談者の感情に共感する
- 具体的で実践的なアドバイスを提供する
- 必要に応じて専門機関を紹介する
- 希望と励ましのメッセージを含める
"""
            
            # 危機的状況の場合の特別対応
            if emotion_analysis['is_crisis']:
                system_instruction += """
⚠️ 重要: これは危機的状況の可能性があります。
- 専門的な支援機関への相談を強く推奨する
- いのちの電話（0570-783-556）などの情報を提供する
- 「あなたは一人じゃない」というメッセージを伝える
"""
            
            # Gemini API呼び出し
            gemini_options = {
                'contents': [{
                    'role': 'user',
                    'parts': [{'text': request.message}]
                }],
                'systemInstruction': {
                    'role': 'system',
                    'parts': [{'text': system_instruction}]
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.gemini_api_url,
                    params={'key': self.gemini_api_key},
                    json=gemini_options
                ) as response:
                    response_data = await response.json()
                    
                    if 'candidates' not in response_data:
                        raise Exception('No candidates in Gemini response')
                    
                    candidate = response_data['candidates'][0]
                    response_text = candidate['content']['parts'][0]['text']
                    
                    # フォローアップ質問を生成
                    follow_up_questions = self.generate_follow_up_questions(advice_type, emotion_analysis)
                    
                    # カスタムプロンプトの使用回数を増加
                    if hasattr(request, 'custom_prompt_id') and request.custom_prompt_id and self.custom_prompt_manager:
                        self.custom_prompt_manager.increment_usage(request.custom_prompt_id)
                    
                    return CounselingResponse(
                        response=response_text,
                        session_id=request.session_id or f"session_{datetime.now().timestamp()}",
                        emotion_analysis=emotion_analysis,
                        advice_type=advice_type,
                        follow_up_questions=follow_up_questions
                    )
                    
        except Exception as e:
            logger.error(f'Counseling response generation failed: {e}')
            
            # エラー時のフォールバック応答
            return CounselingResponse(
                response="申し訳ありません。今少し調子が悪いようです。時間を置いてもう一度お試しいただくか、信頼できる方に直接相談することをお勧めします。あなたは一人ではありません。",
                session_id=request.session_id or f"session_{datetime.now().timestamp()}",
                emotion_analysis={'primary_emotion': 'neutral', 'intensity': 0, 'is_crisis': False, 'all_emotions': {}},
                advice_type='general_support',
                follow_up_questions=['他に何かお手伝いできることはありますか？']
            )
    
    def _get_prompt_for_request(self, request: CounselingRequest) -> str:
        """リクエストに応じたプロンプトを取得（user_idベースでカスタムプロンプト自動適用）"""
        
        print(f"[DEBUG] _get_prompt_for_request called for user {request.user_id}")
        print(f"[DEBUG] custom_prompt_id: {request.custom_prompt_id}")
        print(f"[DEBUG] prompt_id: {getattr(request, 'prompt_id', None)}")
        
        # 暗号化データベースから直接取得（settings_managerを使用）
        from .user_settings import settings_manager
        try:
            # ユーザーの単一カスタムプロンプトを取得
            custom_prompt = settings_manager.get_custom_prompt(request.user_id)
            if custom_prompt:
                print(f"[DEBUG] Using user's custom prompt: {custom_prompt['name']}")
                return custom_prompt['prompt_text']
            else:
                print(f"[DEBUG] No custom prompt found for user")
                        
        except Exception as e:
            print(f"[DEBUG] Error getting custom prompt: {e}")
        
        # カスタムプロンプトがない場合、プロンプトIDが指定されている場合（NAVI.mdベース）
        if hasattr(request, 'prompt_id') and request.prompt_id:
            print(f"[DEBUG] Using NAVI.md prompt: {request.prompt_id}")
            return self.prompt_loader.get_prompt_text(request.prompt_id)
        
        # ユーザープロファイルがある場合、動的プロンプトを生成
        if self.user_profile_manager:
            profile = self.user_profile_manager.get_user_profile(request.user_id)
            if profile:
                print(f"[DEBUG] Using user profile prompt")
                return self.user_profile_manager.generate_prompt_from_profile(request.user_id)
        
        # デフォルトプロンプトをNAVI.mdから取得
        print(f"[DEBUG] Using default prompt: {self.default_prompt_id}")
        return self.prompt_loader.get_prompt_text(self.default_prompt_id)