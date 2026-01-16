"""
統合設定管理

pydantic-settings を使用した型安全な設定管理
- 環境変数から自動読み込み
- バリデーション付き
- デフォルト値対応
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """データベース設定"""

    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = Field(default="localhost", description="データベースホスト")
    port: int = Field(default=5432, description="データベースポート")
    name: str = Field(default="yamii", description="データベース名")
    user: str = Field(default="yamii", description="データベースユーザー")
    password: str = Field(default="", description="データベースパスワード")

    @property
    def url(self) -> str:
        """PostgreSQL接続URL"""
        if self.password:
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.name}"


class AISettings(BaseSettings):
    """AI プロバイダー設定"""

    model_config = SettingsConfigDict(env_prefix="")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY", description="OpenAI API キー")
    openai_model: str = Field(default="gpt-4.1", alias="OPENAI_MODEL", description="OpenAI モデル")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY", description="Gemini API キー")

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """API キーの形式を簡易チェック"""
        if v and not v.startswith("sk-"):
            # 警告のみ（テスト環境等で別形式を使う場合があるため）
            pass
        return v


class MisskeySettings(BaseSettings):
    """Misskey Bot 設定"""

    model_config = SettingsConfigDict(env_prefix="MISSKEY_")

    instance_url: str = Field(default="", description="Misskey インスタンス URL")
    access_token: str = Field(default="", description="Misskey アクセストークン")
    bot_user_id: str = Field(default="", description="Bot ユーザー ID")

    # 動作設定
    stream_reconnect_delay: int = Field(default=5, description="再接続遅延(秒)")
    max_reconnect_attempts: int = Field(default=10, description="最大再接続試行回数")

    @property
    def is_configured(self) -> bool:
        """Misskey が設定済みか"""
        return bool(self.instance_url and self.access_token and self.bot_user_id)


class SecuritySettings(BaseSettings):
    """セキュリティ設定"""

    model_config = SettingsConfigDict(env_prefix="YAMII_")

    # 暗号化
    encryption_enabled: bool = Field(default=True, description="E2EE 暗号化を有効化")
    master_key: Optional[str] = Field(default=None, alias="YAMII_MASTER_KEY", description="マスター暗号化キー (Base64)")

    # API 認証（カンマ区切り文字列で指定）
    api_keys_str: str = Field(
        default="",
        alias="YAMII_API_KEYS",
        description="許可された API キー（カンマ区切り）"
    )
    api_key_header: str = Field(default="X-API-Key", description="API キーヘッダー名")

    # レート制限
    rate_limit_enabled: bool = Field(default=True, description="レート制限を有効化")
    rate_limit_requests: int = Field(default=100, description="レート制限: リクエスト数")
    rate_limit_window: int = Field(default=60, description="レート制限: ウィンドウ(秒)")

    @property
    def api_keys(self) -> List[str]:
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
    data_dir: str = Field(default="data", alias="YAMII_DATA_DIR", description="データ保存ディレクトリ")
    debug: bool = Field(default=False, alias="YAMII_DEBUG", description="デバッグモード")
    log_level: str = Field(default="INFO", alias="YAMII_LOG_LEVEL", description="ログレベル")

    # サブ設定
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ai: AISettings = Field(default_factory=AISettings)
    misskey: MisskeySettings = Field(default_factory=MisskeySettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # API サーバー設定
    api_host: str = Field(default="0.0.0.0", alias="API_HOST", description="API サーバーホスト")
    api_port: int = Field(default=8000, alias="API_PORT", description="API サーバーポート")

    @classmethod
    def load(cls) -> "YamiiSettings":
        """設定をロード（サブ設定も含む）"""
        return cls(
            database=DatabaseSettings(),
            ai=AISettings(),
            misskey=MisskeySettings(),
            security=SecuritySettings(),
        )


@lru_cache()
def get_settings() -> YamiiSettings:
    """
    設定を取得（キャッシュ付き）

    使用例:
        settings = get_settings()
        print(settings.ai.openai_api_key)
        print(settings.misskey.instance_url)
    """
    return YamiiSettings.load()


def reload_settings() -> YamiiSettings:
    """設定を再読み込み"""
    get_settings.cache_clear()
    return get_settings()
