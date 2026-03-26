"""
角色模型
"""
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime


class RoleState(SQLModel, table=True):
    """角色状态模型"""
    __tablename__ = "role_states"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    state_name: str = Field(max_length=50)
    value_type: str = Field(default="str", max_length=10)  # str, int, float
    default_value: str = Field(max_length=255)
    current_value: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    min_value: Optional[str] = Field(default=None, max_length=50)
    max_value: Optional[str] = Field(default=None, max_length=50)


class RoleBase(SQLModel):
    """角色基础模型"""
    name: str = Field(max_length=100)
    title: Optional[str] = Field(default=None, max_length=200)
    persona: str = Field(default="", max_length=10000)
    scenario: Optional[str] = Field(default=None, max_length=5000)
    user_persona: Optional[str] = Field(default=None, max_length=500)
    greeting: Optional[str] = Field(default=None, max_length=1000)
    storyline: Optional[str] = Field(default=None, max_length=5000)
    world_setting: Optional[str] = Field(default=None, max_length=10000)
    plot_milestones: Optional[str] = Field(default=None, max_length=5000)
    # 存储 JSON 字符串，格式：[{"title": "...", "description": "..."}, ...]

    # 公开信息
    public_summary: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[str] = Field(default=None, max_length=255)
    public_avatar: Optional[str] = Field(default=None, max_length=500)
    visibility: str = Field(default="public", max_length=20)  # public, private

    # 文生图设置
    appearance_tags: Optional[str] = Field(default=None, max_length=1000)
    image_style: str = Field(default="anime", max_length=50)
    clothing_state: Optional[str] = Field(default=None, max_length=500)

    # 语音设置
    voice_reference_id: Optional[str] = Field(default=None, max_length=100)

    # 系统字段
    is_system: bool = Field(default=False)
    is_active: bool = Field(default=True)


class Role(RoleBase, table=True):
    """角色数据库模型"""
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RoleCreate(RoleBase):
    """角色创建请求模型"""
    states: Optional[List[dict]] = Field(default=None)


class RoleUpdate(SQLModel):
    """角色更新请求模型"""
    name: Optional[str] = Field(default=None, max_length=100)
    title: Optional[str] = Field(default=None, max_length=200)
    persona: Optional[str] = Field(default=None, max_length=10000)
    scenario: Optional[str] = Field(default=None, max_length=5000)
    user_persona: Optional[str] = Field(default=None, max_length=500)
    greeting: Optional[str] = Field(default=None, max_length=1000)
    storyline: Optional[str] = Field(default=None, max_length=5000)
    world_setting: Optional[str] = Field(default=None, max_length=10000)
    plot_milestones: Optional[str] = Field(default=None, max_length=5000)
    public_summary: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[str] = Field(default=None, max_length=255)
    public_avatar: Optional[str] = Field(default=None, max_length=500)
    visibility: Optional[str] = Field(default=None, max_length=20)
    appearance_tags: Optional[str] = Field(default=None, max_length=1000)
    image_style: Optional[str] = Field(default=None, max_length=50)
    clothing_state: Optional[str] = Field(default=None, max_length=500)
    voice_reference_id: Optional[str] = Field(default=None, max_length=100)
    states: Optional[List[dict]] = Field(default=None)


class RoleResponse(RoleBase):
    """角色响应模型"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    state_count: Optional[int] = Field(default=0)


class RoleListResponse(SQLModel):
    """角色列表响应"""
    success: bool
    data: List[RoleResponse]
    is_logged_in: bool
