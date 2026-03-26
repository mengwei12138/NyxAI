"""
支付路由（爱发电版）
- GET  /packages              获取套餐列表（含爱发电 plan_id，前端生成跳转链接）
- POST /prepare-order         预创建订单，返回 custom_order_id + 爱发电跳转 URL
- POST /webhook               爱发电 Webhook 回调（无鉴权，RSA 验签）
- GET  /order/{id}/status     轮询订单支付状态
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.models.payment import OrderStatusResponse
from app.services.payment_service import PaymentService
from app.core.logger import get_logger

router = APIRouter(prefix="/payment", tags=["支付"])
logger = get_logger("payment.router")


@router.get("/packages")
async def get_packages(session: Session = Depends(get_session)):
    """获取充值套餐列表"""
    return {"success": True, "data": PaymentService.get_packages(session)}


@router.post("/prepare-order")
async def prepare_order(
    body: dict,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    预创建订单，返回：
    - pay_url: 爱发电付款链接（前端直接跳转）
    - custom_order_id: 用于后续轮询状态
    """
    package_id = body.get("package_id", "")
    if not package_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 package_id")

    try:
        pay_url, custom_order_id = PaymentService.build_pay_url(
            user_id=current_user.id,
            package_id=package_id,
            session=session,
        )
        return {
            "success": True,
            "pay_url": pay_url,
            "custom_order_id": custom_order_id,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/webhook")
async def afdian_webhook(
    request: Request,
    session: Session = Depends(get_session),
):
    """
    爱发电 Webhook 接收。
    无论业务结果如何，必须返回 {"ec": 200, "em": ""}，否则爱发电视为失败并重试。
    """
    try:
        payload = await request.json()
        logger.info(f"收到爱发电 Webhook raw: {payload}")
    except Exception as e:
        logger.error(f"解析 Webhook 请求体失败: {e}")
        return JSONResponse({"ec": 200, "em": ""})

    result = await PaymentService.handle_webhook(session, payload)
    return JSONResponse(result)


@router.get("/order/{custom_order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(
    custom_order_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """轮询订单支付状态"""
    return await PaymentService.get_order_status(
        session, custom_order_id, current_user.id
    )
