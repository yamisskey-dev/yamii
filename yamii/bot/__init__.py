"""
Yamii Bot Package
Yamiiボット機能のパッケージ
"""

from __future__ import annotations

from .misskey import YamiiMisskeyBot, YamiiMisskeyBotConfig, load_config

__version__ = "1.0.0"
__author__ = "Yamii Team"
__description__ = "Bot implementations for Yamii life counseling service"

__all__ = ["YamiiMisskeyBot", "YamiiMisskeyBotConfig", "load_config"]
