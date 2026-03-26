"""
Nyx AI Telegram Bot 入口模块
"""

from bot.handlers import (
    start_command,
    help_command,
    role_command,
    clear_command,
    status_command,
    profile_command,
    role_callback,
    button_callback,
    handle_message,
    image_command,
    tts_command,
)
from bot.config import TELEGRAM_BOT_TOKEN, TELEGRAM_PROXY_URL
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


# 启用日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_application() -> Application:
    """创建并配置 Bot 应用"""
    # 检查是否需要代理
    proxy_url = os.getenv('TELEGRAM_PROXY_URL')

    builder = Application.builder().token(
        TELEGRAM_BOT_TOKEN).connect_timeout(60).read_timeout(60)

    if proxy_url:
        # 使用代理
        from telegram.request import HTTPXRequest

        # 创建带代理的请求对象
        request = HTTPXRequest(proxy=proxy_url, connect_timeout=30.0)
        builder = builder.request(request)
        logger.info(f"使用代理: {proxy_url}")

    application = builder.build()

    # 注册命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("role", role_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(CommandHandler("tts", tts_command))

    # 注册回调处理器
    application.add_handler(CallbackQueryHandler(
        role_callback, pattern="^select_role:"))
    application.add_handler(CallbackQueryHandler(
        role_callback, pattern="^start_chat:"))
    application.add_handler(CallbackQueryHandler(
        role_callback, pattern="^back_to_roles$"))
    application.add_handler(CallbackQueryHandler(
        button_callback, pattern="^cmd:"))

    # 注册消息处理器（处理普通文本消息）
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message))

    return application


async def main():
    """主函数"""
    logger.info("启动 Nyx AI Telegram Bot...")

    application = create_application()

    # 启动 Bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    logger.info("Bot 已启动，按 Ctrl+C 停止")

    # 保持运行
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("正在停止 Bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot 已停止")


if __name__ == "__main__":
    asyncio.run(main())
