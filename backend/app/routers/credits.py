"""
积分路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from app.database import get_session
from app.models import User, CreditType
from app.services import CreditService
from app.dependencies import get_current_user

router = APIRouter(prefix="/credits", tags=["积分"])


@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取当前用户积分余额"""
    balance = await CreditService.get_balance(session, current_user.id)
    return {
        "success": True,
        "data": balance
    }


@router.get("/costs")
async def get_costs():
    """获取积分消耗配置"""
    return {
        "success": True,
        "data": CreditService.get_costs()
    }


@router.get("/transactions")
async def get_transactions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取用户交易记录"""
    transactions = await CreditService.get_transactions(
        session, current_user.id, limit
    )
    return {
        "success": True,
        "data": transactions
    }


@router.post("/check/{action}")
async def check_credit(
    action: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    检查积分是否充足
    action: chat, tts, tti, create_role
    """
    type_map = {
        "chat": CreditType.CHAT,
        "tts": CreditType.TTS,
        "tti": CreditType.TTI,
        "create_role": CreditType.CREATE_ROLE,
    }

    if action not in type_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的操作类型: {action}"
        )

    sufficient, balance, required = await CreditService.check_sufficient(
        session, current_user.id, type_map[action]
    )

    return {
        "success": True,
        "data": {
            "sufficient": sufficient,
            "balance": balance,
            "required": required,
            "message": f"需要 {required} 积分，当前余额 {balance}" if not sufficient else "积分充足"
        }
    }


# 管理员接口：充值积分
@router.post("/recharge")
async def recharge(
    amount: int,
    user_id: int = None,
    description: str = "充值",
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """充值积分（仅管理员或自己）"""
    target_user_id = user_id or current_user.id

    # 检查权限
    if target_user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权为其他用户充值"
        )

    # 单次充值上限校验
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="充值金额必须大于 0")
    if amount > 100_000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="单次充值不得超过 100,000")

    success, message, balance = await CreditService.recharge(
        session, target_user_id, amount, description
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return {
        "success": True,
        "message": message,
        "data": {"balance": balance}
    }
