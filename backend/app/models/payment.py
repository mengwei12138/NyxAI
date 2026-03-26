"""
支付订单模型（爱发电版）
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PaymentPackage(SQLModel, table=True):
    """充值套餐配置表（持久化，后台可修改）"""
    __tablename__ = "payment_packages"

    id: Optional[int] = Field(default=None, primary_key=True)
    package_id: str = Field(unique=True, index=True, max_length=32,
                            description="套餐唯一标识，如 starter/standard/pro")
    plan_id: str = Field(max_length=128, description="爱发电方案ID，生成跳转链接用")
    name: str = Field(max_length=64, description="套餐名称")
    amount: float = Field(description="支付金额（元）")
    credits: int = Field(description="到账积分")
    desc: str = Field(default="", max_length=255, description="套餐描述")
    popular: bool = Field(default=False, description="是否推荐（高亮显示）")
    is_active: bool = Field(default=True, description="是否启用")
    sort_order: int = Field(default=0, description="排序，越小越靠前")


class PaymentStatus(str, Enum):
    PENDING = "pending"       # 待支付（前端跳转后等待 Webhook）
    PAID = "paid"             # 已支付（Webhook 确认）
    FAILED = "failed"         # 失败


class PaymentOrder(SQLModel, table=True):
    """支付订单表（基于爱发电 Webhook 被动确认）"""
    __tablename__ = "payment_orders"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 爱发电全局唯一订单号（Webhook 中的 out_trade_no）
    out_trade_no: Optional[str] = Field(
        default=None, unique=True, index=True, max_length=64,
        description="爱发电订单号")

    # 用于关联内部用户的自定义字段（custom_order_id = nyx_{user_id}_{ts}）
    custom_order_id: str = Field(
        unique=True, index=True, max_length=64,
        description="爱发电 custom_order_id，同时作为内部流水号")

    user_id: int = Field(foreign_key="users.id", index=True)

    # 套餐信息（前端生成链接时写入 plan_id，Webhook 回填）
    plan_id: Optional[str] = Field(
        default=None, max_length=128, description="爱发电方案ID")
    package_id: str = Field(max_length=32, description="本地套餐ID")
    package_name: str = Field(max_length=64, description="套餐名称")
    amount: float = Field(description="支付金额（元）")
    credits: int = Field(description="到账积分")

    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING, description="订单状态")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = Field(default=None, description="支付完成时间")


# ---- 响应 Schema ----

class PackageInfo(SQLModel):
    id: str
    plan_id: str           # 爱发电方案ID（生成跳转链接用）
    name: str
    amount: float
    credits: int
    desc: str
    popular: bool = False


class OrderStatusResponse(SQLModel):
    custom_order_id: str
    status: PaymentStatus
    credits: Optional[int] = None
    message: str
