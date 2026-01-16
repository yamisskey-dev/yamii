"""
Domain Ports
依存性逆転のためのインターフェース定義
"""

from .storage_port import IStorage
from .ai_port import IAIProvider
from .platform_port import IPlatformAdapter

__all__ = [
    "IStorage",
    "IAIProvider",
    "IPlatformAdapter",
]
