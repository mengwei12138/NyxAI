"""
积分服务
"""
from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime
from app.models import (
    UserCredits, CreditTransaction, CreditType,
    CreditBalanceResponse, CreditTransactionResponse
)


class CreditService:
    """积分服务类"""

    # 积分消耗配置
    COSTS = {
        CreditType.CHAT: 1,
        CreditType.TTS: 5,
        CreditType.TTI: 10,
        CreditType.CREATE_ROLE: 50,
        CreditType.POLISH: 5,
    }

    @staticmethod
    async def get_or_create_user_credits(session: Session, user_id: int) -> UserCredits:
        """获取或创建用户积分记录"""
        statement = select(UserCredits).where(UserCredits.user_id == user_id)
        credits = session.exec(statement).first()

        if not credits:
            credits = UserCredits(
                user_id=user_id,
                balance=15,  # 新用户赠送15积分
                total_earned=15,
                total_spent=0
            )
            session.add(credits)
            session.commit()
            session.refresh(credits)

            # 记录赠送交易
            transaction = CreditTransaction(
                user_id=user_id,
                amount=15,
                type=CreditType.BONUS,
                description="新用户注册赠送",
                balance_after=15
            )
            session.add(transaction)
            session.commit()

        return credits

    @staticmethod
    async def get_balance(session: Session, user_id: int) -> CreditBalanceResponse:
        """获取用户积分余额"""
        credits = await CreditService.get_or_create_user_credits(session, user_id)
        return CreditBalanceResponse(
            balance=credits.balance,
            total_earned=credits.total_earned,
            total_spent=credits.total_spent
        )

    @staticmethod
    async def check_sufficient(
        session: Session,
        user_id: int,
        credit_type: CreditType
    ) -> tuple[bool, int, int]:
        """
        检查积分是否充足
        返回: (是否充足, 当前余额, 需要积分)
        """
        credits = await CreditService.get_or_create_user_credits(session, user_id)
        required = CreditService.COSTS.get(credit_type, 0)
        return credits.balance >= required, credits.balance, required

    @staticmethod
    async def deduct(
        session: Session,
        user_id: int,
        credit_type: CreditType,
        description: str = "",
        related_id: Optional[int] = None
    ) -> tuple[bool, str, int]:
        """
        扣除积分
        返回: (是否成功, 消息, 扣除后余额)
        """
        credits = await CreditService.get_or_create_user_credits(session, user_id)
        amount = CreditService.COSTS.get(credit_type, 0)

        if credits.balance < amount:
            return False, f"积分不足，需要 {amount} 积分，当前余额 {credits.balance}", credits.balance

        # 扣除积分
        credits.balance -= amount
        credits.total_spent += amount
        credits.updated_at = datetime.utcnow()
        session.add(credits)

        # 记录交易
        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            type=credit_type,
            description=description or f"{credit_type.value}消费",
            related_id=related_id,
            balance_after=credits.balance
        )
        session.add(transaction)
        session.commit()

        return True, "扣除成功", credits.balance

    @staticmethod
    async def recharge(
        session: Session,
        user_id: int,
        amount: int,
        description: str = "充值"
    ) -> tuple[bool, str, int]:
        """
        充值积分
        返回: (是否成功, 消息, 充值后余额)
        """
        if amount <= 0:
            return False, "充值金额必须大于0", 0

        credits = await CreditService.get_or_create_user_credits(session, user_id)

        # 增加积分
        credits.balance += amount
        credits.total_earned += amount
        credits.updated_at = datetime.utcnow()
        session.add(credits)

        # 记录交易
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            type=CreditType.RECHARGE,
            description=description,
            balance_after=credits.balance
        )
        session.add(transaction)
        session.commit()

        return True, "充值成功", credits.balance

    @staticmethod
    async def admin_deduct(
        session: Session,
        user_id: int,
        amount: int,
        description: str = "管理员扣减"
    ) -> tuple[bool, str, int]:
        """
        管理员扣减积分（不受余额限制，可扣至 0 但不低于 0）
        返回: (是否成功, 消息, 扣减后余额)
        """
        if amount <= 0:
            return False, "扣减金额必须大于0", 0

        credits = await CreditService.get_or_create_user_credits(session, user_id)
        actual_deduct = min(amount, credits.balance)  # 最多扣至 0

        credits.balance -= actual_deduct
        credits.total_spent += actual_deduct
        credits.updated_at = datetime.utcnow()
        session.add(credits)

        transaction = CreditTransaction(
            user_id=user_id,
            amount=-actual_deduct,
            type=CreditType.RECHARGE,
            description=description,
            balance_after=credits.balance
        )
        session.add(transaction)
        session.commit()

        return True, f"扣减成功，实际扣减 {actual_deduct} 积分", credits.balance

    @staticmethod
    async def get_transactions(
        session: Session,
        user_id: int,
        limit: int = 50
    ) -> List[CreditTransactionResponse]:
        """获取用户交易记录"""
        statement = (
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
        )
        transactions = session.exec(statement).all()

        return [
            CreditTransactionResponse(
                id=t.id,
                amount=t.amount,
                type=t.type,
                description=t.description,
                created_at=t.created_at
            )
            for t in transactions
        ]

    @staticmethod
    def get_costs() -> dict:
        """获取积分消耗配置"""
        return {
            "chat": CreditService.COSTS[CreditType.CHAT],
            "tts": CreditService.COSTS[CreditType.TTS],
            "tti": CreditService.COSTS[CreditType.TTI],
            "create_role": CreditService.COSTS[CreditType.CREATE_ROLE],
        }
