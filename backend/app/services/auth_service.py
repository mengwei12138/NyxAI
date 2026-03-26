"""
认证服务
"""
from sqlmodel import Session, select
from passlib.context import CryptContext
from app.models import User, UserCreate, UserLogin, TokenResponse
from app.dependencies.auth import create_access_token, create_refresh_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """认证服务类"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)

    @classmethod
    async def register(cls, session: Session, data: UserCreate) -> dict:
        """用户注册 - 返回简化后的用户信息"""
        # 检查两次密码是否一致
        if data.password != data.confirm_password:
            raise ValueError("两次输入的密码不一致")

        # 检查用户名是否已存在
        statement = select(User).where(User.username == data.username)
        existing_user = session.exec(statement).first()
        if existing_user:
            raise ValueError("用户名已存在")

        # 创建新用户
        user = User(
            username=data.username,
            password_hash=cls.get_password_hash(data.password)
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # 返回简化信息
        return {
            "id": user.id,
            "username": user.username,
            "message": "注册成功"
        }

    @classmethod
    async def login(cls, session: Session, data: UserLogin) -> TokenResponse:
        """用户登录"""
        from app.services import CreditService

        # 查找用户
        statement = select(User).where(User.username == data.username)
        user = session.exec(statement).first()

        if not user:
            raise ValueError("用户名或密码错误")

        if not cls.verify_password(data.password, user.password_hash):
            raise ValueError("用户名或密码错误")

        if not user.is_active:
            raise ValueError("用户已被禁用")

        # 获取用户积分
        credits = await CreditService.get_balance(session, user.id)

        # 创建访问令牌和刷新令牌
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # 直接返回 TokenResponse，避免嵌套模型
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            credits=credits.balance,
            total_earned=credits.total_earned,
            total_spent=credits.total_spent
        )

    @classmethod
    async def get_user(cls, session: Session, user_id: int) -> User:
        """获取用户信息"""
        user = session.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")
        return user

    @classmethod
    async def change_password(cls, session: Session, user_id: int, old_password: str, new_password: str) -> dict:
        """修改用户密码"""
        user = await cls.get_user(session, user_id)

        # 验证旧密码
        if not cls.verify_password(old_password, user.password_hash):
            raise ValueError("原密码错误")

        # 更新密码
        user.password_hash = cls.get_password_hash(new_password)
        session.add(user)
        session.commit()
        session.refresh(user)

        return {
            "id": user.id,
            "username": user.username,
            "message": "密码修改成功"
        }
