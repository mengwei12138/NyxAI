"""
管理后台鉴权 - 基于签名 Cookie 的 Session 机制
"""
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from fastapi import Cookie, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from app.config import get_settings
from app.models import User


def create_admin_cookie(user_id: int) -> str:
    """生成签名 Cookie 值"""
    signer = TimestampSigner(get_settings().SECRET_KEY)
    return signer.sign(str(user_id)).decode()


def verify_admin_cookie(admin_session: str) -> int | None:
    """验证签名 Cookie，返回 user_id，无效返回 None"""
    if not admin_session:
        return None
    signer = TimestampSigner(get_settings().SECRET_KEY)
    try:
        user_id = int(signer.unsign(admin_session, max_age=86400))
        return user_id
    except (BadSignature, SignatureExpired, ValueError):
        return None


def get_admin_user_id(admin_session: str = Cookie(None)) -> int | None:
    """
    FastAPI 依赖注入：从 Cookie 取出管理员 user_id。
    路由层根据返回值判断是否重定向，不在此处抛出异常（避免被 FastAPI 处理为 422）。
    """
    return verify_admin_cookie(admin_session)
