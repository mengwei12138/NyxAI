"""
消息处理器模块
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.api_client import api_client
from bot.session import get_user_session
from bot.formatters import format_ai_response


logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户消息"""
    user_id = update.effective_user.id
    user_message = update.message.text

    session = get_user_session(user_id)

    # 检查是否已选择角色
    if not session.is_initialized:
        await update.message.reply_text(
            "⚠️ *请先选择角色*\n\n使用 /role 命令选择你想对话的角色。",
            parse_mode='Markdown'
        )
        return

    # 更新活动时间
    session.update_activity()

    # 显示"正在输入"状态
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action='typing'
    )

    try:
        # 通过 Backend API 发送消息并获取回复
        role_id = session.profile.get('id')
        if not role_id:
            await update.message.reply_text("⚠️ 角色信息丢失，请重新选择角色。")
            return

        # 调用 Backend API 发送消息
        response_data = api_client.send_message(
            role_id=role_id,
            message=user_message
        )

        if not response_data:
            await update.message.reply_text("⚠️ 获取 AI 回复失败，请稍后重试。")
            return

        # 获取 AI 回复
        ai_response = response_data.get('content', '抱歉，我现在无法回复。')

        # 更新本地状态（从 API 返回的状态）
        if 'states' in response_data:
            session.states = response_data['states']

        # 保存最新 AI 消息的数据库 ID（供 /image 命令关联图片）
        if 'message_id' in response_data:
            session.last_message_id = response_data['message_id']

        # 调试日志
        logger.info(f"AI 回复: {ai_response[:200]}...")

        # 格式化 AI 回复（区分动作、对话、内心想法）
        formatted_response = format_ai_response(ai_response)

        # 保存到本地 session
        session.messages.append({'role': 'user', 'content': user_message})
        session.messages.append({'role': 'assistant', 'content': ai_response})

        # 构建快捷命令按鈕
        keyboard = [
            [
                InlineKeyboardButton("🔊 语音（5分）", callback_data="cmd:tts"),
                InlineKeyboardButton("🖼️ 生图（10分）", callback_data="cmd:image")
            ],
            [
                InlineKeyboardButton("📊 /status", callback_data="cmd:status"),
                InlineKeyboardButton("💎 查积分", callback_data="cmd:credits")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 发送回复，附带快捷按钮
        await update.message.reply_text(
            formatted_response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        # 如果状态更新了,可选地发送状态提示(每3次更新显示一次,避免打扰)
        if 'states' in response_data and len(session.messages) % 6 == 0:
            await update.message.reply_text(
                "✨ _角色状态已根据对话发生变化_",
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"处理消息时出错: {e}", exc_info=True)
        await update.message.reply_text(
            "😅 *处理消息时出错*\n\n请稍后重试。",
            parse_mode='Markdown'
        )
