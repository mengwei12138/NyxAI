"""
Bot 专用配置模块
加载 bot/ 目录下的 .env 文件，不依赖外部层级
"""
import os


# 加载 bot 目录下的 .env 文件
try:
    from dotenv import load_dotenv
    # 获取 bot/ 目录路径
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(bot_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"[Config] 已加载环境变量: {env_path}")
    else:
        print(f"[Config] 警告: 未找到 .env 文件: {env_path}")
except ImportError:
    print("[Config] 警告: 未安装 python-dotenv，跳过 .env 加载")


def get_env_or_default(key, default=None, required=False):
    """从环境变量获取配置"""
    value = os.environ.get(key, default)
    if required and not value:
        raise ValueError(f"环境变量 {key} 必须设置")
    return value


# ============================================
# Bot 必需配置
# ============================================

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = get_env_or_default(
    "TELEGRAM_BOT_TOKEN",
    required=True
)

# Backend API 地址
BACKEND_URL = get_env_or_default(
    "BACKEND_URL",
    default="http://127.0.0.1:8000"
)

# Telegram 代理设置
TELEGRAM_PROXY_URL = get_env_or_default(
    "TELEGRAM_PROXY_URL",
    default=""
)
