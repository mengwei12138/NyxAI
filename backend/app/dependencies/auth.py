"""
认证依赖
支持 Access Token + Refresh Token 双令牌机制
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlmodel import Session
from datetime import datetime, timedelta
from app.config import get_settings
from app.database import get_session
from app.models import User
from app.core.cache import is_token_blacklisted

settings = get_settings()
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

# Token 配置
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # Access Token 2小时
REFRESH_TOKEN_EXPIRE_DAYS = 7      # Refresh Token 7天


def create_access_token(user_id: int) -> str:
    """创建JWT访问令牌（短期有效）"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access"
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int) -> str:
    """创建JWT刷新令牌（长期有效）"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> int:
    """
    验证JWT令牌并返回用户ID

    Args:
        token: JWT令牌
        token_type: 期望的令牌类型 (access/refresh)
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY,
                             algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type_claim: str = payload.get("type", "access")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查令牌类型
        if token_type_claim != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"令牌类型错误，期望 {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return int(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    """获取当前登录用户（必需）"""
    token = credentials.credentials

    # 检查 Token 是否在黑名单中
    if await is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已注销",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = verify_token(token, token_type="access")

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security_optional),
    session: Session = Depends(get_session)
) -> User:
    """获取当前登录用户（可选）"""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, session)
    except Exception:
        return None
