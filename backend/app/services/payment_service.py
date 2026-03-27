"""
爱发电支付服务
- Webhook 被动发货：RSA(SHA256) 验签
- API 主动查询：MD5 签名
"""
import base64
import hashlib
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

import requests as http_requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from sqlmodel import Session, select, update
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.core.logger import get_logger
from app.models.payment import (
    PackageInfo, PaymentPackage, PaymentOrder, PaymentStatus, OrderStatusResponse
)
from app.services.credit_service import CreditService

logger = get_logger("payment")
settings = get_settings()

AFDIAN_QUERY_ORDER_URL = "https://ifdian.net/api/open/query-order"

# ---- 爱发电公钥（固定，从官方文档取得）----
AFDIAN_PUBLIC_KEY_PEM = """\
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwwdaCg1Bt+UKZKs0R54y
lYnuANma49IpgoOwNmk3a0rhg/PQuhUJ0EOZSowIC44l0K3+fqGns3Ygi4AfmEfS
4EKbdk1ahSxu7Zkp2rHMt+R9GarQFQkwSS/5x1dYiHNVMiR8oIXDgjmvxuNes2Cr
8fw9dEF0xNBKdkKgG2qAawcN1nZrdyaKWtPVT9m2Hl0ddOO9thZmVLFOb9NVzgYf
jEgI+KWX6aY19Ka/ghv/L4t1IXmz9pctablN5S0CRWpJW3Cn0k6zSXgjVdKm4uN7
jRlgSRaf/Ind46vMCm3N2sgwxu/g3bnooW+db0iLo13zzuvyn727Q3UDQ0MmZcEW
MQIDAQAB
-----END PUBLIC KEY-----"""

# ---- 套餐配置（从数据库读取，后台可热更新）----


def get_packages_from_db(session: Session) -> list[PaymentPackage]:
    """从数据库读取启用中的套餐，按 sort_order 排序"""
    return list(session.exec(
        select(PaymentPackage)
        .where(PaymentPackage.is_active == True)
        .order_by(PaymentPackage.sort_order)
    ).all())


def get_package_by_id(package_id: str, session: Session) -> Optional[PaymentPackage]:
    """按 package_id 查询单个套餐"""
    return session.exec(
        select(PaymentPackage).where(PaymentPackage.package_id == package_id)
    ).first()


def _make_custom_order_id(user_id: int) -> str:
    """生成 custom_order_id，格式：nyx_{user_id}_{随机串}"""
    return f"nyx_{user_id}_{uuid.uuid4().hex[:10]}"


# ---------- RSA 验签（Webhook 用）----------

def _verify_rsa_sign(sign_str: str, sign_b64: str) -> bool:
    """
    使用爱发电官方公钥对 Webhook 签名进行 RSA SHA256 验证。
    sign_str = out_trade_no + user_id + plan_id + total_amount（直接拼接）
    sign_b64 = Webhook data 中的 sign 字段（base64 编码）
    """
    try:
        public_key = serialization.load_pem_public_key(
            AFDIAN_PUBLIC_KEY_PEM.encode("utf-8")
        )
        public_key.verify(
            base64.b64decode(sign_b64),
            sign_str.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception as e:
        logger.warning(f"RSA 验签失败: {e}")
        return False


# ---------- MD5 签名（主动查询 API 用）----------

def _md5_sign(token: str, params_str: str, ts: int, user_id: str) -> str:
    """
    sign = md5(token + params{params} + ts{ts} + user_id{user_id})
    """
    raw = f"{token}params{params_str}ts{ts}user_id{user_id}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ---------- 业务服务 ----------

class PaymentService:

    @staticmethod
    def get_packages(session: Session) -> list[PackageInfo]:
        pkgs = get_packages_from_db(session)
        return [PackageInfo(
            id=p.package_id,
            plan_id=p.plan_id,
            name=p.name,
            amount=p.amount,
            credits=p.credits,
            desc=p.desc,
            popular=p.popular,
        ) for p in pkgs]

    @staticmethod
    def build_pay_url(user_id: int, package_id: str, session: Session) -> tuple:
        """
        构造爱发电付款链接，并在数据库预创建订单记录（PENDING）。
        若该用户对同一套餐存在 30 分钟内的 PENDING 订单，复用已有订单，避免垃圾数据。
        """
        pkg = get_package_by_id(package_id, session)
        if not pkg or not pkg.is_active:
            raise ValueError(f"套餐不存在: {package_id}")

        afd_uid = settings.AFDIAN_USER_ID
        if not afd_uid:
            raise RuntimeError("AFDIAN_USER_ID 未配置")

        plan_id = pkg.plan_id
        if not plan_id:
            raise RuntimeError(
                f"套餐 {package_id} 的爱发电方案 ID 未配置，请在管理后台充值方案页配置 plan_id")

        # 复用 30 分钟内的未支付订单
        reuse_threshold = datetime.utcnow() - timedelta(minutes=30)
        existing_pending = session.exec(
            select(PaymentOrder).where(
                PaymentOrder.user_id == user_id,
                PaymentOrder.package_id == package_id,
                PaymentOrder.status == PaymentStatus.PENDING,
                PaymentOrder.created_at >= reuse_threshold,
            ).order_by(PaymentOrder.created_at.desc())
        ).first()

        if existing_pending:
            custom_order_id = existing_pending.custom_order_id
            logger.info(f"复用已有 PENDING 订单: {custom_order_id}")
        else:
            custom_order_id = _make_custom_order_id(user_id)
            order = PaymentOrder(
                custom_order_id=custom_order_id,
                user_id=user_id,
                plan_id=plan_id,
                package_id=pkg.package_id,
                package_name=pkg.name,
                amount=pkg.amount,
                credits=pkg.credits,
                status=PaymentStatus.PENDING,
            )
            session.add(order)
            session.commit()
            session.refresh(order)

        pay_url = (
            f"https://ifdian.net/order/create"
            f"?user_id={afd_uid}"
            f"&plan_id={plan_id}"
            f"&remark={custom_order_id}"
        )
        return pay_url, custom_order_id

    @staticmethod
    async def handle_webhook(session: Session, payload: dict) -> dict:
        """
        处理爱发电 Webhook 推送。
        - 严格 RSA SHA256 验签（无 sign 或验签失败直接拒绝）
        - 仅处理 status=2（交易成功）
        - 幂等（out_trade_no 已处理则跳过）
        - 通过 remark 字段关联内部预创建订单（我们传入的 custom_order_id 回调时在 remark 中）
        - 充积分
        无论业务结果如何，最终必须返回 {"ec": 200, "em": ""}
        """
        try:
            data = payload.get("data", {})
            order_data = data.get("order", {})

            out_trade_no = order_data.get("out_trade_no", "")
            afd_user_id = order_data.get("user_id", "")
            plan_id = order_data.get("plan_id", "")
            total_amount = order_data.get("total_amount", "")
            status = order_data.get("status")

            # ⚠️ 关键：我们传给爱发电的 custom_order_id 回调时在 remark 字段中返回
            # order_data["custom_order_id"] 是爱发电系统自己生成的，不是我们的内部标识
            remark = order_data.get("remark", "")

            logger.info(
                f"收到爱发电 Webhook: out_trade_no={out_trade_no}, "
                f"remark={remark}, status={status}"
            )

            # 1. 严格验签（RSA SHA256）
            #    sign 在 Webhook data 层级（与 type/order 平级）
            sign = data.get("sign", "") or payload.get("sign", "")
            if not sign:
                logger.warning(
                    f"收到无 sign 的 Webhook 请求，out_trade_no={out_trade_no}，"
                    f"拒绝处理（可能是伪造请求）"
                )
                return {"ec": 200, "em": ""}

            sign_str = f"{out_trade_no}{afd_user_id}{plan_id}{total_amount}"
            if not _verify_rsa_sign(sign_str, sign):
                logger.warning(
                    f"Webhook RSA 验签失败，out_trade_no={out_trade_no}，"
                    f"拒绝处理（签名不匹配）"
                )
                return {"ec": 200, "em": ""}

            # 2. 仅处理 status=2（交易成功）
            if status != 2:
                logger.info(f"订单 {out_trade_no} 状态非成功: {status}，跳过")
                return {"ec": 200, "em": ""}

            # 3. 幂等：通过 out_trade_no 检查是否已处理
            existing = session.exec(
                select(PaymentOrder).where(
                    PaymentOrder.out_trade_no == out_trade_no
                )
            ).first()
            if existing and existing.status == PaymentStatus.PAID:
                logger.info(f"out_trade_no {out_trade_no} 已处理，幂等跳过")
                return {"ec": 200, "em": ""}

            # 4. 通过 remark 找到预创建订单（remark = 我们生成的 custom_order_id）
            if not remark:
                logger.warning(
                    f"Webhook 缺少 remark 字段，out_trade_no={out_trade_no}，跳过")
                return {"ec": 200, "em": ""}

            # 5. 原子更新：用 UPDATE WHERE status='pending' 防止并发重复充值
            #    只有一个并发请求能成功将 status 从 pending 改为 paid
            result = session.exec(
                update(PaymentOrder)
                .where(
                    PaymentOrder.custom_order_id == remark,
                    PaymentOrder.status == PaymentStatus.PENDING,  # 原子条件
                )
                .values(
                    status=PaymentStatus.PAID,
                    out_trade_no=out_trade_no,
                    plan_id=plan_id,
                    paid_at=datetime.utcnow(),
                )
            )
            session.commit()

            if result.rowcount == 0:
                # rowcount=0 说明该订单已被其他并发请求处理或不存在
                logger.info(f"remark={remark} 原子更新无影响行（已处理或不存在），幂等跳过")
                return {"ec": 200, "em": ""}

            # 6. 更新成功，查出订单信息用于充积分
            order = session.exec(
                select(PaymentOrder).where(
                    PaymentOrder.custom_order_id == remark
                )
            ).first()

            if not order:
                logger.error(f"原子更新成功但查不到订单 remark={remark}，异常情况")
                return {"ec": 200, "em": ""}

            # 7. 充积分
            await CreditService.recharge(
                session,
                order.user_id,
                order.credits,
                description=f"爱发电充值：{order.package_name}（{order.amount}元）",
            )

            logger.info(
                f"订单 {remark} 支付成功，"
                f"用户 {order.user_id} 充值 {order.credits} 积分"
            )

        except Exception as e:
            logger.error(f"处理爱发电 Webhook 异常: {e}", exc_info=True)

        return {"ec": 200, "em": ""}

    @staticmethod
    async def get_order_status(
        session: Session, custom_order_id: str, user_id: int
    ) -> OrderStatusResponse:
        order = session.exec(
            select(PaymentOrder).where(
                PaymentOrder.custom_order_id == custom_order_id,
                PaymentOrder.user_id == user_id,
            )
        ).first()

        if not order:
            return OrderStatusResponse(
                custom_order_id=custom_order_id,
                status=PaymentStatus.FAILED,
                message="订单不存在",
            )

        msg_map = {
            PaymentStatus.PENDING: "等待支付",
            PaymentStatus.PAID: "支付成功",
            PaymentStatus.FAILED: "支付失败",
        }
        return OrderStatusResponse(
            custom_order_id=custom_order_id,
            status=order.status,
            credits=order.credits if order.status == PaymentStatus.PAID else None,
            message=msg_map.get(order.status, ""),
        )

    @staticmethod
    async def query_orders_from_afdian(page: int = 1) -> dict:
        """
        主动查询爱发电订单（兜底补单用），使用 MD5 签名。
        返回爱发电原始响应。
        """
        token = settings.AFDIAN_API_TOKEN
        user_id = settings.AFDIAN_USER_ID
        if not token or not user_id:
            raise RuntimeError("AFDIAN_USER_ID / AFDIAN_API_TOKEN 未配置")

        params = json.dumps({"page": page}, separators=(",", ":"))
        ts = int(time.time())
        sign = _md5_sign(token, params, ts, user_id)

        body = {
            "user_id": user_id,
            "params": params,
            "ts": ts,
            "sign": sign,
        }

        resp = http_requests.post(
            AFDIAN_QUERY_ORDER_URL,
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"爱发电主动查询响应: ec={result.get('ec')}, page={page}")
        return result
