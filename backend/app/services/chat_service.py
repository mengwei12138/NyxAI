"""
聊天服务
"""
from sqlmodel import Session, select
from typing import List, Optional, Dict
from datetime import datetime
from app.models import (
    ChatMessage, ChatMessageCreate, ChatRequest, ChatHistory, MessageRole,
    UserRoleState, RoleState, UserChatSettings
)


class ChatService:
    """聊天服务类"""

    @classmethod
    async def get_chat_history(
        cls,
        session: Session,
        role_id: int,
        user_id: int,
        limit: int = 20,
        before_id: int = 0
    ) -> List[ChatMessage]:
        """获取聊天历史（分页）
        before_id=0 返回最新 limit 条；
        before_id>0 返回该 id 之前（更早）的 limit 条，用于上拉加载更多。
        """
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.role_id == role_id,
                ChatMessage.user_id == user_id
            )
        )
        if before_id > 0:
            stmt = stmt.where(ChatMessage.id < before_id)
        stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit)
        results = session.exec(stmt).all()
        return list(reversed(results))  # 按时间正序返回

    @classmethod
    async def create_message(
        cls,
        session: Session,
        role_id: int,
        user_id: int,
        role: MessageRole,
        content: str,
        image_url: Optional[str] = None
    ) -> ChatMessage:
        """创建消息"""
        message = ChatMessage(
            role_id=role_id,
            user_id=user_id,
            role=role,
            content=content,
            image_url=image_url
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        return message

    @classmethod
    async def clear_history(cls, session: Session, role_id: int, user_id: int) -> bool:
        """清空聊天历史"""
        statement = select(ChatMessage).where(
            ChatMessage.role_id == role_id,
            ChatMessage.user_id == user_id
        )
        messages = session.exec(statement).all()
        for msg in messages:
            session.delete(msg)
        session.commit()
        return True

    @classmethod
    def format_history_for_prompt(cls, messages: List[ChatMessage]) -> List[ChatHistory]:
        """格式化历史记录用于提示词"""
        return [
            ChatHistory(role=msg.role.value, content=msg.content)
            for msg in messages
        ]

    @classmethod
    async def get_user_role_states(
        cls,
        session: Session,
        user_id: int,
        role_id: int
    ) -> Dict[str, str]:
        """获取用户对特定角色的状态实例（用户隔离）"""
        # 获取角色默认状态定义
        statement = select(RoleState).where(RoleState.role_id == role_id)
        default_states = session.exec(statement).all()

        # 获取用户的状态实例
        statement = select(UserRoleState).where(
            UserRoleState.user_id == user_id,
            UserRoleState.role_id == role_id
        )
        user_states = session.exec(statement).all()

        # 构建状态字典：优先使用用户自定义值，否则使用默认值
        states = {}
        user_state_map = {s.state_name: s.state_value for s in user_states}

        for default in default_states:
            state_name = default.state_name
            # 如果用户有自定义值，使用自定义值；否则使用默认值
            state_value = user_state_map.get(state_name, default.default_value)
            states[state_name] = {
                'value': state_value,
                'desc': default.description or '',
                'min': default.min_value,
                'max': default.max_value
            }

        return states

    @classmethod
    async def update_user_role_state(
        cls,
        session: Session,
        user_id: int,
        role_id: int,
        state_name: str,
        state_value: str
    ) -> UserRoleState:
        """更新用户对特定角色的状态值"""
        # 查找现有状态
        statement = select(UserRoleState).where(
            UserRoleState.user_id == user_id,
            UserRoleState.role_id == role_id,
            UserRoleState.state_name == state_name
        )
        existing = session.exec(statement).first()

        if existing:
            # 更新现有状态
            existing.state_value = state_value
            existing.updated_at = datetime.utcnow()
            session.add(existing)
        else:
            # 创建新状态
            new_state = UserRoleState(
                user_id=user_id,
                role_id=role_id,
                state_name=state_name,
                state_value=state_value
            )
            session.add(new_state)

        session.commit()
        return existing or new_state

    @classmethod
    async def reset_user_role_states(
        cls,
        session: Session,
        user_id: int,
        role_id: int
    ) -> bool:
        """重置用户对特定角色的所有状态为默认值"""
        # 删除用户的所有状态实例
        statement = select(UserRoleState).where(
            UserRoleState.user_id == user_id,
            UserRoleState.role_id == role_id
        )
        user_states = session.exec(statement).all()

        for state in user_states:
            session.delete(state)

        session.commit()
        return True

    @classmethod
    async def get_user_chat_settings(
        cls,
        session: Session,
        user_id: int,
        role_id: int
    ) -> Optional[UserChatSettings]:
        """获取用户聊天自定义设置"""
        statement = select(UserChatSettings).where(
            UserChatSettings.user_id == user_id,
            UserChatSettings.role_id == role_id
        )
        return session.exec(statement).first()

    @classmethod
    async def save_user_chat_settings(
        cls,
        session: Session,
        user_id: int,
        role_id: int,
        appearance_tags: Optional[str] = None,
        voice_ref: Optional[str] = None,
        image_style: Optional[str] = None
    ) -> UserChatSettings:
        """保存用户聊天自定义设置（upsert）"""
        statement = select(UserChatSettings).where(
            UserChatSettings.user_id == user_id,
            UserChatSettings.role_id == role_id
        )
        existing = session.exec(statement).first()

        if existing:
            if appearance_tags is not None:
                existing.appearance_tags = appearance_tags
            if voice_ref is not None:
                existing.voice_ref = voice_ref
            if image_style is not None:
                existing.image_style = image_style
            existing.updated_at = datetime.utcnow()
            session.add(existing)
        else:
            existing = UserChatSettings(
                user_id=user_id,
                role_id=role_id,
                appearance_tags=appearance_tags,
                voice_ref=voice_ref,
                image_style=image_style
            )
            session.add(existing)

        session.commit()
        session.refresh(existing)
        return existing
