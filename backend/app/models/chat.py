"""
聊天模型
"""
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageBase(SQLModel):
    """聊天消息基础模型"""
    role: MessageRole
    content: str = Field(max_length=20000)
    image_url: Optional[str] = Field(default=None, max_length=1000)
    audio_url: Optional[str] = Field(default=None, max_length=1000)


class ChatMessage(ChatMessageBase, table=True):
    """聊天消息数据库模型"""
    __tablename__ = "chat_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessageCreate(SQLModel):
    """创建聊天消息请求"""
    content: str = Field(min_length=1, max_length=20000)


class ChatMessageResponse(ChatMessageBase):
    """聊天消息响应"""
    id: int
    role_id: int
    user_id: int
    created_at: datetime

    def model_dump(self, **kwargs):
        """自定义序列化，将枚举转为字符串"""
        data = super().model_dump(**kwargs)
        if isinstance(data.get('role'), MessageRole):
            data['role'] = data['role'].value
        return data


class ChatHistory(SQLModel):
    """聊天历史"""
    role: str
    content: str


class ChatRequest(SQLModel):
    """聊天请求"""
    message: str = Field(min_length=1, max_length=20000)
    story_mode: bool = False


class ChatResponse(SQLModel):
    """聊天响应"""
    success: bool
    message: str
    data: Optional[ChatMessageResponse] = None
    choices: List[str] = []


class TTSRequest(SQLModel):
    """TTS请求"""
    text: str = Field(min_length=1, max_length=5000)
    role_id: Optional[int] = None
    message_id: Optional[int] = None    # 用于生成后写回 audio_url 到消息记录
    voice_ref: Optional[str] = None  # 用户在聊天设置中选择的音色 reference_id


class TTSResponse(SQLModel):
    """TTS响应"""
    success: bool
    audio_url: Optional[str] = None  # OSS/CDN 公网 URL（优先）
    audio: Optional[str] = None      # base64编码（OSS 未配置时回退）
    format: str = "mp3"
    error: Optional[str] = None


class UserRoleState(SQLModel, table=True):
    """用户角色状态实例 - 每个用户对每个角色有独立的状态"""
    __tablename__ = "user_role_states"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    state_name: str = Field(max_length=50)
    state_value: str = Field(max_length=255)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserChatSettings(SQLModel, table=True):
    """用户聊天自定义设置 - 属于用户对某个角色的个性化配置"""
    __tablename__ = "user_chat_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    # 用户在聊天设置面板自定义的外貌（覆盖角色默认外貌）
    appearance_tags: Optional[str] = Field(default=None, max_length=2000)
    # 用户选择的声音参考
    voice_ref: Optional[str] = Field(default=None, max_length=200)
    # 用户选择的画风（覆盖角色默认画风）
    image_style: Optional[str] = Field(default=None, max_length=50)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserRoleStateResponse(SQLModel):
    """用户角色状态响应"""
    state_name: str
    state_value: str
    updated_at: datetime


class ResetStatesRequest(SQLModel):
    """重置状态请求"""
    role_id: int


class ResetStatesResponse(SQLModel):
    """重置状态响应"""
    success: bool
    message: str
