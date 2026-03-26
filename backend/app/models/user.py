"""
用户模型
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class UserBase(SQLModel):
    """用户基础模型"""
    username: str = Field(index=True, unique=True, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)


class User(UserBase, table=True):
    """用户数据库模型"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(SQLModel):
    """用户创建请求模型"""
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    confirm_password: str = Field(min_length=6, max_length=100)


class UserLogin(SQLModel):
    """用户登录请求模型"""
    username: str
    password: str


class UserChangePassword(SQLModel):
    """用户修改密码请求模型"""
    old_password: str
    new_password: str = Field(min_length=6, max_length=100)


class UserUpdateRequest(SQLModel):
    """更新用户信息请求模型（username / email）"""
    username: Optional[str] = Field(default=None, min_length=1, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)


class TokenResponse(SQLModel):
    """Token响应模型 - 支持双令牌机制"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 7200  # Access Token 有效期（秒）
    user_id: int
    username: str
    email: Optional[str] = None
    is_admin: bool = False
    credits: int = 0
    total_earned: int = 0
    total_spent: int = 0
