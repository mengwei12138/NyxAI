"""
签到系统模型
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date, datetime


class UserCheckin(SQLModel, table=True):
    """用户签到记录表"""
    __tablename__ = "user_checkins"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    last_checkin_date: Optional[date] = Field(
        default=None, description="上次签到日期")
    streak_days: int = Field(default=0, description="当前连续签到天数 0-6")
    total_checkins: int = Field(default=0, description="累计签到次数")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CheckinStatusResponse(SQLModel):
    """签到状态响应"""
    has_checked_in_today: bool
    streak_days: int
    today_points: int
    total_checkins: int


class CheckinResultResponse(SQLModel):
    """签到结果响应"""
    success: bool
    is_new: bool
    points_earned: int
    streak_days: int
    total_checkins: int
    message: str
