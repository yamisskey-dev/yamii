"""
Domain Ports
依存性逆転のためのインターフェース定義
"""

from .ai_port import IAIProvider
from .platform_port import IPlatformAdapter
from .storage_port import IStorage

__all__ = [
    "IStorage",
    "IAIProvider",
    "IPlatformAdapter",
]
