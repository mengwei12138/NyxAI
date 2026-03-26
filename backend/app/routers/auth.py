"""
认证路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlmodel import Session
from app.database import get_session
from app.models import UserCreate, UserLogin, UserChangePassword, UserUpdateRequest, TokenResponse, User
from app.services import AuthService
from app.dependencies import get_current_user
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register")
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: UserCreate,
    session: Session = Depends(get_session)
):
    """用户注册 - 返回简单成功信息"""
    try:
        result = await AuthService.register(session, data)
        return {
            "success": True,
            "message": result["message"],
            "user_id": result["id"],
            "username": result["username"]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: UserLogin,
    session: Session = Depends(get_session)
):
    """用户登录"""
    try:
        return await AuthService.login(session, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me")
async def get_me(
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取当前用户信息"""
    from app.services import CreditService

    # 获取用户积分信息
    credits = await CreditService.get_balance(session, current_user.id)

    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "is_admin": current_user.is_admin,
            "credits": credits.balance,
            "total_earned": credits.total_earned,
            "total_spent": credits.total_spent
        }
    }


@router.post("/change-password")
async def change_password(
    data: UserChangePassword,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """修改用户密码"""
    try:
        result = await AuthService.change_password(
            session, current_user.id, data.old_password, data.new_password
        )
        return {
            "success": True,
            "message": result["message"]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/me")
async def update_me(
    data: UserUpdateRequest,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """更新当前用户信息（username、email）"""
    from sqlmodel import select
    from app.models import User

    user = session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新 username
    if data.username is not None and data.username.strip():
        new_username = data.username.strip()
        if new_username != user.username:
            existing = session.exec(
                select(User).where(User.username == new_username)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已被占用"
                )
            user.username = new_username

    # 更新 email
    if data.email is not None:
        user.email = data.email or None

    from datetime import datetime
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "success": True,
        "message": "信息已更新",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    }


@router.get("/stats")
async def get_user_stats(
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取用户统计数据"""
    from sqlmodel import select, func
    from app.models import Role, ChatMessage, CreditTransaction, CreditType

    # 统计创建的角色数
    role_count = session.exec(
        select(func.count(Role.id)).where(Role.user_id == current_user.id)
    ).first() or 0

    # 统计聊天消息数
    chat_count = session.exec(
        select(func.count(ChatMessage.id)).where(
            ChatMessage.user_id == current_user.id)
    ).first() or 0

    # 统计主动生成图片次数（以 TTI 类型的积分消耗记录为准）
    image_count = session.exec(
        select(func.count(CreditTransaction.id)).where(
            (CreditTransaction.user_id == current_user.id) &
            (CreditTransaction.type == CreditType.TTI)
        )
    ).first() or 0

    return {
        "success": True,
        "data": {
            "roles": role_count,
            "chats": chat_count,
            "images": image_count
        }
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    session: Session = Depends(get_session)
):
    """
    使用 Refresh Token 获取新的 Access Token

    Args:
        refresh_token: 刷新令牌
    """
    from app.dependencies.auth import verify_token, create_access_token, create_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS
    from app.services import CreditService
    from app.core.cache import is_token_blacklisted

    # 检查 Refresh Token 是否在黑名单中
    if await is_token_blacklisted(refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已注销",
        )

    # 验证 Refresh Token
    try:
        user_id = verify_token(refresh_token, token_type="refresh")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌无效或已过期",
        )

    # 获取用户信息
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )

    # 获取用户积分
    credits = await CreditService.get_balance(session, user.id)

    # 创建新的令牌对
    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=7200,
        user_id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        credits=credits.balance,
        total_earned=credits.total_earned,
        total_spent=credits.total_spent
    )


@router.post("/logout")
async def logout(
    current_user=Depends(get_current_user),
    authorization: str = Header(None)
):
    """
    用户注销

    将当前 Access Token 加入黑名单，使其立即失效
    """
    from app.core.cache import add_token_to_blacklist
    from app.dependencies.auth import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        # 将 Token 加入黑名单，过期时间与 Token 有效期相同
        await add_token_to_blacklist(token, ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    return {
        "success": True,
        "message": "注销成功"
    }


@router.post("/bot/register-or-login", deprecated=True)
async def bot_register_or_login_deprecated(
    telegram_id: int,
    first_name: str,
    username: str = None,
):
    """
    [已废弃] 请改用 POST /api/bot/auth
    此接口与 /api/bot/auth 功能重复，统一由 bot.py 维护。
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="此接口已废弃，请改用 POST /api/bot/auth"
    )
