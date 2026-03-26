"""
审计日志模型
记录管理后台的所有操作
"""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class AuditLog(SQLModel, table=True):
    """审计日志表"""
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 操作者信息
    admin_id: int = Field(index=True, description="管理员ID")
    admin_username: str = Field(description="管理员用户名")

    # 操作信息
    action: str = Field(
        description="操作类型: create/update/delete/login/logout/recharge/ban")
    resource_type: str = Field(description="资源类型: user/role/credit/system")
    resource_id: Optional[int] = Field(default=None, description="资源ID")

    # 操作详情
    details: str = Field(description="操作详情（JSON格式）")
    ip_address: Optional[str] = Field(default=None, description="操作者IP地址")
    user_agent: Optional[str] = Field(default=None, description="User-Agent")

    # 时间戳
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="操作时间")


class AuditLogCreate(SQLModel):
    """创建审计日志请求"""
    admin_id: int
    admin_username: str
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    details: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
