"""
Navi Bot Package
naviボット機能のパッケージ
"""

from .misskey import NaviMisskeyBot, NaviMisskeyBotConfig, load_config

__version__ = "1.0.0"
__author__ = "Navi Team"
__description__ = "Bot implementations for Navi life counseling service"

__all__ = [
    "NaviMisskeyBot",
    "NaviMisskeyBotConfig", 
    "load_config"
]