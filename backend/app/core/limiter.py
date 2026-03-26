"""
API限流配置
使用 slowapi + Redis 存储限流计数器
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger("limiter")
settings = get_settings()

# 创建限流器（使用内存存储，Redis 存储在 slowapi 0.1.9 中需要额外配置）
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # 默认全局限流
)

if settings.REDIS_URL:
    logger.info("Redis 已配置，但 slowapi 0.1.9 使用内存存储限流计数器")

# 分级限流配置
LIMITS = {
    "auth": ["5/minute"],           # 登录/注册
    "chat": ["30/minute"],          # 聊天发送
    "image": ["10/minute"],         # 文生图
    "tts": ["10/minute"],           # 语音合成
    "default": ["100/minute"],      # 其他接口
}
