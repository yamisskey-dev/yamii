"""
Navi Misskey Bot Configuration
naviのMisskeyボット設定
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class NaviMisskeyBotConfig:
    """Navi Misskeyボット設定クラス"""
    
    # Misskeyサーバー設定
    misskey_instance_url: str
    misskey_access_token: str
    
    # Naviサーバー設定
    navi_api_url: str = "http://localhost:8000"
    
    # ボット動作設定
    bot_name: str = "navi"
    bot_display_name: str = "Navi - 人生相談AI"
    
    # ログ設定
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # タイムアウト設定
    request_timeout: int = 30
    session_timeout: int = 30 * 60  # 30分
    
    # 応答設定
    enable_crisis_support: bool = True
    crisis_hotline_numbers: list = None
    
    def __post_init__(self):
        """設定の後処理"""
        if self.crisis_hotline_numbers is None:
            self.crisis_hotline_numbers = [
                "いのちの電話: 0570-783-556",
                "こころの健康相談統一ダイヤル: 0570-064-556"
            ]


def load_config() -> NaviMisskeyBotConfig:
    """環境変数から設定を読み込む"""
    
    # Misskeyボット有効化チェック
    enable_bot = os.getenv("ENABLE_MISSKEY_BOT", "false").lower() == "true"
    if not enable_bot:
        raise ValueError("ENABLE_MISSKEY_BOT is set to false. Set it to true to enable the Misskey bot.")
    
    misskey_instance_url = os.getenv("MISSKEY_INSTANCE_URL")
    misskey_access_token = os.getenv("MISSKEY_ACCESS_TOKEN")
    
    if not misskey_instance_url:
        raise ValueError("MISSKEY_INSTANCE_URL environment variable is required when ENABLE_MISSKEY_BOT=true")
    
    if not misskey_access_token:
        raise ValueError("MISSKEY_ACCESS_TOKEN environment variable is required when ENABLE_MISSKEY_BOT=true")
    
    # カスタム緊急時相談窓口の読み込み
    crisis_hotlines = []
    hotlines_env = os.getenv("BOT_CRISIS_HOTLINES")
    if hotlines_env:
        crisis_hotlines = [line.strip() for line in hotlines_env.split(",")]
    
    config = NaviMisskeyBotConfig(
        misskey_instance_url=misskey_instance_url,
        misskey_access_token=misskey_access_token,
        navi_api_url=os.getenv("NAVI_API_URL", "http://localhost:8000"),
        bot_name=os.getenv("BOT_NAME", "navi"),
        bot_display_name=os.getenv("BOT_DISPLAY_NAME", "Navi - 人生相談AI"),
        log_level=os.getenv("BOT_LOG_LEVEL", "INFO"),
        log_file=os.getenv("BOT_LOG_FILE"),
        request_timeout=int(os.getenv("BOT_REQUEST_TIMEOUT", "30")),
        session_timeout=int(os.getenv("BOT_SESSION_TIMEOUT", "1800")),
        enable_crisis_support=os.getenv("BOT_ENABLE_CRISIS_SUPPORT", "true").lower() == "true"
    )
    
    # カスタム緊急時相談窓口を設定
    if crisis_hotlines:
        config.crisis_hotline_numbers = crisis_hotlines
    
    return config


def is_bot_enabled() -> bool:
    """Misskeyボットが有効化されているかチェック"""
    return os.getenv("ENABLE_MISSKEY_BOT", "false").lower() == "true"