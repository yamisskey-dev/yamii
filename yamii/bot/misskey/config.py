"""
Yamii Misskey Bot Configuration
yamiiのMisskeyボット設定
"""

import os
from dataclasses import dataclass


@dataclass
class YamiiMisskeyBotConfig:
    """Yamii Misskeyボット設定クラス（独立設計）"""

    # Yamii API設定
    yamii_api_url: str = "http://localhost:8000"
    yamii_api_timeout: int = 30

    # ボット基本設定
    bot_name: str = "yamii"
    bot_username: str = "yamii"

    # セッション設定
    session_timeout: int = 3600  # 1時間

    # ログ設定
    log_level: str = "INFO"
    log_file: str | None = None

    # 機能設定
    enable_dm: bool = True
    enable_mentions: bool = True
    enable_timeline: bool = False
    enable_global_timeline: bool = False

    # プロアクティブアウトリーチ設定
    enable_proactive_outreach: bool = True
    proactive_check_interval: int = 3600  # 1時間ごとにチェック

    # 危機対応設定
    crisis_hotlines: list = None

    # Misskey固有設定
    misskey_instance_url: str = ""
    misskey_access_token: str = ""
    misskey_bot_user_id: str = ""

    # HTTP/WebSocket設定
    request_timeout: int = 30

    def __post_init__(self):
        """設定の後処理"""
        if self.crisis_hotlines is None:
            self.crisis_hotlines = [
                "いのちの電話: 0570-783-556",
                "こころの健康相談統一ダイヤル: 0570-064-556",
            ]

        # Misskey固有の検証
        if not self.misskey_instance_url:
            raise ValueError("misskey_instance_url is required")
        if not self.misskey_access_token:
            raise ValueError("misskey_access_token is required")
        if not self.misskey_bot_user_id:
            raise ValueError("misskey_bot_user_id is required")

    @property
    def crisis_hotline_numbers(self):
        """危機対応ホットライン番号リスト"""
        return self.crisis_hotlines


def load_config() -> YamiiMisskeyBotConfig:
    """環境変数から設定を読み込む"""

    # Misskeyボット有効化チェック
    enable_bot = os.getenv("ENABLE_MISSKEY_BOT", "false").lower() == "true"
    if not enable_bot:
        raise ValueError(
            "ENABLE_MISSKEY_BOT is set to false. Set it to true to enable the Misskey bot."
        )

    # 必須環境変数のチェック
    misskey_instance_url = os.getenv("MISSKEY_INSTANCE_URL")
    misskey_access_token = os.getenv("MISSKEY_ACCESS_TOKEN")
    misskey_bot_user_id = os.getenv("MISSKEY_BOT_USER_ID")

    if not misskey_instance_url:
        raise ValueError(
            "MISSKEY_INSTANCE_URL environment variable is required when ENABLE_MISSKEY_BOT=true"
        )
    if not misskey_access_token:
        raise ValueError(
            "MISSKEY_ACCESS_TOKEN environment variable is required when ENABLE_MISSKEY_BOT=true"
        )
    if not misskey_bot_user_id:
        raise ValueError(
            "MISSKEY_BOT_USER_ID environment variable is required when ENABLE_MISSKEY_BOT=true"
        )

    # URLの正規化
    if not misskey_instance_url.startswith(("http://", "https://")):
        misskey_instance_url = f"https://{misskey_instance_url}"

    # カスタム緊急時相談窓口の読み込み
    crisis_hotlines = []
    hotlines_env = os.getenv("BOT_CRISIS_HOTLINES")
    if hotlines_env:
        crisis_hotlines = [line.strip() for line in hotlines_env.split(",")]

    config = YamiiMisskeyBotConfig(
        # 共通設定（ベースクラス）
        yamii_api_url=os.getenv("YAMII_API_URL", "http://localhost:8000"),
        yamii_api_timeout=int(os.getenv("YAMII_API_TIMEOUT", "30")),
        bot_name=os.getenv("BOT_NAME", "yamii"),
        bot_username=os.getenv("BOT_USERNAME", "yamii"),
        session_timeout=int(os.getenv("BOT_SESSION_TIMEOUT", "3600")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE"),
        enable_dm=os.getenv("BOT_ENABLE_DM", "true").lower() == "true",
        enable_mentions=os.getenv("BOT_ENABLE_MENTIONS", "true").lower() == "true",
        enable_timeline=os.getenv("BOT_ENABLE_TIMELINE", "false").lower() == "true",
        enable_global_timeline=os.getenv("BOT_ENABLE_GLOBAL_TIMELINE", "false").lower()
        == "true",
        # プロアクティブアウトリーチ設定
        enable_proactive_outreach=os.getenv("BOT_ENABLE_PROACTIVE", "true").lower()
        == "true",
        proactive_check_interval=int(os.getenv("BOT_PROACTIVE_INTERVAL", "3600")),
        # Misskey固有設定
        misskey_instance_url=misskey_instance_url,
        misskey_access_token=misskey_access_token,
        misskey_bot_user_id=misskey_bot_user_id,
    )

    # カスタム緊急時相談窓口を設定
    if crisis_hotlines:
        config.crisis_hotlines = crisis_hotlines

    return config


def is_bot_enabled() -> bool:
    """Misskeyボットが有効化されているかチェック"""
    return os.getenv("ENABLE_MISSKEY_BOT", "false").lower() == "true"
