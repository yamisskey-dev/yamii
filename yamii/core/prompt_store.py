"""
データベースベースのプロンプト管理システム
YAMII.mdに依存しない独立したプロンプトストレージ
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PromptEntry:
    """プロンプトエントリー"""

    id: str
    name: str
    description: str
    prompt_text: str
    category: str = "counseling"
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    active: bool = True

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prompt_text": self.prompt_text,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "active": self.active,
        }


class PromptStore:
    """プロンプトストレージ（メモリ内DB代替）"""

    def __init__(self):
        self.prompts: dict[str, PromptEntry] = {}
        self._initialize_default_prompts()

    def _initialize_default_prompts(self):
        """デフォルトプロンプトの初期化（シンプル版）"""
        default_prompts = [
            PromptEntry(
                id="default",
                name="相談対応",
                description="シンプルな相談対応",
                category="counseling",
                tags=["相談", "標準"],
                prompt_text="""あなたは相談者の話に寄り添う相談相手です。
まず気持ちを受け止め、必要に応じて一緒に考えます。
危機的状況では専門機関への相談を案内します。""",
            ),
        ]

        for prompt in default_prompts:
            self.prompts[prompt.id] = prompt

    def get_prompt(self, prompt_id: str) -> PromptEntry | None:
        """プロンプトを取得"""
        return self.prompts.get(prompt_id)

    def get_prompt_text(self, prompt_id: str) -> str:
        """プロンプトテキストを取得（フォールバック付き）"""
        prompt = self.get_prompt(prompt_id)
        if prompt and prompt.active:
            return prompt.prompt_text

        # フォールバック
        if prompt_id != "default":
            return self.get_prompt_text("default")

        # 最終フォールバック
        return """あなたは相談者の話に寄り添う相談相手です。
まず気持ちを受け止め、必要に応じて一緒に考えます。"""

    def list_prompts(
        self, category: str = None, active_only: bool = True
    ) -> list[PromptEntry]:
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

    def search_prompts(self, query: str) -> list[PromptEntry]:
        """プロンプトを検索"""
        results = []
        query_lower = query.lower()

        for prompt in self.prompts.values():
            if not prompt.active:
                continue

            if (
                query_lower in prompt.name.lower()
                or query_lower in prompt.description.lower()
                or query_lower in prompt.prompt_text.lower()
                or any(query_lower in tag.lower() for tag in prompt.tags)
            ):
                results.append(prompt)

        return results

    def get_available_prompt_ids(self) -> list[str]:
        """利用可能なプロンプトIDの一覧"""
        return [p.id for p in self.prompts.values() if p.active]

    def validate_prompt_id(self, prompt_id: str) -> bool:
        """プロンプトIDが有効かチェック"""
        prompt = self.prompts.get(prompt_id)
        return prompt is not None and prompt.active


# グローバルインスタンス（シングルトンパターン）
_global_prompt_store: PromptStore | None = None


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


def list_available_prompts() -> list[dict[str, Any]]:
    """利用可能なプロンプト一覧を取得"""
    return [p.to_dict() for p in get_prompt_store().list_prompts()]


def validate_prompt_id(prompt_id: str) -> bool:
    """プロンプトIDが有効かチェック"""
    return get_prompt_store().validate_prompt_id(prompt_id)
