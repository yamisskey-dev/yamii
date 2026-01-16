"""
API Routes
エンドポイント定義
"""

from .commands import router as commands_router
from .counseling import router as counseling_router
from .outreach import router as outreach_router
from .user import router as user_router

__all__ = [
    "counseling_router",
    "user_router",
    "outreach_router",
    "commands_router",
]
