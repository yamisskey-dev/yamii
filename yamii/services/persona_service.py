"""
ペルソナサービス - キャラクター設定の管理と自動分析
"""

import asyncio
import aiohttp
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from ..core.logging import get_logger, log_business_event, log_error
from ..core.exceptions import ExternalServiceError, ValidationError
from ..persona import (
    Persona,
    PersonaStore,
    PersonaAnalyzer,
    PersonaSourceType,
    PersonalityProfile,
    SpeechPattern,
    BackgroundStory,
    ResponseBehavior,
    get_persona_store,
    get_persona_analyzer,
)


class PersonaAnalysisService:
    """
    ペルソナ分析サービス

    テキストデータからLLMを使ってペルソナを自動分析・生成
    """

    def __init__(self, api_key: str, data_dir: str = "data"):
        self.api_key = api_key
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.store = get_persona_store(data_dir)
        self.analyzer = get_persona_analyzer()

        # Gemini API設定
        self.gemini_model = "gemini-2.0-flash-exp"
        self.gemini_api_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent"
        )

        self.logger = get_logger("persona_service")

    async def analyze_text_and_create_persona(
        self,
        text_data: str,
        persona_name: str,
        persona_id: Optional[str] = None,
        source_type: PersonaSourceType = PersonaSourceType.TEXT_ANALYSIS,
        created_by: Optional[str] = None,
        category: str = "custom",
        tags: Optional[List[str]] = None
    ) -> Persona:
        """
        テキストデータを分析してペルソナを作成

        Args:
            text_data: 分析対象のテキストデータ
            persona_name: ペルソナの名前
            persona_id: ペルソナID（省略時は自動生成）
            source_type: ソースタイプ
            created_by: 作成者ユーザーID
            category: カテゴリ
            tags: タグリスト

        Returns:
            Persona: 生成されたペルソナ
        """
        try:
            log_business_event(
                self.logger,
                "persona_analysis_started",
                persona_name=persona_name,
                text_length=len(text_data),
                source_type=source_type.value
            )

            # 分析プロンプトを生成
            analysis_prompt = self.analyzer.create_analysis_prompt(text_data)

            # LLMで分析を実行
            analysis_result_text = await self._call_llm(analysis_prompt)

            # 分析結果をパース
            analysis_result = self.analyzer.parse_analysis_result(analysis_result_text)

            if not analysis_result:
                raise ValidationError("分析結果のパースに失敗しました")

            # ペルソナIDを生成
            if not persona_id:
                persona_id = f"persona_{uuid.uuid4().hex[:8]}"

            # ペルソナを作成
            persona = self.analyzer.create_persona_from_analysis(
                analysis_result=analysis_result,
                persona_id=persona_id,
                persona_name=persona_name,
                source_type=source_type
            )

            # 追加情報を設定
            persona.created_by = created_by
            persona.category = category
            persona.tags = tags or []
            persona.source_data = f"text_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # ストアに保存
            self.store.add_persona(persona)

            log_business_event(
                self.logger,
                "persona_analysis_completed",
                persona_id=persona.id,
                persona_name=persona_name,
                traits_count=len(persona.personality.traits)
            )

            return persona

        except Exception as e:
            log_error(self.logger, e, {"persona_name": persona_name})
            raise

    async def analyze_from_file(
        self,
        file_path: str,
        persona_name: str,
        file_type: str = "auto",
        **kwargs
    ) -> Persona:
        """
        ファイルからテキストを読み込んでペルソナを分析

        Args:
            file_path: ファイルパス
            persona_name: ペルソナ名
            file_type: ファイルタイプ（auto/json/csv/txt）
            **kwargs: analyze_text_and_create_personaへの追加引数

        Returns:
            Persona: 生成されたペルソナ
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        # ファイルタイプの自動判定
        if file_type == "auto":
            file_type = path.suffix.lower().lstrip(".")

        # ファイルを読み込み
        if file_type == "json":
            text_data = self._load_json_file(path)
        elif file_type == "csv":
            text_data = self._load_csv_file(path)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                text_data = f.read()

        return await self.analyze_text_and_create_persona(
            text_data=text_data,
            persona_name=persona_name,
            source_type=PersonaSourceType.TEXT_ANALYSIS,
            **kwargs
        )

    def _load_json_file(self, path: Path) -> str:
        """JSONファイルからテキストを抽出"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        texts = []

        # Misskeyノート形式をサポート
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if "text" in item:
                        texts.append(item["text"])
                    elif "content" in item:
                        texts.append(item["content"])
                elif isinstance(item, str):
                    texts.append(item)
        elif isinstance(data, dict):
            if "notes" in data:
                for note in data["notes"]:
                    if "text" in note:
                        texts.append(note["text"])

        return "\n".join(filter(None, texts))

    def _load_csv_file(self, path: Path) -> str:
        """CSVファイルからテキストを抽出"""
        import csv
        texts = []

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "text" in row:
                    texts.append(row["text"])
                elif "content" in row:
                    texts.append(row["content"])

        return "\n".join(filter(None, texts))

    async def _call_llm(self, prompt: str) -> str:
        """LLMを呼び出す"""
        try:
            gemini_options = {
                'contents': [{
                    'role': 'user',
                    'parts': [{'text': prompt}]
                }],
                'generationConfig': {
                    'temperature': 0.7,
                    'maxOutputTokens': 4096
                }
            }

            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.gemini_api_url,
                    params={'key': self.api_key},
                    json=gemini_options
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ExternalServiceError(
                            f"Gemini API error: HTTP {response.status} - {error_text}",
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
                    return candidate['content']['parts'][0].get('text', '')

        except aiohttp.ClientError as e:
            raise ExternalServiceError(
                f"Network error calling Gemini API: {str(e)}",
                service_name="Gemini API"
            )

    # === ペルソナ管理API ===

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """ペルソナを取得"""
        return self.store.get_persona(persona_id)

    def get_persona_prompt(self, persona_id: str) -> str:
        """ペルソナのシステムプロンプトを取得"""
        return self.store.get_persona_prompt(persona_id)

    def list_personas(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        public_only: bool = False
    ) -> List[Persona]:
        """ペルソナ一覧を取得"""
        personas = self.store.list_personas(
            category=category,
            tags=tags,
            public_only=public_only
        )

        if user_id:
            # 公開ペルソナ + ユーザーが作成したペルソナ
            user_personas = self.store.get_user_personas(user_id)
            persona_ids = {p.id for p in personas}
            for up in user_personas:
                if up.id not in persona_ids:
                    personas.append(up)

        return personas

    def create_persona_manual(
        self,
        persona_id: str,
        name: str,
        description: str,
        created_by: Optional[str] = None,
        **kwargs
    ) -> Persona:
        """手動でペルソナを作成"""
        persona = Persona(
            id=persona_id,
            name=name,
            description=description,
            source_type=PersonaSourceType.MANUAL,
            created_by=created_by,
            **kwargs
        )
        self.store.add_persona(persona)
        return persona

    def update_persona(self, persona_id: str, **kwargs) -> bool:
        """ペルソナを更新"""
        return self.store.update_persona(persona_id, **kwargs)

    def delete_persona(self, persona_id: str, user_id: Optional[str] = None) -> bool:
        """ペルソナを削除"""
        persona = self.store.get_persona(persona_id)
        if not persona:
            return False

        # デフォルトペルソナは削除不可
        if persona.is_public and not persona.created_by:
            raise ValidationError("デフォルトペルソナは削除できません")

        # 所有権チェック
        if user_id and persona.created_by and persona.created_by != user_id:
            raise ValidationError("他のユーザーのペルソナは削除できません")

        return self.store.delete_persona(persona_id)

    def clone_persona(
        self,
        source_persona_id: str,
        new_name: str,
        created_by: Optional[str] = None
    ) -> Optional[Persona]:
        """ペルソナを複製"""
        new_id = f"persona_{uuid.uuid4().hex[:8]}"
        return self.store.clone_persona(
            source_persona_id=source_persona_id,
            new_id=new_id,
            new_name=new_name,
            created_by=created_by
        )

    def search_personas(self, query: str) -> List[Persona]:
        """ペルソナを検索"""
        return self.store.search_personas(query)

    # === カスタムプロンプト設定 ===

    def set_custom_prompt(self, persona_id: str, custom_prompt: str) -> bool:
        """カスタムプロンプトを設定"""
        return self.store.update_persona(persona_id, custom_prompt=custom_prompt)

    def clear_custom_prompt(self, persona_id: str) -> bool:
        """カスタムプロンプトをクリア"""
        return self.store.update_persona(persona_id, custom_prompt=None)

    # === ペルソナ設定の個別更新 ===

    def update_personality(
        self,
        persona_id: str,
        traits: Optional[List[str]] = None,
        values: Optional[List[str]] = None,
        communication_style: Optional[str] = None,
        **kwargs
    ) -> bool:
        """性格設定を更新"""
        persona = self.store.get_persona(persona_id)
        if not persona:
            return False

        if traits is not None:
            from ..persona import PersonalityTrait
            persona.personality.traits = [
                PersonalityTrait(t) for t in traits
                if t in [e.value for e in PersonalityTrait]
            ]
        if values is not None:
            persona.personality.values = values
        if communication_style is not None:
            from ..persona import CommunicationTone
            if communication_style in [e.value for e in CommunicationTone]:
                persona.personality.communication_style = CommunicationTone(communication_style)

        for key, value in kwargs.items():
            if hasattr(persona.personality, key):
                setattr(persona.personality, key, value)

        persona.updated_at = datetime.now()
        self.store._save_personas()
        return True

    def update_speech_pattern(
        self,
        persona_id: str,
        sentence_endings: Optional[List[str]] = None,
        favorite_phrases: Optional[List[str]] = None,
        honorific_level: Optional[str] = None,
        emoji_usage: Optional[str] = None,
        **kwargs
    ) -> bool:
        """発話パターンを更新"""
        persona = self.store.get_persona(persona_id)
        if not persona:
            return False

        if sentence_endings is not None:
            persona.speech_pattern.sentence_endings = sentence_endings
        if favorite_phrases is not None:
            persona.speech_pattern.favorite_phrases = favorite_phrases
        if honorific_level is not None:
            persona.speech_pattern.honorific_level = honorific_level
        if emoji_usage is not None:
            persona.speech_pattern.emoji_usage = emoji_usage

        for key, value in kwargs.items():
            if hasattr(persona.speech_pattern, key):
                setattr(persona.speech_pattern, key, value)

        persona.updated_at = datetime.now()
        self.store._save_personas()
        return True

    def update_background(
        self,
        persona_id: str,
        name: Optional[str] = None,
        occupation: Optional[str] = None,
        background: Optional[str] = None,
        motivation: Optional[str] = None,
        expertise: Optional[List[str]] = None,
        **kwargs
    ) -> bool:
        """背景ストーリーを更新"""
        persona = self.store.get_persona(persona_id)
        if not persona:
            return False

        if name is not None:
            persona.background.name = name
        if occupation is not None:
            persona.background.occupation = occupation
        if background is not None:
            persona.background.background = background
        if motivation is not None:
            persona.background.motivation = motivation
        if expertise is not None:
            persona.background.expertise = expertise

        for key, value in kwargs.items():
            if hasattr(persona.background, key):
                setattr(persona.background, key, value)

        persona.updated_at = datetime.now()
        self.store._save_personas()
        return True

    def update_behavior(
        self,
        persona_id: str,
        response_length: Optional[str] = None,
        advice_style: Optional[str] = None,
        crisis_response_mode: Optional[bool] = None,
        **kwargs
    ) -> bool:
        """応答行動を更新"""
        persona = self.store.get_persona(persona_id)
        if not persona:
            return False

        if response_length is not None:
            persona.behavior.response_length = response_length
        if advice_style is not None:
            persona.behavior.advice_style = advice_style
        if crisis_response_mode is not None:
            persona.behavior.crisis_response_mode = crisis_response_mode

        for key, value in kwargs.items():
            if hasattr(persona.behavior, key):
                setattr(persona.behavior, key, value)

        persona.updated_at = datetime.now()
        self.store._save_personas()
        return True

    # === エクスポート/インポート ===

    def export_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """ペルソナをエクスポート"""
        persona = self.store.get_persona(persona_id)
        if not persona:
            return None
        return persona.to_dict()

    def import_persona(
        self,
        persona_data: Dict[str, Any],
        new_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Persona:
        """ペルソナをインポート"""
        persona = Persona.from_dict(persona_data)

        if new_id:
            persona.id = new_id
        else:
            # IDが既に存在する場合は新しいIDを生成
            if self.store.get_persona(persona.id):
                persona.id = f"persona_{uuid.uuid4().hex[:8]}"

        persona.created_at = datetime.now()
        persona.updated_at = datetime.now()
        persona.created_by = created_by

        self.store.add_persona(persona)
        return persona


def create_persona_service(api_key: str, data_dir: str = "data") -> PersonaAnalysisService:
    """ペルソナサービスを作成するファクトリ関数"""
    return PersonaAnalysisService(api_key=api_key, data_dir=data_dir)
