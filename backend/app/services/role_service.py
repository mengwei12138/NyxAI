"""
角色服务
"""
from sqlmodel import Session, select, func
from typing import List, Optional
from app.models import Role, RoleCreate, RoleUpdate, RoleResponse, RoleState, User


class RoleService:
    """角色服务类"""

    @staticmethod
    def _normalize_state(state_data: dict) -> dict:
        """
        将前端/AI 返回的 state 格式统一转换为 RoleState 数据库字段格式。
        前端格式: {name, type, value, defaultValue, description}
        AI 格式:  {state_name, display_name, state_value, default_value, min_value, max_value}
        DB 格式:  {state_name, value_type, current_value, default_value, description, min_value, max_value}
        """
        # 字段来源优先级：前端字段 > AI字段 > 空
        state_name = (
            state_data.get("display_name") or
            state_data.get("name") or
            state_data.get("state_name") or
            "未命名"
        )
        raw_type = state_data.get("type") or "string"
        value_type = "int" if raw_type in (
            "number", "int", "integer") else "str"

        current_value = str(
            state_data.get("value") or
            state_data.get("state_value") or
            state_data.get("default_value") or
            state_data.get("defaultValue") or
            "0"
        )
        default_value = str(
            state_data.get("defaultValue") or
            state_data.get("default_value") or
            current_value
        )
        description = state_data.get("description") or None
        min_value = str(state_data["min_value"]) if state_data.get(
            "min_value") is not None else None
        max_value = str(state_data["max_value"]) if state_data.get(
            "max_value") is not None else None

        return {
            "state_name": state_name,
            "value_type": value_type,
            "current_value": current_value,
            "default_value": default_value,
            "description": description,
            "min_value": min_value,
            "max_value": max_value,
        }

    @classmethod
    async def get_roles(
        cls,
        session: Session,
        user_id: Optional[int] = None,
        view_mode: str = "public",
        is_admin: bool = False
    ) -> List[RoleResponse]:
        """获取角色列表"""
        if view_mode == "my" and user_id:
            # 获取我的角色（包括私密）
            # 普通用户排除系统预设角色；管理员可见自己名下的所有角色（含系统角色）
            where_conditions = [Role.user_id ==
                                user_id, Role.is_active == True]
            if not is_admin:
                where_conditions.append(Role.is_system == False)
            statement = (
                select(Role, func.count(RoleState.id).label("state_count"))
                .outerjoin(RoleState, RoleState.role_id == Role.id)
                .where(*where_conditions)
                .group_by(Role.id)
                .order_by(Role.created_at.desc())
            )
        else:
            # 获取公开角色（包括系统预设）
            statement = (
                select(Role, func.count(RoleState.id).label("state_count"))
                .outerjoin(RoleState, RoleState.role_id == Role.id)
                .where(Role.visibility == "public", Role.is_active == True)
                .group_by(Role.id)
                .order_by(Role.created_at.desc())
            )

        results = session.exec(statement).all()
        roles = []
        for role, state_count in results:
            role_data = RoleResponse.model_validate(role)
            role_data.state_count = state_count
            roles.append(role_data)
        return roles

    @classmethod
    async def get_role(cls, session: Session, role_id: int) -> Optional[Role]:
        """获取单个角色"""
        return session.get(Role, role_id)

    @classmethod
    async def create_role(cls, session: Session, user_id: int, data: RoleCreate) -> Role:
        """创建角色"""
        # 创建角色
        role_data = data.model_dump(exclude={"states"})
        role = Role(**role_data, user_id=user_id)
        session.add(role)
        session.commit()
        session.refresh(role)

        # 创建状态
        if data.states:
            for state_data in data.states:
                state = RoleState(
                    role_id=role.id,
                    **cls._normalize_state(state_data)
                )
                session.add(state)
            session.commit()

        return role

    @classmethod
    async def update_role(
        cls,
        session: Session,
        role_id: int,
        user_id: int,
        data: RoleUpdate
    ) -> Role:
        """更新角色"""
        role = session.get(Role, role_id)
        if not role:
            raise ValueError("角色不存在")
        if role.user_id != user_id:
            raise ValueError("无权修改此角色")

        # 更新角色字段
        update_data = data.model_dump(exclude_unset=True, exclude={"states"})
        for key, value in update_data.items():
            setattr(role, key, value)

        # 更新状态
        if data.states is not None:
            # 删除旧状态
            statement = select(RoleState).where(RoleState.role_id == role_id)
            old_states = session.exec(statement).all()
            for state in old_states:
                session.delete(state)

            # 创建新状态
            for state_data in data.states:
                state = RoleState(
                    role_id=role_id,
                    **cls._normalize_state(state_data)
                )
                session.add(state)

        session.commit()
        session.refresh(role)
        return role

    @classmethod
    async def delete_role(cls, session: Session, role_id: int, user_id: int) -> bool:
        """删除角色（软删除）"""
        role = session.get(Role, role_id)
        if not role:
            raise ValueError("角色不存在")
        if role.user_id != user_id:
            raise ValueError("无权删除此角色")

        role.is_active = False
        session.commit()
        return True

    @classmethod
    async def get_role_states(cls, session: Session, role_id: int) -> List[RoleState]:
        """获取角色状态"""
        statement = select(RoleState).where(RoleState.role_id == role_id)
        return session.exec(statement).all()
