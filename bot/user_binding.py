"""
Telegram 用户与 Web 用户绑定模块
调用 Backend API 进行用户管理
"""
import logging
from typing import Dict, Tuple, Optional
from bot.api_client import api_client


logger = logging.getLogger(__name__)

# Telegram 用户ID到Web用户ID的映射: {telegram_user_id: user_id}
tg_user_mapping: Dict[int, int] = {}


def get_or_create_web_user(telegram_user) -> Tuple[Optional[int], bool]:
    """
    获取或创建Web用户账户（通过 Backend API）

    Args:
        telegram_user: Telegram User 对象

    Returns:
        (user_id, is_new): Web用户ID和是否新创建
    """
    telegram_id = telegram_user.id

    # 检查是否已有映射
    if telegram_id in tg_user_mapping:
        return tg_user_mapping[telegram_id], False

    try:
        # 调用新的 Bot 认证 API
        result = api_client.bot_auth(
            telegram_id=telegram_id,
            first_name=telegram_user.first_name,
            username=telegram_user.username
        )

        # TokenResponse 是扁平结构：{access_token, user_id, username, ...}
        if result and "user_id" in result:
            user_id = result["user_id"]
            tg_user_mapping[telegram_id] = user_id
            # 设置 telegram_id 到 API 客户端
            api_client.set_telegram_id(telegram_id)
            logger.info(
                f"为 Telegram 用户 {telegram_id} 创建/绑定 Web 账户: ID: {user_id}")
            return user_id, True
        else:
            logger.error(f"Bot 用户认证失败，响应格式: {result}")
            return None, False
    except Exception as e:
        logger.error(f"Bot 用户认证异常: {e}")
        return None, False


def get_cached_user_id(telegram_id: int) -> Optional[int]:
    """获取缓存的 Web 用户 ID"""
    return tg_user_mapping.get(telegram_id)
