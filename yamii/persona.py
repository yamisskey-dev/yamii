"""
ペルソナシステム - 柔軟なキャラクター設定と自動ペルソナ分析機能

特徴:
- テキストデータからの自動ペルソナ分析（LLM使用）
- 手動でのペルソナ定義
- 複数のペルソナソース対応（SNS投稿、チャット履歴、手動入力など）
- ペルソナのテンプレートと継承
- 対話スタイルの詳細設定
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class PersonaSourceType(Enum):
    """ペルソナソースタイプ"""
    MANUAL = "manual"           # 手動入力
    TEXT_ANALYSIS = "text_analysis"  # テキスト分析から
    SNS_POSTS = "sns_posts"     # SNS投稿から
    CHAT_HISTORY = "chat_history"  # チャット履歴から
    TEMPLATE = "template"       # テンプレートから
    HYBRID = "hybrid"           # 複合


class CommunicationTone(Enum):
    """コミュニケーショントーン"""
    FORMAL = "formal"           # フォーマル
    CASUAL = "casual"           # カジュアル
    FRIENDLY = "friendly"       # フレンドリー
    PROFESSIONAL = "professional"  # プロフェッショナル
    PLAYFUL = "playful"         # 遊び心がある
    EMPATHETIC = "empathetic"   # 共感的
    ASSERTIVE = "assertive"     # 断定的
    GENTLE = "gentle"           # 優しい


class PersonalityTrait(Enum):
    """性格特性"""
    EXTROVERT = "extrovert"     # 外向的
    INTROVERT = "introvert"     # 内向的
    ANALYTICAL = "analytical"   # 分析的
    CREATIVE = "creative"       # 創造的
    PRACTICAL = "practical"     # 実践的
    IDEALISTIC = "idealistic"   # 理想主義
    OPTIMISTIC = "optimistic"   # 楽観的
    REALISTIC = "realistic"     # 現実的
    SUPPORTIVE = "supportive"   # 支持的
    CHALLENGING = "challenging" # 挑戦的


@dataclass
class SpeechPattern:
    """発話パターン"""
    sentence_endings: List[str] = field(default_factory=list)  # 文末表現（例：「〜だよ」「〜です」）
    favorite_phrases: List[str] = field(default_factory=list)  # 口癖
    interjections: List[str] = field(default_factory=list)     # 感嘆詞
    honorific_level: str = "normal"  # 敬語レベル（casual/normal/polite/very_polite）
    emoji_usage: str = "none"        # 絵文字使用（none/minimal/moderate/frequent）
    punctuation_style: str = "normal"  # 句読点スタイル

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sentence_endings": self.sentence_endings,
            "favorite_phrases": self.favorite_phrases,
            "interjections": self.interjections,
            "honorific_level": self.honorific_level,
            "emoji_usage": self.emoji_usage,
            "punctuation_style": self.punctuation_style
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpeechPattern":
        return cls(
            sentence_endings=data.get("sentence_endings", []),
            favorite_phrases=data.get("favorite_phrases", []),
            interjections=data.get("interjections", []),
            honorific_level=data.get("honorific_level", "normal"),
            emoji_usage=data.get("emoji_usage", "none"),
            punctuation_style=data.get("punctuation_style", "normal")
        )


@dataclass
class PersonalityProfile:
    """性格プロファイル"""
    traits: List[PersonalityTrait] = field(default_factory=list)
    values: List[str] = field(default_factory=list)           # 価値観
    interests: List[str] = field(default_factory=list)        # 興味・関心
    strengths: List[str] = field(default_factory=list)        # 強み
    communication_style: CommunicationTone = CommunicationTone.FRIENDLY
    emotional_expression: str = "moderate"  # low/moderate/high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "traits": [t.value for t in self.traits],
            "values": self.values,
            "interests": self.interests,
            "strengths": self.strengths,
            "communication_style": self.communication_style.value,
            "emotional_expression": self.emotional_expression
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityProfile":
        return cls(
            traits=[PersonalityTrait(t) for t in data.get("traits", [])],
            values=data.get("values", []),
            interests=data.get("interests", []),
            strengths=data.get("strengths", []),
            communication_style=CommunicationTone(data.get("communication_style", "friendly")),
            emotional_expression=data.get("emotional_expression", "moderate")
        )


@dataclass
class BackgroundStory:
    """背景ストーリー"""
    name: str = ""
    age: Optional[str] = None
    occupation: str = ""
    background: str = ""            # 経歴・背景
    motivation: str = ""            # 動機・目的
    relationships: List[str] = field(default_factory=list)  # 関係性
    expertise: List[str] = field(default_factory=list)      # 専門分野

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "age": self.age,
            "occupation": self.occupation,
            "background": self.background,
            "motivation": self.motivation,
            "relationships": self.relationships,
            "expertise": self.expertise
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackgroundStory":
        return cls(
            name=data.get("name", ""),
            age=data.get("age"),
            occupation=data.get("occupation", ""),
            background=data.get("background", ""),
            motivation=data.get("motivation", ""),
            relationships=data.get("relationships", []),
            expertise=data.get("expertise", [])
        )


@dataclass
class ResponseBehavior:
    """応答行動設定"""
    response_length: str = "medium"  # short/medium/long/adaptive
    thinking_style: str = "balanced"  # intuitive/analytical/balanced
    advice_style: str = "supportive"  # supportive/directive/collaborative
    question_frequency: str = "moderate"  # low/moderate/high
    example_usage: str = "moderate"   # low/moderate/high
    humor_level: str = "moderate"     # none/subtle/moderate/frequent

    # 特殊な応答条件
    crisis_response_mode: bool = True  # 危機的状況への特別対応
    redirect_to_professional: bool = True  # 専門家への案内を行う

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_length": self.response_length,
            "thinking_style": self.thinking_style,
            "advice_style": self.advice_style,
            "question_frequency": self.question_frequency,
            "example_usage": self.example_usage,
            "humor_level": self.humor_level,
            "crisis_response_mode": self.crisis_response_mode,
            "redirect_to_professional": self.redirect_to_professional
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResponseBehavior":
        return cls(
            response_length=data.get("response_length", "medium"),
            thinking_style=data.get("thinking_style", "balanced"),
            advice_style=data.get("advice_style", "supportive"),
            question_frequency=data.get("question_frequency", "moderate"),
            example_usage=data.get("example_usage", "moderate"),
            humor_level=data.get("humor_level", "moderate"),
            crisis_response_mode=data.get("crisis_response_mode", True),
            redirect_to_professional=data.get("redirect_to_professional", True)
        )


@dataclass
class Persona:
    """ペルソナ（キャラクター設定）"""
    id: str
    name: str
    description: str

    # ソース情報
    source_type: PersonaSourceType = PersonaSourceType.MANUAL
    source_data: Optional[str] = None  # ソースデータへの参照

    # 詳細設定
    personality: PersonalityProfile = field(default_factory=PersonalityProfile)
    speech_pattern: SpeechPattern = field(default_factory=SpeechPattern)
    background: BackgroundStory = field(default_factory=BackgroundStory)
    behavior: ResponseBehavior = field(default_factory=ResponseBehavior)

    # カスタムプロンプト（上記を上書き）
    custom_prompt: Optional[str] = None

    # メタデータ
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    is_active: bool = True
    is_public: bool = False  # 公開ペルソナかどうか
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None  # ユーザーID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type.value,
            "source_data": self.source_data,
            "personality": self.personality.to_dict(),
            "speech_pattern": self.speech_pattern.to_dict(),
            "background": self.background.to_dict(),
            "behavior": self.behavior.to_dict(),
            "custom_prompt": self.custom_prompt,
            "tags": self.tags,
            "category": self.category,
            "is_active": self.is_active,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Persona":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            source_type=PersonaSourceType(data.get("source_type", "manual")),
            source_data=data.get("source_data"),
            personality=PersonalityProfile.from_dict(data.get("personality", {})),
            speech_pattern=SpeechPattern.from_dict(data.get("speech_pattern", {})),
            background=BackgroundStory.from_dict(data.get("background", {})),
            behavior=ResponseBehavior.from_dict(data.get("behavior", {})),
            custom_prompt=data.get("custom_prompt"),
            tags=data.get("tags", []),
            category=data.get("category", "general"),
            is_active=data.get("is_active", True),
            is_public=data.get("is_public", False),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            created_by=data.get("created_by")
        )

    def generate_system_prompt(self) -> str:
        """ペルソナからシステムプロンプトを生成"""
        if self.custom_prompt:
            return self.custom_prompt

        parts = []

        # 基本情報
        if self.background.name:
            parts.append(f"あなたは「{self.background.name}」です。")
        else:
            parts.append(f"あなたは「{self.name}」というキャラクターです。")

        if self.description:
            parts.append(self.description)

        # 背景
        if self.background.occupation:
            parts.append(f"職業/役割: {self.background.occupation}")
        if self.background.background:
            parts.append(f"背景: {self.background.background}")
        if self.background.motivation:
            parts.append(f"目的: {self.background.motivation}")
        if self.background.expertise:
            parts.append(f"専門分野: {', '.join(self.background.expertise)}")

        # 性格
        if self.personality.traits:
            trait_names = {
                PersonalityTrait.EXTROVERT: "外向的",
                PersonalityTrait.INTROVERT: "内向的",
                PersonalityTrait.ANALYTICAL: "分析的",
                PersonalityTrait.CREATIVE: "創造的",
                PersonalityTrait.PRACTICAL: "実践的",
                PersonalityTrait.IDEALISTIC: "理想主義的",
                PersonalityTrait.OPTIMISTIC: "楽観的",
                PersonalityTrait.REALISTIC: "現実的",
                PersonalityTrait.SUPPORTIVE: "支持的",
                PersonalityTrait.CHALLENGING: "挑戦的",
            }
            traits_text = ", ".join([trait_names.get(t, t.value) for t in self.personality.traits])
            parts.append(f"性格: {traits_text}")

        if self.personality.values:
            parts.append(f"大切にしている価値観: {', '.join(self.personality.values)}")

        # コミュニケーションスタイル
        tone_names = {
            CommunicationTone.FORMAL: "フォーマルな",
            CommunicationTone.CASUAL: "カジュアルな",
            CommunicationTone.FRIENDLY: "フレンドリーな",
            CommunicationTone.PROFESSIONAL: "プロフェッショナルな",
            CommunicationTone.PLAYFUL: "遊び心のある",
            CommunicationTone.EMPATHETIC: "共感的な",
            CommunicationTone.ASSERTIVE: "自信に満ちた",
            CommunicationTone.GENTLE: "優しい",
        }
        parts.append(f"コミュニケーションスタイル: {tone_names.get(self.personality.communication_style, '')}話し方")

        # 発話パターン
        if self.speech_pattern.sentence_endings:
            parts.append(f"文末表現: {', '.join(self.speech_pattern.sentence_endings)}")
        if self.speech_pattern.favorite_phrases:
            parts.append(f"口癖: {', '.join(self.speech_pattern.favorite_phrases)}")

        honorific_map = {
            "casual": "敬語は使わず、くだけた話し方をする",
            "normal": "適度な敬語を使う",
            "polite": "丁寧な敬語を使う",
            "very_polite": "非常に丁寧な敬語を使う"
        }
        if self.speech_pattern.honorific_level in honorific_map:
            parts.append(honorific_map[self.speech_pattern.honorific_level])

        emoji_map = {
            "none": "絵文字は使わない",
            "minimal": "絵文字は控えめに使う",
            "moderate": "適度に絵文字を使う",
            "frequent": "絵文字を積極的に使う"
        }
        if self.speech_pattern.emoji_usage in emoji_map:
            parts.append(emoji_map[self.speech_pattern.emoji_usage])

        # 応答行動
        parts.append("\n**応答のガイドライン:**")

        length_map = {
            "short": "簡潔で短い応答を心がける",
            "medium": "適度な長さの応答をする",
            "long": "詳細で丁寧な応答をする",
            "adaptive": "状況に応じて応答の長さを調整する"
        }
        if self.behavior.response_length in length_map:
            parts.append(f"- {length_map[self.behavior.response_length]}")

        advice_map = {
            "supportive": "相手を支持し、励ます姿勢で接する",
            "directive": "明確な方向性を示し、具体的な指示を与える",
            "collaborative": "一緒に考え、解決策を導く"
        }
        if self.behavior.advice_style in advice_map:
            parts.append(f"- {advice_map[self.behavior.advice_style]}")

        if self.behavior.crisis_response_mode:
            parts.append("- 危機的状況（自殺願望など）の場合は、専門機関への相談を強く推奨する")

        return "\n".join(parts)


class PersonaAnalyzer:
    """ペルソナ分析器（テキストデータから自動分析）"""

    def __init__(self):
        # 分析用プロンプトテンプレート
        self._analysis_prompt_template = """以下のテキストデータを分析し、この人物のペルソナ（キャラクター設定）を抽出してください。

**分析するテキスト:**
{text_data}

**以下の項目について、JSONフォーマットで回答してください:**

```json
{{
  "personality": {{
    "traits": ["性格特性のリスト（extrovert/introvert/analytical/creative/practical/idealistic/optimistic/realistic/supportive/challenging）"],
    "values": ["大切にしている価値観のリスト"],
    "interests": ["興味・関心のリスト"],
    "strengths": ["強みのリスト"],
    "communication_style": "コミュニケーションスタイル（formal/casual/friendly/professional/playful/empathetic/assertive/gentle）",
    "emotional_expression": "感情表現の程度（low/moderate/high）"
  }},
  "speech_pattern": {{
    "sentence_endings": ["よく使う文末表現のリスト"],
    "favorite_phrases": ["口癖・よく使うフレーズのリスト"],
    "interjections": ["よく使う感嘆詞のリスト"],
    "honorific_level": "敬語レベル（casual/normal/polite/very_polite）",
    "emoji_usage": "絵文字使用頻度（none/minimal/moderate/frequent）"
  }},
  "background": {{
    "occupation": "推測される職業や役割",
    "expertise": ["専門分野や得意なことのリスト"],
    "interests_detail": "興味関心の詳細な説明"
  }},
  "summary": "この人物の特徴を3-5文で要約"
}}
```

テキストから読み取れる情報のみを記載し、推測が難しい項目は空のリストまたはnullとしてください。"""

    def create_analysis_prompt(self, text_data: str, max_chars: int = 10000) -> str:
        """分析用プロンプトを生成"""
        # テキストが長すぎる場合は切り詰める
        if len(text_data) > max_chars:
            text_data = text_data[:max_chars] + "...(以下省略)"

        return self._analysis_prompt_template.format(text_data=text_data)

    def parse_analysis_result(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """LLMの分析結果をパース"""
        try:
            # JSONブロックを抽出
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # JSONブロックがない場合は全体をJSONとして試す
                json_str = llm_response

            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def create_persona_from_analysis(
        self,
        analysis_result: Dict[str, Any],
        persona_id: str,
        persona_name: str,
        source_type: PersonaSourceType = PersonaSourceType.TEXT_ANALYSIS
    ) -> Persona:
        """分析結果からペルソナを作成"""
        personality_data = analysis_result.get("personality", {})
        speech_data = analysis_result.get("speech_pattern", {})
        background_data = analysis_result.get("background", {})

        return Persona(
            id=persona_id,
            name=persona_name,
            description=analysis_result.get("summary", ""),
            source_type=source_type,
            personality=PersonalityProfile(
                traits=[PersonalityTrait(t) for t in personality_data.get("traits", [])
                        if t in [e.value for e in PersonalityTrait]],
                values=personality_data.get("values", []),
                interests=personality_data.get("interests", []),
                strengths=personality_data.get("strengths", []),
                communication_style=CommunicationTone(
                    personality_data.get("communication_style", "friendly")
                ) if personality_data.get("communication_style") in [e.value for e in CommunicationTone]
                else CommunicationTone.FRIENDLY,
                emotional_expression=personality_data.get("emotional_expression", "moderate")
            ),
            speech_pattern=SpeechPattern(
                sentence_endings=speech_data.get("sentence_endings", []),
                favorite_phrases=speech_data.get("favorite_phrases", []),
                interjections=speech_data.get("interjections", []),
                honorific_level=speech_data.get("honorific_level", "normal"),
                emoji_usage=speech_data.get("emoji_usage", "none")
            ),
            background=BackgroundStory(
                name=persona_name,
                occupation=background_data.get("occupation", ""),
                expertise=background_data.get("expertise", [])
            )
        )


class PersonaStore:
    """ペルソナストア"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.personas_file = self.data_dir / "personas.json"
        self.data_dir.mkdir(exist_ok=True)

        self._personas: Dict[str, Persona] = {}
        self._load_personas()
        self._initialize_default_personas()

    def _load_personas(self) -> None:
        """ペルソナを読み込み"""
        if self.personas_file.exists():
            try:
                with open(self.personas_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for persona_id, persona_data in data.get("personas", {}).items():
                        self._personas[persona_id] = Persona.from_dict(persona_data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"ペルソナ読み込みエラー: {e}")

    def _save_personas(self) -> None:
        """ペルソナを保存"""
        data = {
            "personas": {pid: p.to_dict() for pid, p in self._personas.items()},
            "updated_at": datetime.now().isoformat()
        }
        with open(self.personas_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _initialize_default_personas(self) -> None:
        """デフォルトペルソナの初期化"""
        default_personas = [
            Persona(
                id="counselor_standard",
                name="人生相談カウンセラー",
                description="経験豊富で共感力の高いカウンセラー",
                category="counseling",
                tags=["カウンセラー", "標準", "人生相談"],
                personality=PersonalityProfile(
                    traits=[PersonalityTrait.SUPPORTIVE, PersonalityTrait.ANALYTICAL],
                    values=["共感", "成長", "誠実さ"],
                    communication_style=CommunicationTone.EMPATHETIC,
                    emotional_expression="moderate"
                ),
                speech_pattern=SpeechPattern(
                    honorific_level="polite",
                    emoji_usage="minimal"
                ),
                background=BackgroundStory(
                    name="相談員",
                    occupation="人生相談カウンセラー",
                    motivation="相談者の悩みに寄り添い、前向きな一歩を支援する",
                    expertise=["傾聴", "共感", "問題解決支援"]
                ),
                behavior=ResponseBehavior(
                    advice_style="supportive",
                    crisis_response_mode=True,
                    redirect_to_professional=True
                ),
                is_public=True
            ),
            Persona(
                id="friendly_sister",
                name="優しいお姉さん",
                description="親しみやすくて頼りになるお姉さんキャラクター",
                category="counseling",
                tags=["お姉さん", "親しみやすい", "家族的"],
                personality=PersonalityProfile(
                    traits=[PersonalityTrait.SUPPORTIVE, PersonalityTrait.OPTIMISTIC, PersonalityTrait.EXTROVERT],
                    values=["家族愛", "成長", "励まし"],
                    communication_style=CommunicationTone.FRIENDLY,
                    emotional_expression="high"
                ),
                speech_pattern=SpeechPattern(
                    sentence_endings=["〜だよ", "〜だね", "〜かな？"],
                    favorite_phrases=["大丈夫だよ", "一緒に考えよう", "応援してるよ"],
                    honorific_level="casual",
                    emoji_usage="moderate"
                ),
                background=BackgroundStory(
                    name="お姉さん",
                    occupation="頼れるお姉さん",
                    motivation="弟や妹のように相談者を見守り、成長を支援する"
                ),
                behavior=ResponseBehavior(
                    advice_style="supportive",
                    humor_level="moderate"
                ),
                is_public=True
            ),
            Persona(
                id="wise_mentor",
                name="人生の師匠",
                description="豊富な経験を持つ賢明なメンター",
                category="counseling",
                tags=["メンター", "師匠", "経験豊富"],
                personality=PersonalityProfile(
                    traits=[PersonalityTrait.ANALYTICAL, PersonalityTrait.REALISTIC, PersonalityTrait.SUPPORTIVE],
                    values=["知恵", "自立", "長期的視点"],
                    communication_style=CommunicationTone.PROFESSIONAL,
                    emotional_expression="moderate"
                ),
                speech_pattern=SpeechPattern(
                    honorific_level="normal",
                    emoji_usage="none"
                ),
                background=BackgroundStory(
                    name="師匠",
                    occupation="人生のメンター",
                    motivation="相談者が自分で答えを見つけられるよう導く",
                    expertise=["人生経験", "質問力", "長期的視点"]
                ),
                behavior=ResponseBehavior(
                    advice_style="collaborative",
                    question_frequency="high",
                    thinking_style="analytical"
                ),
                is_public=True
            ),
            Persona(
                id="tech_support",
                name="テクニカルサポート",
                description="IT・技術系の相談に特化したサポーター",
                category="technical",
                tags=["技術", "IT", "サポート"],
                personality=PersonalityProfile(
                    traits=[PersonalityTrait.ANALYTICAL, PersonalityTrait.PRACTICAL],
                    values=["正確性", "効率", "学習"],
                    communication_style=CommunicationTone.PROFESSIONAL
                ),
                speech_pattern=SpeechPattern(
                    honorific_level="polite",
                    emoji_usage="none"
                ),
                background=BackgroundStory(
                    occupation="テクニカルサポート",
                    expertise=["プログラミング", "システム設計", "トラブルシューティング"]
                ),
                behavior=ResponseBehavior(
                    advice_style="directive",
                    example_usage="high",
                    thinking_style="analytical"
                ),
                is_public=True
            ),
        ]

        for persona in default_personas:
            if persona.id not in self._personas:
                self._personas[persona.id] = persona

        self._save_personas()

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """ペルソナを取得"""
        return self._personas.get(persona_id)

    def get_persona_prompt(self, persona_id: str) -> str:
        """ペルソナのシステムプロンプトを取得"""
        persona = self.get_persona(persona_id)
        if persona and persona.is_active:
            return persona.generate_system_prompt()
        return self.get_persona_prompt("counselor_standard")

    def list_personas(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        active_only: bool = True,
        public_only: bool = False
    ) -> List[Persona]:
        """ペルソナ一覧を取得"""
        personas = list(self._personas.values())

        if active_only:
            personas = [p for p in personas if p.is_active]
        if public_only:
            personas = [p for p in personas if p.is_public]
        if category:
            personas = [p for p in personas if p.category == category]
        if tags:
            personas = [p for p in personas if any(t in p.tags for t in tags)]

        return personas

    def add_persona(self, persona: Persona) -> bool:
        """ペルソナを追加"""
        if persona.id in self._personas:
            return False
        self._personas[persona.id] = persona
        self._save_personas()
        return True

    def update_persona(self, persona_id: str, **kwargs) -> bool:
        """ペルソナを更新"""
        if persona_id not in self._personas:
            return False

        persona = self._personas[persona_id]
        for key, value in kwargs.items():
            if hasattr(persona, key):
                setattr(persona, key, value)
        persona.updated_at = datetime.now()

        self._save_personas()
        return True

    def delete_persona(self, persona_id: str) -> bool:
        """ペルソナを削除"""
        if persona_id in self._personas:
            del self._personas[persona_id]
            self._save_personas()
            return True
        return False

    def search_personas(self, query: str) -> List[Persona]:
        """ペルソナを検索"""
        results = []
        query_lower = query.lower()

        for persona in self._personas.values():
            if not persona.is_active:
                continue

            if (query_lower in persona.name.lower() or
                query_lower in persona.description.lower() or
                any(query_lower in tag.lower() for tag in persona.tags)):
                results.append(persona)

        return results

    def get_user_personas(self, user_id: str) -> List[Persona]:
        """ユーザーが作成したペルソナを取得"""
        return [p for p in self._personas.values() if p.created_by == user_id]

    def clone_persona(
        self,
        source_persona_id: str,
        new_id: str,
        new_name: str,
        created_by: Optional[str] = None
    ) -> Optional[Persona]:
        """ペルソナを複製"""
        source = self.get_persona(source_persona_id)
        if not source:
            return None

        new_persona = Persona.from_dict(source.to_dict())
        new_persona.id = new_id
        new_persona.name = new_name
        new_persona.created_at = datetime.now()
        new_persona.updated_at = datetime.now()
        new_persona.created_by = created_by
        new_persona.is_public = False

        self.add_persona(new_persona)
        return new_persona


# グローバルインスタンス
_global_persona_store: Optional[PersonaStore] = None
_global_persona_analyzer: Optional[PersonaAnalyzer] = None


def get_persona_store(data_dir: str = "data") -> PersonaStore:
    """グローバルペルソナストアを取得"""
    global _global_persona_store
    if _global_persona_store is None:
        _global_persona_store = PersonaStore(data_dir=data_dir)
    return _global_persona_store


def get_persona_analyzer() -> PersonaAnalyzer:
    """グローバルペルソナアナライザーを取得"""
    global _global_persona_analyzer
    if _global_persona_analyzer is None:
        _global_persona_analyzer = PersonaAnalyzer()
    return _global_persona_analyzer


# 便利関数
def get_persona_prompt(persona_id: str) -> str:
    """ペルソナプロンプトを取得"""
    return get_persona_store().get_persona_prompt(persona_id)


def list_available_personas() -> List[Dict[str, Any]]:
    """利用可能なペルソナ一覧を取得"""
    return [p.to_dict() for p in get_persona_store().list_personas(public_only=True)]
