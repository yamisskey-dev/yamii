"""
API Routes
エンドポイント定義
"""

from .counseling import router as counseling_router
from .user import router as user_router
from .outreach import router as outreach_router
from .commands import router as commands_router

__all__ = [
    "counseling_router",
    "user_router",
    "outreach_router",
    "commands_router",
]
