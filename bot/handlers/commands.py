"""
命令处理器模块
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from bot.api_client import api_client
from bot.session import get_user_session
from bot.user_binding import get_or_create_web_user
from bot.formatters import format_states_display, format_character_info


logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start 命令 - 欢迎信息、自动创建账户和显示菜单"""
    user = update.effective_user

    # 自动创建或绑定 Web 用户账户
    web_user_id, is_new = get_or_create_web_user(user)

    if web_user_id:
        account_status = "✅ 已为你自动创建账户" if is_new else "✅ 已连接到你的账户"
    else:
        account_status = "⚠️ 账户连接失败，但你可以继续使用"

    welcome_text = f"""
🌙 *欢迎来到 Nyx AI*

你好, {user.first_name}!

{account_status}

我是一个智能角色扮演 AI,可以扮演各种角色与你对话。

*可用命令:*
/role - 选择或切换角色
/clear - 重置当前对话
/status - 查看当前状态
/image - 根据对话生成图片
/profile - 用户中心
/help - 显示帮助信息

请先使用 /role 选择一个角色开始对话!
"""

    # 创建底部键盘菜单
    keyboard = [
        ['/role', '/status', '/image'],
        ['/profile', '/clear', '/help']
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help 命令 - 显示帮助"""
    help_text = """
🌙 *Nyx AI 帮助*

*基础命令:*
/start - 开始使用
/role - 选择或切换角色
/clear - 重置当前对话和状态
/status - 查看当前角色状态
/help - 显示此帮助

*使用说明:*
1. 使用 /role 选择你想对话的角色
2. 直接发送消息开始对话
3. AI 会根据对话内容自动更新状态
4. 使用 /status 随时查看当前状态
5. 使用 /clear 重新开始对话
6. 使用 /image 根据对话生成图片

*特点:*
- 沉浸式角色扮演体验
- 动态状态系统
- 上下文感知对话
- 支持文生图 /image
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def role_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/role 命令 - 显示角色选择菜单"""
    user = update.effective_user
    # 确保 telegram_id 已设置（防止未走 /start 直接使用 /role）
    if api_client.telegram_id is None:
        get_or_create_web_user(user)

    # 通过 API 获取角色列表
    agents = api_client.get_roles(mode="public")

    if not agents:
        await update.message.reply_text("⚠️ 暂无可用角色,请联系管理员。")
        return

    keyboard = []
    for agent in agents:
        keyboard.append([
            InlineKeyboardButton(
                f"🎭 {agent['name']}",
                callback_data=f"select_role:{agent['id']}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎭 *请选择要对话的角色:*",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/clear 命令 - 重置对话和状态"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    if not session.is_initialized:
        await update.message.reply_text("⚠️ 你还没有选择角色。")
        return

    character_name = session.profile['name']
    role_id = session.role_id

    # 重置用户状态（调用后端 API）
    try:
        api_client.reset_role_states(role_id)
        # 重新获取重置后的状态
        states = api_client.get_role_states(role_id)
        session.initialize(session.profile, states)

        await update.message.reply_text(
            f"✅ *对话和状态已重置*\n\n与 *{character_name}* 的对话历史已清空，\n"
            f"所有状态已恢复为默认值。",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"重置状态失败: {e}")
        # 仅重置本地会话
        session.initialize(session.profile, session.states)
        await update.message.reply_text(
            f"✅ *对话已重置*\n\n与 *{character_name}* 的对话历史已清空，"
            f"但状态重置可能未同步到服务器。",
            parse_mode='Markdown'
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status 命令 - 查看当前状态"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    if not session.is_initialized:
        await update.message.reply_text(
            "⚠️ *请先选择角色*\n\n使用 /role 命令选择你想对话的角色。",
            parse_mode='Markdown'
        )
        return

    character_name = session.profile['name']
    role_id = session.role_id

    # 实时从后端拉取用户隔离状态（与 Web 端保持一致）
    try:
        fresh_states = api_client.get_role_states(role_id)
        if fresh_states:
            session.states = fresh_states
    except Exception as e:
        logger.warning(f"实时拉取状态失败，使用缓存: {e}")

    states_text = format_states_display(session.states)

    await update.message.reply_text(
        f"🎭 *当前角色*: {character_name}\n\n{states_text}",
        parse_mode='Markdown'
    )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/profile 命令 - 用户中心"""
    user = update.effective_user
    web_user_id, _ = get_or_create_web_user(user)

    if not web_user_id:
        await update.message.reply_text("⚠️ 无法获取用户信息。")
        return

    # 从 API 获取用户信息
    try:
        user_info = api_client.get_me()
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        await update.message.reply_text("⚠️ 获取用户信息失败。")
        return

    username = user_info.get('username', '未知')
    password = user_info.get('password', '未知')
    credits = user_info.get('credits', 0)

    profile_text = f"""👤 *用户中心*

🆔 Telegram ID: `{user.id}`
👤 用户名: @{user.username or '未设置'}
📛 显示名: {user.first_name} {user.last_name or ''}

💎 *当前积分*: `{credits}` 分
_（聊天 1分 / 语音 5分 / 生图 10分）_

🔗 *Web 端登录信息*：
```
用户名: {username}
密码: {password}
```

[点击登录 Web 端](http://localhost:5173/)

💡 点击代码块即可复制，或长按选择复制。
⚠️ 请妥善保管密码，不要分享给他人！"""

    await update.message.reply_text(profile_text, parse_mode='Markdown')
