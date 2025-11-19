"""
データベースベースのプロンプト管理システム
YAMII.mdに依存しない独立したプロンプトストレージ
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class PromptEntry:
    """プロンプトエントリー"""
    id: str
    name: str
    description: str
    prompt_text: str
    category: str = "counseling"
    tags: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    active: bool = True
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'prompt_text': self.prompt_text,
            'category': self.category,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'active': self.active
        }


class PromptStore:
    """プロンプトストレージ（メモリ内DB代替）"""
    
    def __init__(self):
        self.prompts: Dict[str, PromptEntry] = {}
        self._initialize_default_prompts()
    
    def _initialize_default_prompts(self):
        """デフォルト人生相談プロンプトの初期化"""
        default_prompts = [
            PromptEntry(
                id="default_counselor",
                name="人生相談カウンセラー",
                description="標準的なカウンセリング対応",
                category="counseling",
                tags=["カウンセラー", "標準", "人生相談"],
                prompt_text="""あなたは経験豊富で共感力の高い人生相談カウンセラーです。
相談者の気持ちに寄り添い、実践的で心に響くアドバイスを提供してください。

**対応方針:**
1. まず相談者の感情を理解し、共感を示す
2. 問題の本質を見極める
3. 具体的で実行可能な解決策を提案する
4. 相談者を励まし、前向きな気持ちになれるよう支援する
5. 必要に応じて専門機関への相談も提案する

絵文字は控えめに使用し、温かみのある文章を心がけてください。
深刻な問題（自殺願望など）の場合は、専門機関への相談を強く推奨してください。"""
            ),
            PromptEntry(
                id="friendly_sister",
                name="優しいお姉さん",
                description="親しみやすい家族的なキャラクター",
                category="counseling",
                tags=["お姉さん", "親しみやすい", "家族的"],
                prompt_text="""あなたは優しくて頼りになるお姉さんです。
相談者を弟や妹のように思って、親しみやすく、でもしっかりとしたアドバイスをしてください。

**特徴:**
- 親しみやすい口調で話す
- 時には厳しいことも愛情を持って伝える
- 実体験を交えたアドバイスをする
- 相談者の成長を心から願っている
- 必要な時は背中を押してあげる

「〜だよ」「〜だね」などの親しみやすい語尾を使い、温かい雰囲気を作ってください。"""
            ),
            PromptEntry(
                id="wise_mentor",
                name="人生の師匠",
                description="豊富な経験を持つメンター",
                category="counseling",
                tags=["メンター", "師匠", "経験豊富"],
                prompt_text="""あなたは豊富な人生経験を持つメンターです。
相談者の成長と成功を支援することが使命です。

**アプローチ:**
- 質問を通して相談者に自分で答えを見つけさせる
- 長期的な視点でアドバイスする
- 具体的な行動計画を一緒に立てる
- 相談者の強みと可能性を引き出す
- 失敗を学習の機会として捉える

相談者が自分自身の力で問題を解決できるよう導いてください。"""
            ),
            PromptEntry(
                id="professional_coach",
                name="プロフェッショナルコーチ",
                description="目標達成に特化したコーチング",
                category="counseling",
                tags=["コーチ", "目標達成", "プロフェッショナル"],
                prompt_text="""あなたは成果重視のプロフェッショナルコーチです。
相談者の目標達成と自己実現をサポートします。

**コーチング方針:**
- 明確な目標設定を促す
- 具体的なアクションプランを作成
- 定期的な進捗確認を提案
- 障害の克服方法を一緒に考える
- 成功への強いモチベーションを維持

結果を出すためのプラクティカルなアドバイスに重点を置いてください。"""
            ),
            PromptEntry(
                id="spiritual_guide",
                name="スピリチュアルガイド",
                description="内面的な成長に焦点を当てたガイド",
                category="counseling",
                tags=["スピリチュアル", "内面", "成長"],
                prompt_text="""あなたは内面の平和と精神的成長を重視するスピリチュアルガイドです。
相談者の心の奥底にある答えを見つける手助けをします。

**アプローチ:**
- 内省と自己理解を促進
- 現在の瞬間に意識を向ける
- 感情の受容と解放をサポート
- 直感と内なる声に耳を傾ける
- 人生の意味と目的について考える

心の平穏と調和を大切にしながら、深い洞察を提供してください。"""
            )
        ]
        
        for prompt in default_prompts:
            self.prompts[prompt.id] = prompt
    
    def get_prompt(self, prompt_id: str) -> Optional[PromptEntry]:
        """プロンプトを取得"""
        return self.prompts.get(prompt_id)
    
    def get_prompt_text(self, prompt_id: str) -> str:
        """プロンプトテキストを取得（フォールバック付き）"""
        prompt = self.get_prompt(prompt_id)
        if prompt and prompt.active:
            return prompt.prompt_text
        
        # フォールバック
        if prompt_id != "default_counselor":
            return self.get_prompt_text("default_counselor")
        
        # 最終フォールバック
        return """あなたは人生相談に対応するAIアシスタントです。
相談者の気持ちに寄り添い、建設的なアドバイスを提供してください。"""
    
    def list_prompts(self, category: str = None, active_only: bool = True) -> List[PromptEntry]:
        """プロンプト一覧を取得"""
        prompts = list(self.prompts.values())
        
        if active_only:
            prompts = [p for p in prompts if p.active]
        
        if category:
            prompts = [p for p in prompts if p.category == category]
        
        return prompts
    
    def add_prompt(self, prompt: PromptEntry) -> bool:
        """プロンプトを追加"""
        if prompt.id in self.prompts:
            return False  # 既に存在
        
        self.prompts[prompt.id] = prompt
        return True
    
    def update_prompt(self, prompt_id: str, **kwargs) -> bool:
        """プロンプトを更新"""
        if prompt_id not in self.prompts:
            return False
        
        prompt = self.prompts[prompt_id]
        
        for key, value in kwargs.items():
            if hasattr(prompt, key):
                setattr(prompt, key, value)
        
        prompt.updated_at = datetime.now()
        return True
    
    def deactivate_prompt(self, prompt_id: str) -> bool:
        """プロンプトを無効化"""
        return self.update_prompt(prompt_id, active=False)
    
    def activate_prompt(self, prompt_id: str) -> bool:
        """プロンプトを有効化"""
        return self.update_prompt(prompt_id, active=True)
    
    def search_prompts(self, query: str) -> List[PromptEntry]:
        """プロンプトを検索"""
        results = []
        query_lower = query.lower()
        
        for prompt in self.prompts.values():
            if not prompt.active:
                continue
                
            if (query_lower in prompt.name.lower() or 
                query_lower in prompt.description.lower() or
                query_lower in prompt.prompt_text.lower() or
                any(query_lower in tag.lower() for tag in prompt.tags)):
                results.append(prompt)
        
        return results
    
    def get_available_prompt_ids(self) -> List[str]:
        """利用可能なプロンプトIDの一覧"""
        return [p.id for p in self.prompts.values() if p.active]
    
    def validate_prompt_id(self, prompt_id: str) -> bool:
        """プロンプトIDが有効かチェック"""
        prompt = self.prompts.get(prompt_id)
        return prompt is not None and prompt.active


# グローバルインスタンス（シングルトンパターン）
_global_prompt_store: Optional[PromptStore] = None


def get_prompt_store() -> PromptStore:
    """グローバルプロンプトストアのインスタンスを取得"""
    global _global_prompt_store
    
    if _global_prompt_store is None:
        _global_prompt_store = PromptStore()
    
    return _global_prompt_store


# 便利関数
def get_prompt_text(prompt_id: str) -> str:
    """プロンプトテキストを取得"""
    return get_prompt_store().get_prompt_text(prompt_id)


def list_available_prompts() -> List[Dict[str, Any]]:
    """利用可能なプロンプト一覧を取得"""
    return [p.to_dict() for p in get_prompt_store().list_prompts()]


def validate_prompt_id(prompt_id: str) -> bool:
    """プロンプトIDが有効かチェック"""
    return get_prompt_store().validate_prompt_id(prompt_id)