"""
改良されたカウンセリングサービス
依存性注入とクリーンアーキテクチャを採用
"""

import asyncio
import aiohttp
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..core.logging import get_logger, log_business_event, log_error
from ..core.exceptions import ExternalServiceError, CounselingError, ValidationError
from .emotion_service import EmotionAnalysisService, EmotionType
from ..memory import MemorySystem
from ..user_profile import UserProfileManager
from ..user_settings import UserSettingsManager
from ..core.prompt_store import PromptStore, get_prompt_store
from ..core.secure_prompt_store import SecurePromptStore, get_secure_prompt_store
from ..core.encryption import get_e2ee_crypto, get_key_manager


@dataclass
class CounselingRequest:
    """人生相談リクエスト"""
    message: str
    user_id: str
    session_id: Optional[str] = None
    user_name: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    custom_prompt_id: Optional[str] = None
    prompt_id: Optional[str] = None

    def __post_init__(self):
        """バリデーション"""
        if not self.message or not self.message.strip():
            raise ValidationError("メッセージは必須です", field="message")
        if not self.user_id or not self.user_id.strip():
            raise ValidationError("ユーザーIDは必須です", field="user_id")
        
        # デフォルト値の設定
        if self.context is None:
            self.context = {}
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())


@dataclass
class CounselingResponse:
    """人生相談レスポンス"""
    response: str
    session_id: str
    emotion_analysis: Dict[str, Any]
    advice_type: str
    follow_up_questions: List[str]
    
    @property
    def is_crisis(self) -> bool:
        """危機状況かどうか"""
        return self.emotion_analysis.get('is_crisis', False)


class AdviceTypeClassifier:
    """アドバイスタイプ分類器"""
    
    def __init__(self):
        self.logger = get_logger("advice_classifier")
        
        # カテゴリキーワード
        self._category_keywords = {
            'crisis_support': [
                '死にたい', '消えたい', '自殺', '生きる意味', '限界',
                '自分を傷つけ', '終わりにしたい'
            ],
            'mental_health': [
                'うつ', 'うつ病', '精神的', 'メンタル', '心療内科',
                '精神科', 'カウンセラー', '薬', '治療'
            ],
            'relationship': [
                '恋愛', '恋人', '彼氏', '彼女', '片思い', '失恋',
                'デート', '結婚', '離婚', 'パートナー'
            ],
            'career': [
                '仕事', '職場', '転職', '就職', '会社', '上司',
                '同僚', '残業', '給料', 'キャリア', '昇進'
            ],
            'family': [
                '家族', '親', '父', '母', '兄弟', '姉妹',
                '子供', '育児', '介護', '実家'
            ],
            'friendship': [
                '友達', '友人', '仲間', '人間関係', 'サークル',
                '飲み会', '付き合い'
            ],
            'education': [
                '勉強', '学校', '大学', '受験', 'テスト',
                '試験', '宿題', '成績', '進路'
            ],
            'health': [
                '健康', '病気', '体調', '病院', '医者',
                '症状', '治療', '診察'
            ]
        }
    
    def classify(self, message: str, emotion_type: EmotionType) -> str:
        """メッセージと感情からアドバイスタイプを分類"""
        message_lower = message.lower()
        
        # 危機的状況の優先判定
        if emotion_type == EmotionType.DEPRESSION:
            return 'crisis_support'
        
        for crisis_keyword in self._category_keywords['crisis_support']:
            if crisis_keyword in message_lower:
                return 'crisis_support'
        
        # その他のカテゴリ判定
        for category, keywords in self._category_keywords.items():
            if category == 'crisis_support':
                continue
            
            matches = sum(1 for keyword in keywords if keyword in message_lower)
            if matches > 0:
                self.logger.info(f"Classified as {category} (matches: {matches})")
                return category
        
        return 'general_support'


class FollowUpGenerator:
    """フォローアップ質問生成器"""
    
    def __init__(self):
        self._follow_up_templates = {
            'crisis_support': [
                '今、誰か信頼できる人はそばにいますか？',
                '専門のカウンセラーや医師に相談することを考えてみませんか？',
                'あなたの安全が最も重要です。いのちの電話（0570-783-556）もご活用ください。'
            ],
            'mental_health': [
                'この状況はいつ頃から続いていますか？',
                '今まで試してみた対処法はありますか？',
                '信頼できる人に相談したことはありますか？'
            ],
            'relationship': [
                'お相手とはどのくらいお付き合いされているのですか？',
                'この問題について話し合ったことはありますか？',
                'あなた自身はどのような関係を望んでいますか？'
            ],
            'career': [
                '現在の職場環境についてもう少し教えてください',
                '理想的な働き方はどのようなものですか？',
                'キャリアプランについて考えたことはありますか？'
            ],
            'family': [
                'ご家族との関係について詳しく教えてください',
                'この状況がどのくらい続いていますか？',
                '家族以外で相談できる人はいますか？'
            ],
            'general_support': [
                'このことで一番困っていることは何ですか？',
                '理想的な状況はどのようなものでしょうか？',
                'これまでに似たような経験はありますか？'
            ]
        }
    
    def generate(self, advice_type: str, emotion_type: EmotionType) -> List[str]:
        """フォローアップ質問を生成"""
        templates = self._follow_up_templates.get(advice_type, 
                                                 self._follow_up_templates['general_support'])
        
        # 危機的状況では質問を制限
        if advice_type == 'crisis_support':
            return templates[:2]  # 安全確認に集中
        
        return templates[:2]  # 通常は2つまで


class CounselingService:
    """改良されたカウンセリングサービス"""
    
    def __init__(self, api_key: str, memory_system: MemorySystem,
                 user_profile_manager: UserProfileManager,
                 settings_manager: UserSettingsManager,
                 secure_prompt_store: SecurePromptStore = None):
        self.api_key = api_key
        self.memory_system = memory_system
        self.user_profile_manager = user_profile_manager
        self.settings_manager = settings_manager
        self.secure_prompt_store = secure_prompt_store
        self.e2ee_crypto = get_e2ee_crypto()
        self.key_manager = get_key_manager()
        
        # サービス依存関係
        self.emotion_service = EmotionAnalysisService()
        self.advice_classifier = AdviceTypeClassifier()
        self.follow_up_generator = FollowUpGenerator()
        
        # API設定
        self.gemini_model = "gemini-2.0-flash-exp"
        self.gemini_api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent"
        )
        
        self.logger = get_logger("counseling_service")
    
    async def generate_counseling_response(self, request: CounselingRequest) -> CounselingResponse:
        """人生相談レスポンスを生成"""
        try:
            log_business_event(
                self.logger, 
                "counseling_request_received",
                user_id=request.user_id,
                session_id=request.session_id,
                message_length=len(request.message)
            )
            
            # 1. 感情分析
            emotion_analysis = self.emotion_service.analyze_emotion(request.message)
            
            # 2. アドバイスタイプ分類
            advice_type = self.advice_classifier.classify(
                request.message, emotion_analysis.primary_emotion
            )
            
            # 3. プロンプト取得
            system_prompt = await self._get_system_prompt(request, emotion_analysis, advice_type)
            
            # 4. AI応答生成
            ai_response = await self._generate_ai_response(request, system_prompt)
            
            # 5. フォローアップ質問生成
            follow_up_questions = self.follow_up_generator.generate(
                advice_type, emotion_analysis.primary_emotion
            )
            
            # 6. メモリに保存
            self.memory_system.add_conversation(
                user_id=request.user_id,
                user_message=request.message,
                ai_response=ai_response,
                importance=emotion_analysis.intensity,
                context=advice_type
            )
            
            response = CounselingResponse(
                response=ai_response,
                session_id=request.session_id,
                emotion_analysis=emotion_analysis.to_dict(),
                advice_type=advice_type,
                follow_up_questions=follow_up_questions
            )
            
            log_business_event(
                self.logger,
                "counseling_response_generated",
                user_id=request.user_id,
                session_id=request.session_id,
                advice_type=advice_type,
                primary_emotion=emotion_analysis.primary_emotion.value,
                is_crisis=emotion_analysis.is_crisis
            )
            
            return response
            
        except Exception as e:
            log_error(self.logger, e, {
                "user_id": request.user_id,
                "session_id": request.session_id
            })
            
            # フォールバック応答
            return await self._create_fallback_response(request, str(e))
    
    async def _get_system_prompt(self, request: CounselingRequest, 
                               emotion_analysis, advice_type: str) -> str:
        """システムプロンプトを構築"""
        try:
            # カスタムプロンプトの取得を試行
            custom_prompt = self.settings_manager.get_custom_prompt(request.user_id)
            if custom_prompt:
                base_prompt = custom_prompt['prompt_text']
                self.logger.info(f"Using custom prompt for user {request.user_id}")
            
            # 指定プロンプトIDからのE2EE取得
            elif request.prompt_id:
                base_prompt = await self._get_encrypted_prompt(request.user_id, request.prompt_id)
                self.logger.info(f"Using specified encrypted prompt: {request.prompt_id}")
            
            # ユーザープロファイルからの動的プロンプト
            else:
                profile = self.user_profile_manager.get_user_profile(request.user_id)
                if profile:
                    base_prompt = self.user_profile_manager.generate_prompt_from_profile(
                        request.user_id
                    )
                    self.logger.info(f"Using profile-based prompt for user {request.user_id}")
                else:
                    base_prompt = await self._get_encrypted_prompt(request.user_id, "default_counselor")
                    self.logger.info("Using default encrypted counselor prompt")
            
        except Exception as e:
            self.logger.warning(f"Failed to get encrypted prompt: {e}, using default")
            base_prompt = await self._get_encrypted_prompt(request.user_id, "default_counselor")
        
        # 現在時刻と文脈情報を追加
        now = datetime.now().strftime('%Y年%m月%d日 %H:%M')
        context_info = f"""
現在日時: {now}
相談者: {request.user_name or request.user_id}
感情分析結果: {emotion_analysis.primary_emotion.value}（強度: {emotion_analysis.intensity}/10）
相談タイプ: {advice_type}
信頼度: {emotion_analysis.confidence:.2f}

以下の点を考慮して回答してください:
- 相談者の感情に共感し、受容的な態度を示す
- 具体的で実践的なアドバイスを提供する
- 必要に応じて専門機関への相談を提案する
- 希望と励ましのメッセージを含める
"""
        
        # 危機的状況の特別指示
        if emotion_analysis.is_crisis:
            context_info += """
⚠️ 重要: これは危機的状況の可能性があります。
- 専門的な支援機関への相談を強く推奨する
- いのちの電話（0570-783-556）などの情報を提供する
- 「あなたは一人じゃない」というメッセージを伝える
- 安全の確保を最優先とする
"""
        
        return f"{base_prompt}\n\n{context_info}"
    
    async def _generate_ai_response(self, request: CounselingRequest, 
                                  system_prompt: str) -> str:
        """AIからの応答を生成"""
        try:
            gemini_options = {
                'contents': [{
                    'role': 'user',
                    'parts': [{'text': request.message}]
                }],
                'systemInstruction': {
                    'role': 'system',
                    'parts': [{'text': system_prompt}]
                }
            }
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.gemini_api_url,
                    params={'key': self.api_key},
                    json=gemini_options
                ) as response:
                    if response.status != 200:
                        raise ExternalServiceError(
                            f"Gemini API error: HTTP {response.status}",
                            service_name="Gemini API",
                            status_code=response.status
                        )
                    
                    response_data = await response.json()
                    
                    if 'candidates' not in response_data or not response_data['candidates']:
                        raise ExternalServiceError(
                            "No candidates in Gemini response",
                            service_name="Gemini API"
                        )
                    
                    candidate = response_data['candidates'][0]
                    if 'content' not in candidate or 'parts' not in candidate['content']:
                        raise ExternalServiceError(
                            "Invalid response structure from Gemini API",
                            service_name="Gemini API"
                        )
                    
                    response_text = candidate['content']['parts'][0].get('text', '')
                    
                    if not response_text.strip():
                        raise ExternalServiceError(
                            "Empty response from Gemini API",
                            service_name="Gemini API"
                        )
                    
                    return response_text
                    
        except aiohttp.ClientError as e:
            raise ExternalServiceError(
                f"Network error calling Gemini API: {str(e)}",
                service_name="Gemini API"
            )
        except Exception as e:
            if isinstance(e, ExternalServiceError):
                raise
            raise ExternalServiceError(
                f"Unexpected error calling Gemini API: {str(e)}",
                service_name="Gemini API"
            )
    
    async def _create_fallback_response(self, request: CounselingRequest, 
                                      error_msg: str) -> CounselingResponse:
        """エラー時のフォールバック応答"""
        fallback_message = (
            "申し訳ありません。今少し調子が悪いようです。"
            "時間を置いてもう一度お試しいただくか、"
            "信頼できる方に直接相談することをお勧めします。"
            "あなたは一人ではありません。"
        )
        
        return CounselingResponse(
            response=fallback_message,
            session_id=request.session_id or str(uuid.uuid4()),
            emotion_analysis={
                'primary_emotion': 'neutral',
                'intensity': 0,
                'is_crisis': False,
                'all_emotions': {},
                'confidence': 0.0
            },
            advice_type='general_support',
            follow_up_questions=['他に何かお手伝いできることはありますか？']
        )
    async def _get_encrypted_prompt(self, user_id: str, prompt_id: str) -> str:
        """
        E2EE暗号化プロンプトを取得・復号
        
        Args:
            user_id: ユーザーID
            prompt_id: プロンプトID
            
        Returns:
            str: 復号されたプロンプトテキスト
        """
        try:
            if not self.secure_prompt_store:
                self.secure_prompt_store = await get_secure_prompt_store()
            
            # ユーザーのキーペアを取得
            keys = self.key_manager.load_keys(user_id)
            if not keys:
                # キーが存在しない場合は生成
                public_key_b64, private_key_b64 = self.key_manager.generate_and_save_keys(user_id)
                private_key = self.e2ee_crypto.key_from_base64(private_key_b64)
                
                # デフォルトプロンプトを作成
                await self._ensure_default_prompts(user_id)
            else:
                _, private_key_b64 = keys
                private_key = self.e2ee_crypto.key_from_base64(private_key_b64)
            
            # 暗号化プロンプトを取得・復号
            decrypted_json = await self.secure_prompt_store.get_prompt(user_id, prompt_id, private_key)
            
            if decrypted_json:
                import json
                prompt_data = json.loads(decrypted_json)
                return prompt_data.get('prompt_text', '')
            
            # フォールバック: デフォルトプロンプトテキスト
            return """あなたは経験豊富で共感力の高い人生相談カウンセラーです。
相談者の気持ちに寄り添い、実践的で心に響くアドバイスを提供してください。

対応方針:
1. まず相談者の感情を理解し、共感を示す
2. 問題の本質を見極める
3. 具体的で実行可能な解決策を提案する
4. 相談者を励まし、前向きな気持ちになれるよう支援する
5. 必要に応じて専門機関への相談も提案する

絵文字は控えめに使用し、温かみのある文章を心がけてください。
深刻な問題（自殺願望など）の場合は、専門機関への相談を強く推奨してください。"""
            
        except Exception as e:
            self.logger.error(f"E2EE プロンプト取得エラー: {e}")
            # フォールバック
            return """あなたは人生相談に対応するAIアシスタントです。
相談者の気持ちに寄り添い、建設的なアドバイスを提供してください。"""
    
    async def _ensure_default_prompts(self, user_id: str) -> None:
        """
        ユーザーのデフォルトプロンプトが存在することを確認
        
        Args:
            user_id: ユーザーID
        """
        try:
            # ユーザーの公開鍵を取得
            keys = self.key_manager.load_keys(user_id)
            if keys:
                public_key_b64, _ = keys
                public_key = self.e2ee_crypto.key_from_base64(public_key_b64)
                
                # デフォルトプロンプトを作成
                default_prompt = {
                    "id": "default_counselor",
                    "title": "人生相談カウンセラー",
                    "description": "標準的なカウンセリング対応",
                    "prompt_text": """あなたは経験豊富で共感力の高い人生相談カウンセラーです。
相談者の気持ちに寄り添い、実践的で心に響くアドバイスを提供してください。

対応方針:
1. まず相談者の感情を理解し、共感を示す
2. 問題の本質を見極める
3. 具体的で実行可能な解決策を提案する
4. 相談者を励まし、前向きな気持ちになれるよう支援する
5. 必要に応じて専門機関への相談も提案する

絵文字は控えめに使用し、温かみのある文章を心がけてください。
深刻な問題（自殺願望など）の場合は、専門機関への相談を強く推奨してください。""",
                    "tags": ["カウンセラー", "標準", "人生相談"]
                }
                
                await self.secure_prompt_store.store_prompt(
                    user_id=user_id,
                    prompt_data=default_prompt,
                    public_key=public_key,
                    title=default_prompt["title"],
                    description=default_prompt["description"]
                )
                
                self.logger.info(f"デフォルトプロンプトを作成: user={user_id}")
                
        except Exception as e:
            self.logger.error(f"デフォルトプロンプト作成エラー: {e}")
