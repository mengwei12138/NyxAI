"""
应用配置
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache

# 根据 APP_ENV 环境变量决定加载哪个配置文件
# APP_ENV=production → .env.production
# APP_ENV 未设置或其他值 → .env（本地开发）
_APP_ENV = os.getenv("APP_ENV", "development")
_ENV_FILE = ".env.production" if _APP_ENV == "production" else ".env"


class Settings(BaseSettings):
    """应用配置类"""
    # Prometheus 指标端点鉴权 Token（留空则不鉴权，仅建议内网部署时留空）
    METRICS_TOKEN: str = ""

    # 管理后台路径（建议设为随机隐秘路径，防止被枚举扫描）
    # 例如：ADMIN_PATH=/manage-a3f9b2c7
    ADMIN_PATH: str = "/admin"

    # 应用配置
    APP_NAME: str = "Nyx AI API"
    DEBUG: bool = False

    # 数据库配置（支持 SQLite 和 PostgreSQL）
    # SQLite: sqlite:///./instance/nyx_ai.db
    # PostgreSQL: postgresql://user:password@localhost:5432/nyx_ai
    DATABASE_URL: str = "sqlite:///./instance/nyx_ai.db"

    # Redis 配置（用于限流、缓存、Token 黑名单）
    REDIS_URL: str = ""  # redis://localhost:6379/0

    # JWT配置（生产环境必须在 .env 中设置强随机 SECRET_KEY，不可使用默认值）
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-RANDOM-64-CHAR-STRING"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # CORS配置（生产环境通过 CORS_ORIGINS 环境变量传入，多个域名用逗号分隔）
    # 例如：CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
    CORS_ORIGINS_STR: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    @property
    def CORS_ORIGINS(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS_STR.split(",") if o.strip()]

    # API配置
    API_PREFIX: str = "/api"

    # 外部API配置
    FISH_AUDIO_API_KEY: str = ""
    ZIMAGE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    MODEL_NAME: str = "x-ai/grok-4-fast"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""

    # 系统角色声音 (Fish Audio s1 模型)
    SYSTEM_ROLE_VOICE_ID: str = "5c09bfed66ce4a968c3022d6f85c8e07"

    # Backblaze B2 对象存储配置（留空则回退到本地存储）
    # B2_KEY_ID:         Application Key ID（非 Master Key）
    # B2_APPLICATION_KEY:Application Key 密钥
    # B2_BUCKET_NAME:    存储桶名称
    # B2_ENDPOINT_URL:   S3 兼容端点，格式 https://s3.{region}.backblazeb2.com
    # B2_CDN_DOMAIN:     可选，CDN 自定义域名（留空则用默认 B2 URL）
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_ENDPOINT_URL: str = "https://s3.us-west-004.backblazeb2.com"
    B2_CDN_DOMAIN: str = ""

    # 爱发电支付配置（https://ifdian.net/developer）
    AFDIAN_USER_ID: str = ""     # 爱发电创作者 UID
    AFDIAN_API_TOKEN: str = ""   # 用于主动查询 API 的 Token

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略未定义的配置项


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
