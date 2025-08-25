"""
AI Chat Service - Gemini API Integration
yuiのaichat機能をPython FastAPIに移植
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

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AiChatRequest:
    """AIチャットリクエスト"""
    def __init__(self, question: str, prompt: str, api: str, key: str, 
                 from_mention: bool = True, friend_name: Optional[str] = None,
                 grounding: bool = False, history: Optional[List[Dict]] = None,
                 memory: Optional[Dict] = None):
        self.question = question
        self.prompt = prompt
        self.api = api
        self.key = key
        self.from_mention = from_mention
        self.friend_name = friend_name
        self.grounding = grounding
        self.history = history or []
        self.memory = memory

class Base64File:
    """Base64エンコードされたファイル"""
    def __init__(self, file_type: str, base64_data: str, url: Optional[str] = None):
        self.type = file_type
        self.base64 = base64_data
        self.url = url

class AiChatService:
    """AI Chat Service - Geminiとの通信を管理"""
    
    GEMINI_MODEL = "gemini-2.0-flash-exp"
    TIMEOUT_TIME = 30 * 60  # 30分
    
    def __init__(self):
        self.custom_emojis = set()  # カスタム絵文字のキャッシュ
        
    def is_youtube_url(self, url: str) -> bool:
        """YouTube URLかどうかを判定"""
        return (
            'www.youtube.com' in url or
            'm.youtube.com' in url or
            'youtu.be' in url
        )
    
    def normalize_youtube_url(self, url: str) -> str:
        """YouTube URLを正規化"""
        try:
            url_obj = urlparse(url)
            video_id = ''
            
            # youtu.beドメインの場合
            if 'youtu.be' in url_obj.netloc:
                video_id = url_obj.path.split('/')[1]
            # youtube.comドメインの場合
            elif 'youtube.com' in url_obj.netloc:
                query_params = parse_qs(url_obj.query)
                video_id = query_params.get('v', [''])[0]
            
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        except Exception as e:
            logger.error(f"YouTube URL解析エラー: {e}")
        
        return url
    
    def analyze_mood(self, message: str) -> str:
        """メッセージの感情を分析"""
        # Misskeyカスタム絵文字の感情分析
        emoji_sentiments = {
            # ポジティブ系
            ':smile:': 'happy', ':grin:': 'happy', ':laughing:': 'happy', ':joy:': 'happy',
            ':heart:': 'happy', ':heart_eyes:': 'happy', ':blush:': 'happy', ':wink:': 'happy',
            ':ok_hand:': 'happy', ':thumbsup:': 'happy', ':clap:': 'happy', ':tada:': 'happy',
            ':sparkles:': 'happy', ':star:': 'happy', ':rainbow:': 'happy', ':sunny:': 'happy',
            
            # ネガティブ系
            ':cry:': 'sad', ':sob:': 'sad', ':broken_heart:': 'sad', ':disappointed:': 'sad',
            ':rage:': 'angry', ':angry:': 'angry', ':punch:': 'angry', ':middle_finger:': 'angry',
            ':fearful:': 'anxious', ':worried:': 'anxious', ':cold_sweat:': 'anxious', ':sweat:': 'anxious',
            
            # その他
            ':thinking:': 'neutral', ':neutral_face:': 'neutral', ':expressionless:': 'neutral'
        }
        
        # 絵文字の感情をチェック
        for emoji, sentiment in emoji_sentiments.items():
            if emoji in message:
                return sentiment
        
        # 高度なキーワード分析
        sentiment_keywords = {
            'happy': [
                '嬉しい', '楽しい', '幸せ', '最高', '素晴らしい', '感動', '感激', '興奮',
                'ワクワク', 'ドキドキ', 'やったー', 'よっしゃ', 'やった', '成功', '達成',
                '感謝', 'ありがとう', '愛してる', '大好き', '完璧', '理想'
            ],
            'sad': [
                '悲しい', '辛い', '苦しい', '切ない', '寂しい', '孤独', '絶望', '失望',
                '落ち込む', '凹む', 'しんどい', '疲れた', '死にたい', '消えたい', '終わり',
                '諦める', '無理', 'ダメ', '失敗', '後悔', '申し訳ない', 'ごめん'
            ],
            'angry': [
                '怒', 'イライラ', '腹立つ', 'ムカつく', 'キレる', '許せない', '最悪',
                'クソ', 'うざい', 'うるさい', 'しつこい', 'めんどくさい', 'やだ',
                '嫌い', '大嫌い', '消えろ', '死ね', '殺す', 'ぶっ殺す', '殴る'
            ],
            'anxious': [
                '不安', '心配', '怖い', '恐い', '緊張', 'ドキドキ', 'ハラハラ',
                '焦る', '急ぐ', '間に合わない', 'やばい', 'まずい', '危険',
                '大変', '困る', 'どうしよう', '助けて', '助け', '救い'
            ]
        }
        
        # 感情スコアを計算
        scores = {'happy': 0, 'sad': 0, 'angry': 0, 'anxious': 0, 'neutral': 0}
        
        for sentiment, keywords in sentiment_keywords.items():
            for keyword in keywords:
                count = len(re.findall(keyword, message))
                scores[sentiment] += count * 2
        
        # 否定語と強調語の考慮
        negation_words = ['ない', 'ません', 'じゃない', 'ではない', '違う', 'ちがう']
        emphasis_words = ['すごく', 'とても', 'めちゃくちゃ', '超', '激', '死ぬほど', 'マジで']
        
        has_negation = any(word in message for word in negation_words)
        has_emphasis = any(word in message for word in emphasis_words)
        
        if has_negation:
            scores['happy'] = max(0, scores['happy'] - 2)
            scores['sad'] += 1
            scores['anxious'] += 1
        
        if has_emphasis:
            for key in scores:
                if key != 'neutral':
                    scores[key] *= 1.5
        
        # 最高スコアの感情を返す
        max_score = max(scores.values())
        if max_score == 0:
            return 'neutral'
        
        for sentiment, score in scores.items():
            if score == max_score:
                return sentiment
        
        return 'neutral'
    
    def calculate_importance(self, message: str) -> int:
        """メッセージの重要度を計算（0-10）"""
        importance = 5  # デフォルト重要度
        
        # 感情分析を利用
        mood = self.analyze_mood(message)
        if mood == 'happy':
            importance += 2
        elif mood == 'sad':
            importance += 3
        elif mood == 'angry':
            importance += 3
        elif mood == 'anxious':
            importance += 2
        
        # 質問は重要
        if '？' in message or '?' in message:
            importance += 2
        
        # 個人的な内容は重要
        if any(word in message for word in ['私', '僕', '俺', '自分']):
            importance += 2
        
        # 緊急度の高い内容
        if any(word in message for word in ['急いで', 'すぐ', '今すぐ', '助けて']):
            importance += 3
        
        # 長いメッセージは重要
        if len(message) > 50:
            importance += 1
        if len(message) > 100:
            importance += 1
        
        # 絵文字の使用
        emoji_count = len(re.findall(r':[a-zA-Z_]+:', message))
        if emoji_count > 0:
            importance += min(emoji_count, 2)
        
        # 強調表現
        if '！' in message or '!' in message:
            importance += 1
        if any(word in message for word in ['すごく', 'とても', 'めちゃくちゃ']):
            importance += 1
        
        return min(importance, 10)
    
    def extract_current_topic(self, message: str) -> str:
        """現在の話題を抽出"""
        topic_keywords = {
            'weather': ['天気', '雨', '晴れ', '曇り', '雪', '台風', '気温', '暑い', '寒い', '湿度'],
            'work': ['仕事', '会社', '職場', '上司', '同僚', '会議', '残業', '給料', '転職', '就職'],
            'hobby': ['趣味', '好き', '興味', 'ゲーム', '映画', '音楽', '読書', 'スポーツ', '料理', '旅行'],
            'family': ['家族', '親', '子供', '兄弟', '姉妹', '夫', '妻', '結婚', '離婚', '育児'],
            'friends': ['友達', '友人', '仲間', '彼氏', '彼女', '恋人', 'デート', '飲み会', 'サークル'],
            'food': ['食べ物', '料理', 'レストラン', 'カフェ', 'お酒', '甘い', '辛い', '美味しい', 'まずい'],
            'technology': ['パソコン', 'スマホ', 'アプリ', 'プログラミング', 'AI', '機械学習', 'インターネット'],
            'health': ['健康', '病気', '病院', '薬', 'ダイエット', '運動', '睡眠', 'ストレス', '疲れ'],
            'money': ['お金', '貯金', '投資', '株', '保険', 'ローン', '節約', '浪費', '給料', '副業'],
            'education': ['学校', '大学', '勉強', '試験', 'テスト', '宿題', '研究', '論文', '卒業', '入学']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in message for keyword in keywords):
                return topic
        
        return 'general'
    
    def manage_human_like_memory(self, memory: Optional[Dict], new_conversation: Dict) -> Dict:
        """人間らしい記憶管理"""
        if not memory:
            memory = {
                'conversations': [],
                'userProfile': {
                    'name': '',
                    'interests': [],
                    'conversationStyle': 'casual',
                    'lastInteraction': datetime.now().timestamp()
                },
                'conversationContext': {
                    'currentTopic': '',
                    'mood': 'neutral',
                    'relationshipLevel': 5
                }
            }
        
        # 新しい会話を追加
        memory['conversations'].append({
            'id': new_conversation['id'],
            'timestamp': datetime.now().timestamp(),
            'userMessage': new_conversation['userMessage'],
            'aiResponse': new_conversation['aiResponse'],
            'context': self.analyze_conversation_context(new_conversation['userMessage']),
            'importance': self.calculate_importance(new_conversation['userMessage']),
            'isActive': True
        })
        
        # 記憶の整理
        memory['conversations'] = self.organize_memories(memory['conversations'])
        
        # ユーザープロファイルの更新
        memory['userProfile']['lastInteraction'] = datetime.now().timestamp()
        
        # 会話コンテキストの更新
        memory['conversationContext']['currentTopic'] = self.extract_current_topic(
            new_conversation['userMessage']
        )
        memory['conversationContext']['mood'] = self.analyze_mood(new_conversation['userMessage'])
        
        return memory
    
    def analyze_conversation_context(self, message: str) -> str:
        """会話の文脈を分析"""
        context = []
        
        # 感情分析
        mood = self.analyze_mood(message)
        if mood == 'happy':
            context.append('positive_emotion')
        elif mood in ['sad', 'angry', 'anxious']:
            context.append('negative_emotion')
        
        # 話題分析
        topic = self.extract_current_topic(message)
        if topic != 'general':
            context.append(topic)
        
        # 会話の種類分析
        if '？' in message or '?' in message:
            context.append('question')
        if '！' in message or '!' in message:
            context.append('exclamation')
        if '...' in message or '…' in message:
            context.append('hesitation')
        
        return ','.join(context) if context else 'general'
    
    def organize_memories(self, conversations: List[Dict]) -> List[Dict]:
        """記憶を整理（重要度と時間に基づく）"""
        now = datetime.now().timestamp()
        one_day = 24 * 60 * 60
        one_week = 7 * one_day
        
        # 重要度と時間に基づいてアクティブ状態を更新
        for conv in conversations:
            age = now - conv['timestamp']
            
            # 1週間以上前で重要度が低いものは非アクティブ
            if age > one_week and conv['importance'] < 6:
                conv['isActive'] = False
            
            # 1日以上前で重要度が非常に低いものは非アクティブ
            if age > one_day and conv['importance'] < 4:
                conv['isActive'] = False
        
        # アクティブな記憶を最大20個まで保持
        active_memories = [c for c in conversations if c['isActive']]
        if len(active_memories) > 20:
            # 重要度が低いものから削除
            active_memories.sort(key=lambda x: x['importance'])
            for m in active_memories[:len(active_memories) - 20]:
                m['isActive'] = False
        
        return conversations
    
    def generate_human_like_context(self, memory: Dict) -> str:
        """人間らしい文脈を生成"""
        if not memory or not memory.get('conversations'):
            return ''
        
        active_memories = [c for c in memory['conversations'] if c.get('isActive', True)]
        if not active_memories:
            return ''
        
        # 最近の会話（最大5個）を自然な文脈として生成
        recent_memories = sorted(active_memories, key=lambda x: x['timestamp'], reverse=True)[:5]
        
        context = ''
        if memory.get('userProfile', {}).get('name'):
            context += f"{memory['userProfile']['name']}さんとの過去の会話を参考にしてください。\n\n"
        
        context += '過去の会話の流れ：\n'
        for i, mem in enumerate(recent_memories):
            date = datetime.fromtimestamp(mem['timestamp']).strftime('%Y-%m-%d')
            context += f"{i + 1}. [{date}] {mem['userMessage']} → {mem['aiResponse']}\n"
        
        current_topic = memory.get('conversationContext', {}).get('currentTopic')
        if current_topic and current_topic != 'general':
            context += f"\n現在の話題: {current_topic}\n"
        
        mood = memory.get('conversationContext', {}).get('mood')
        if mood and mood != 'neutral':
            mood_labels = {
                'happy': '嬉しい',
                'sad': '悲しい', 
                'angry': '怒っている',
                'anxious': '不安・心配',
                'neutral': '普通'
            }
            context += f"相手の気分: {mood_labels.get(mood, '普通')}\n"
        
        return context
    
    async def generate_text_by_gemini(self, ai_chat: AiChatRequest, files: List[Base64File], is_chat: bool) -> Optional[str]:
        """Gemini APIを使用してテキストを生成"""
        logger.info('Generate Text By Gemini...')
        
        # 現在時刻を取得
        now = datetime.now().strftime('%Y年%m月%d日 %H:%M')
        
        # システム命令を構築
        system_instruction_text = (
            ai_chat.prompt +
            f'また、現在日時は{now}であり、これは回答の参考にし、絶対に時刻を聞かれるまで時刻情報は提供しないこと。' +
            'なお、他の日時は無効とすること。' +
            '絵文字については、Misskeyカスタム絵文字（:smile:, :heart:, :cry:, :angry:, :thinking:など）を使用してください。標準絵文字は使用しないでください。'
        )
        
        if ai_chat.friend_name:
            system_instruction_text += f'なお、会話相手の名前は{ai_chat.friend_name}とする。'
        
        # ランダムトーク機能の場合の配慮
        if not ai_chat.from_mention:
            system_instruction_text += (
                'これらのメッセージは、あなたに対するメッセージではないことを留意し、返答すること'
                '（会話相手は突然話しかけられた認識している）。'
            )
        
        # 感情的な質問や相談の場合はグラウンディングを無効化
        emotional_keywords = [
            '辛い', '苦しい', '悲しい', '寂しい', '死にたい', '消えたい', '生きる意味', '希望がない',
            'かまって', '愛して', '好き', '嫌い', '怒り', '不安', '怖い', '心配',
            '疲れた', '眠い', 'だるい', 'やる気がない', '無価値', 'ダメ', '失敗',
            '助けて', 'どうすれば', 'どうしたら', '困ってる', '悩んでる'
        ]
        
        is_emotional_question = any(keyword in ai_chat.question for keyword in emotional_keywords)
        if is_emotional_question:
            logger.info('Emotional question detected, disabling grounding')
            ai_chat.grounding = False
        
        # グラウンディングについての追記
        if ai_chat.grounding:
            system_instruction_text += '返答のルール2:Google search with grounding.'
        
        # URLから情報を取得
        youtube_urls = []
        has_youtube_url = False
        
        url_pattern = re.compile(r'(https?://[a-zA-Z0-9!?/+_~=:;.,*&@#$%\'-]+)')
        urls = url_pattern.findall(ai_chat.question)
        
        for url in urls:
            if self.is_youtube_url(url):
                logger.info(f'YouTube URL detected: {url}')
                normalized_url = self.normalize_youtube_url(url)
                logger.info(f'Normalized YouTube URL: {normalized_url}')
                youtube_urls.append(normalized_url)
                has_youtube_url = True
                continue
            
            # 他のURLの処理は省略（必要に応じて実装）
        
        # Geminiリクエストの構築
        contents = []
        
        # 履歴の処理
        if ai_chat.history:
            for hist in ai_chat.history:
                contents.append({
                    'role': hist['role'],
                    'parts': [{'text': hist['content']}]
                })
        
        # 人間らしい記憶システムを使用
        if ai_chat.memory:
            human_context = self.generate_human_like_context(ai_chat.memory)
            if human_context:
                system_instruction_text += '\n\n' + human_context
                logger.info(f'[aichat] 人間らしい文脈を追加: {len(human_context)}文字')
        
        system_instruction = {
            'role': 'system',
            'parts': [{'text': system_instruction_text}]
        }
        
        # ユーザーメッセージの構築
        parts = [{'text': ai_chat.question}]
        
        # YouTubeのURLをfileDataとして追加
        for youtube_url in youtube_urls:
            parts.append({
                'fileData': {
                    'mimeType': 'video/mp4',
                    'fileUri': youtube_url
                }
            })
        
        # 画像ファイルを追加
        for file in files:
            parts.append({
                'inlineData': {
                    'mimeType': file.type,
                    'data': file.base64
                }
            })
        
        contents.append({'role': 'user', 'parts': parts})
        
        # Geminiリクエストオプション
        gemini_options = {
            'contents': contents,
            'systemInstruction': system_instruction
        }
        
        # YouTube URLがない場合のみグラウンディングを有効化
        if ai_chat.grounding and not has_youtube_url:
            gemini_options['tools'] = [{'google_search': {}}]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ai_chat.api,
                    params={'key': ai_chat.key},
                    json=gemini_options
                ) as response:
                    response_data = await response.json()
                    logger.info(f'Gemini response: {json.dumps(response_data, ensure_ascii=False)}')
                    
                    if 'candidates' not in response_data:
                        logger.error('No candidates in Gemini response')
                        return None
                    
                    candidates = response_data['candidates']
                    if not candidates:
                        logger.error('Empty candidates in Gemini response')
                        return None
                    
                    candidate = candidates[0]
                    if 'content' not in candidate:
                        logger.error('No content in candidate')
                        return None
                    
                    content = candidate['content']
                    if 'parts' not in content:
                        logger.error('No parts in content')
                        return None
                    
                    # テキストを結合
                    response_text = ''
                    for part in content['parts']:
                        if 'text' in part:
                            response_text += part['text']
                    
                    # グラウンディングメタデータを処理
                    grounding_metadata = ''
                    if 'groundingMetadata' in candidate:
                        metadata = candidate['groundingMetadata']
                        
                        # 参考サイト情報
                        if 'groundingChunks' in metadata:
                            chunks = metadata['groundingChunks'][:3]  # 最大3つまで
                            for i, chunk in enumerate(chunks):
                                if 'web' in chunk and 'uri' in chunk['web'] and 'title' in chunk['web']:
                                    grounding_metadata += f"参考({i + 1}): [{chunk['web']['title']}]({chunk['web']['uri']})\n"
                        
                        # 検索ワード
                        if not is_chat and 'webSearchQueries' in metadata:
                            queries = metadata['webSearchQueries']
                            if queries:
                                grounding_metadata += f"検索ワード: {', '.join(queries)}\n"
                    
                    response_text += grounding_metadata
                    return response_text
                    
        except Exception as e:
            logger.error(f'Error calling Gemini API: {e}')
            return None