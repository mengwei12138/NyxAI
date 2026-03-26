"""
审计日志服务
"""
import json
from sqlmodel import Session
from app.models.audit import AuditLog, AuditLogCreate
from app.core.logger import get_logger

logger = get_logger("audit")


class AuditService:
    """审计日志服务"""

    @staticmethod
    def log(
        session: Session,
        admin_id: int,
        admin_username: str,
        action: str,
        resource_type: str,
        resource_id: int = None,
        details: dict = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> AuditLog:
        """
        记录审计日志

        Args:
            session: 数据库会话
            admin_id: 管理员ID
            admin_username: 管理员用户名
            action: 操作类型
            resource_type: 资源类型
            resource_id: 资源ID
            details: 操作详情字典
            ip_address: IP地址
            user_agent: User-Agent
        """
        try:
            log = AuditLog(
                admin_id=admin_id,
                admin_username=admin_username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=json.dumps(
                    details, ensure_ascii=False) if details else "{}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.add(log)
            session.commit()

            # 同时输出到日志
            logger.info(
                f"[AUDIT] {admin_username} {action} {resource_type}/{resource_id}",
                extra={
                    "admin_id": admin_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "details": details
                }
            )

            return log
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
            # 审计日志失败不应影响主业务
            return None

    @staticmethod
    def log_user_recharge(
        session: Session,
        admin_id: int,
        admin_username: str,
        user_id: int,
        username: str,
        amount: int,
        ip_address: str = None
    ):
        """记录用户充值操作"""
        return AuditService.log(
            session=session,
            admin_id=admin_id,
            admin_username=admin_username,
            action="recharge",
            resource_type="user",
            resource_id=user_id,
            details={
                "target_username": username,
                "amount": amount,
                "operation": f"为用户 {username} 充值 {amount} 积分"
            },
            ip_address=ip_address
        )

    @staticmethod
    def log_user_ban(
        session: Session,
        admin_id: int,
        admin_username: str,
        user_id: int,
        username: str,
        is_banned: bool,
        ip_address: str = None
    ):
        """记录用户封禁/解封操作"""
        action = "ban" if is_banned else "unban"
        return AuditService.log(
            session=session,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource_type="user",
            resource_id=user_id,
            details={
                "target_username": username,
                "is_banned": is_banned,
                "operation": f"{'封禁' if is_banned else '解封'}用户 {username}"
            },
            ip_address=ip_address
        )

    @staticmethod
    def log_role_delete(
        session: Session,
        admin_id: int,
        admin_username: str,
        role_id: int,
        role_name: str,
        ip_address: str = None
    ):
        """记录角色删除操作"""
        return AuditService.log(
            session=session,
            admin_id=admin_id,
            admin_username=admin_username,
            action="delete",
            resource_type="role",
            resource_id=role_id,
            details={
                "role_name": role_name,
                "operation": f"删除角色 {role_name}"
            },
            ip_address=ip_address
        )

    @staticmethod
    def log_role_toggle(
        session: Session,
        admin_id: int,
        admin_username: str,
        role_id: int,
        role_name: str,
        is_active: bool,
        ip_address: str = None
    ):
        """记录角色启用/禁用操作"""
        action = "activate" if is_active else "deactivate"
        return AuditService.log(
            session=session,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource_type="role",
            resource_id=role_id,
            details={
                "role_name": role_name,
                "is_active": is_active,
                "operation": f"{'启用' if is_active else '禁用'}角色 {role_name}"
            },
            ip_address=ip_address
        )

    @staticmethod
    def log_admin_login(
        session: Session,
        admin_id: int,
        admin_username: str,
        success: bool,
        ip_address: str = None,
        user_agent: str = None
    ):
        """记录管理员登录"""
        return AuditService.log(
            session=session,
            admin_id=admin_id,
            admin_username=admin_username,
            action="login_success" if success else "login_failed",
            resource_type="system",
            details={
                "success": success,
                "operation": "管理员登录" + ("成功" if success else "失败")
            },
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def log_admin_logout(
        session: Session,
        admin_id: int,
        admin_username: str,
        ip_address: str = None
    ):
        """记录管理员登出"""
        return AuditService.log(
            session=session,
            admin_id=admin_id,
            admin_username=admin_username,
            action="logout",
            resource_type="system",
            details={
                "operation": "管理员登出"
            },
            ip_address=ip_address
        )
