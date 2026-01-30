"""
API Routes
エンドポイント定義
"""

from .auth import router as auth_router
from .commands import router as commands_router
from .counseling import router as counseling_router
from .title import router as title_router
from .user import router as user_router
from .user_data import router as user_data_router

__all__ = [
    "auth_router",
    "counseling_router",
    "title_router",
    "user_router",
    "user_data_router",
    "commands_router",
]
