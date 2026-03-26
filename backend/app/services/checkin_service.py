"""
签到服务
连续7天签到，积分递增1-7，断签重置，循环往复
"""
from datetime import date, timedelta
from sqlmodel import Session, select
from typing import Optional
from app.models import UserCheckin, CreditType
from app.services import CreditService

# 7天签到积分奖励
CHECKIN_REWARDS = [1, 2, 3, 4, 5, 6, 7]


class CheckinService:
    """签到服务类"""

    @staticmethod
    async def get_or_create_checkin(session: Session, user_id: int) -> UserCheckin:
        """获取或创建用户签到记录"""
        statement = select(UserCheckin).where(UserCheckin.user_id == user_id)
        checkin = session.exec(statement).first()

        if not checkin:
            # 新用户，last_checkin_date 为 None，首次签到时从第1天开始
            checkin = UserCheckin(
                user_id=user_id,
                last_checkin_date=None,
                streak_days=0,
                total_checkins=0
            )
            session.add(checkin)
            session.commit()
            session.refresh(checkin)

        return checkin

    @staticmethod
    def _is_consecutive(last_date: Optional[date], today: date) -> bool:
        """判断是否是连续签到（昨天签到）"""
        if last_date is None:
            return False
        return last_date == today - timedelta(days=1)

    @staticmethod
    def _is_same_day(last_date: Optional[date], today: date) -> bool:
        """判断是否是同一天"""
        if last_date is None:
            return False
        return last_date == today

    @staticmethod
    async def checkin(session: Session, user_id: int) -> dict:
        """
        执行签到

        Returns:
            {
                "success": bool,
                "is_new": bool,           # 是否新签到（非重复）
                "points_earned": int,     # 获得积分
                "streak_days": int,       # 当前连续天数（0-6）
                "total_checkins": int,    # 累计签到次数
                "message": str
            }
        """
        from datetime import datetime

        checkin_record = await CheckinService.get_or_create_checkin(session, user_id)
        today = date.today()

        # 检查今天是否已经签到（幂等）
        if CheckinService._is_same_day(checkin_record.last_checkin_date, today):
            today_points = CHECKIN_REWARDS[checkin_record.streak_days]
            return {
                "success": True,
                "is_new": False,
                "points_earned": 0,
                "streak_days": checkin_record.streak_days,
                "total_checkins": checkin_record.total_checkins,
                "message": f"今天已经签到过了，连续签到 {checkin_record.streak_days + 1} 天"
            }

        # 判断是否断签
        if CheckinService._is_consecutive(checkin_record.last_checkin_date, today):
            # 连续签到，天数+1（0-6循环）
            checkin_record.streak_days = (checkin_record.streak_days + 1) % 7
        else:
            # 断签，重置为第1天
            checkin_record.streak_days = 0

        # 计算今日奖励积分
        points_earned = CHECKIN_REWARDS[checkin_record.streak_days]

        # 更新签到记录
        checkin_record.last_checkin_date = today
        checkin_record.total_checkins += 1
        checkin_record.updated_at = datetime.utcnow()
        session.add(checkin_record)

        # 发放积分
        await CreditService.recharge(
            session,
            user_id,
            points_earned,
            description=f"连续签到第 {checkin_record.streak_days + 1} 天奖励"
        )

        session.commit()

        return {
            "success": True,
            "is_new": True,
            "points_earned": points_earned,
            "streak_days": checkin_record.streak_days,
            "total_checkins": checkin_record.total_checkins,
            "message": f"签到成功！获得 {points_earned} 积分，连续签到 {checkin_record.streak_days + 1} 天"
        }

    @staticmethod
    async def get_status(session: Session, user_id: int) -> dict:
        """
        获取签到状态

        Returns:
            {
                "has_checked_in_today": bool,
                "streak_days": int,
                "today_points": int,
                "total_checkins": int
            }
        """
        checkin_record = await CheckinService.get_or_create_checkin(session, user_id)
        today = date.today()

        has_checked_in_today = CheckinService._is_same_day(
            checkin_record.last_checkin_date, today
        )

        # 如果今天已签到，显示当前天数；否则显示明天将要获得的天数
        if has_checked_in_today:
            today_points = 0  # 今天已签到，不再获得积分
        else:
            # 计算今天签到能获得多少积分
            if CheckinService._is_consecutive(checkin_record.last_checkin_date, today):
                next_streak = (checkin_record.streak_days + 1) % 7
            else:
                next_streak = 0
            today_points = CHECKIN_REWARDS[next_streak]

        return {
            "has_checked_in_today": has_checked_in_today,
            "streak_days": checkin_record.streak_days,
            "today_points": today_points,
            "total_checkins": checkin_record.total_checkins
        }
