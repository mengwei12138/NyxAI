"""
积分系统模型
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CreditType(str, Enum):
    """积分变动类型"""
    RECHARGE = "recharge"          # 充值
    CHAT = "chat"                  # 聊天消费
    TTS = "tts"                    # TTS语音消费
    TTI = "tti"                    # 文生图消费
    CREATE_ROLE = "create_role"    # 创建角色消费
    POLISH = "polish"              # AI润色消费
    REFUND = "refund"              # 退款
    BONUS = "bonus"                # 奖励/赠送


class UserCredits(SQLModel, table=True):
    """用户积分余额表"""
    __tablename__ = "user_credits"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    balance: int = Field(default=0, description="当前积分余额")
    total_earned: int = Field(default=0, description="累计获得积分")
    total_spent: int = Field(default=0, description="累计消费积分")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CreditTransaction(SQLModel, table=True):
    """积分交易记录表"""
    __tablename__ = "credit_transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    amount: int = Field(description="变动金额(正数为增加,负数为减少)")
    type: CreditType = Field(description="交易类型")
    description: str = Field(max_length=255, description="交易描述")
    related_id: Optional[int] = Field(
        default=None, description="关联ID(如角色ID、消息ID等)")
    balance_after: int = Field(description="交易后余额")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreditCost(SQLModel):
    """积分消耗配置"""
    CHAT: int = 1          # 每次聊天消耗
    TTS: int = 5           # 每次TTS消耗
    TTI: int = 10          # 每次文生图消耗
    CREATE_ROLE: int = 50  # 创建角色消耗


class CreditBalanceResponse(SQLModel):
    """积分余额响应"""
    balance: int
    total_earned: int
    total_spent: int


class CreditTransactionResponse(SQLModel):
    """交易记录响应"""
    id: int
    amount: int
    type: CreditType
    description: str
    created_at: datetime


class CreditCostResponse(SQLModel):
    """积分消耗配置响应"""
    chat: int
    tts: int
    tti: int
    create_role: int


class CreditCheckResult(SQLModel):
    """积分检查结果"""
    sufficient: bool
    balance: int
    required: int
    message: Optional[str] = None
