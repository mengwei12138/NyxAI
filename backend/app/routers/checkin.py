"""
签到路由
"""
from fastapi import APIRouter, Depends, status
from sqlmodel import Session
from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.services.checkin_service import CheckinService

router = APIRouter(prefix="/checkin", tags=["签到"])


@router.post("/")
async def do_checkin(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """执行签到"""
    result = await CheckinService.checkin(session, current_user.id)
    return {
        "success": result["success"],
        "data": {
            "is_new": result["is_new"],
            "points_earned": result["points_earned"],
            "streak_days": result["streak_days"],
            "total_checkins": result["total_checkins"],
        },
        "message": result["message"]
    }


@router.get("/status")
async def get_checkin_status(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取签到状态"""
    status_data = await CheckinService.get_status(session, current_user.id)
    return {
        "success": True,
        "data": status_data
    }
