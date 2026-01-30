"""
統合設定管理

pydantic-settings を使用した型安全な設定管理
- 環境変数から自動読み込み
- バリデーション付き
- デフォルト値対応
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """AI プロバイダー設定"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    openai_api_key: str = Field(
        default="", alias="OPENAI_API_KEY", description="OpenAI API キー"
    )
    openai_model: str = Field(
        default="gpt-4.1", alias="OPENAI_MODEL", description="OpenAI モデル"
    )

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """API キーの形式を簡易チェック"""
        if v and not v.startswith("sk-"):
            import logging
            logging.getLogger(__name__).warning(
                "OpenAI API key does not start with 'sk-' - may be invalid"
            )
        return v


class SecuritySettings(BaseSettings):
    """セキュリティ設定"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="YAMII_", extra="ignore")

    # API 認証（カンマ区切り文字列で指定）
    api_keys_str: str = Field(
        default="",
        alias="YAMII_API_KEYS",
        description="許可された API キー（カンマ区切り）",
    )
    api_key_header: str = Field(default="X-API-Key", description="API キーヘッダー名")

    # レート制限
    rate_limit_enabled: bool = Field(default=True, description="レート制限を有効化")
    rate_limit_requests: int = Field(
        default=100, description="レート制限: リクエスト数"
    )
    rate_limit_window: int = Field(default=60, description="レート制限: ウィンドウ(秒)")

    @property
    def api_keys(self) -> list[str]:
        """API キーリストを取得"""
        if not self.api_keys_str:
            return []
        return [k.strip() for k in self.api_keys_str.split(",") if k.strip()]


class YamiiSettings(BaseSettings):
    """Yamii 全体設定"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 基本設定
    data_dir: str = Field(
        default="data", alias="YAMII_DATA_DIR", description="データ保存ディレクトリ"
    )
    debug: bool = Field(
        default=False, alias="YAMII_DEBUG", description="デバッグモード"
    )
    log_level: str = Field(
        default="INFO", alias="YAMII_LOG_LEVEL", description="ログレベル"
    )

    # サブ設定
    ai: AISettings = Field(default_factory=AISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # API サーバー設定
    api_host: str = Field(
        default="http://localhost:8000", alias="API_HOST", description="API サーバーベースURL"
    )
    api_port: int = Field(
        default=8000, alias="API_PORT", description="API サーバーポート"
    )

    # フロントエンド設定
    frontend_url: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_URL",
        description="フロントエンドのベースURL",
    )

    @classmethod
    def load(cls) -> YamiiSettings:
        """設定をロード（サブ設定も含む）"""
        return cls(
            ai=AISettings(),
            security=SecuritySettings(),
        )


@lru_cache
def get_settings() -> YamiiSettings:
    """
    設定を取得（キャッシュ付き）

    使用例:
        settings = get_settings()
        print(settings.ai.openai_api_key)
    """
    return YamiiSettings.load()


def reload_settings() -> YamiiSettings:
    """設定を再読み込み"""
    get_settings.cache_clear()
    return get_settings()
