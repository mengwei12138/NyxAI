"""
路由模块
"""
from .auth import router as auth_router
from .roles import router as roles_router
from .chat import router as chat_router
from .bot import router as bot_router
from .credits import router as credits_router
from .payment import router as payment_router
from .checkin import router as checkin_router

__all__ = ["auth_router", "roles_router",
           "chat_router", "bot_router", "credits_router", "payment_router", "checkin_router"]
