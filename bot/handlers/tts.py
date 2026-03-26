"""
TTS 语音处理模块
处理 AI 回复的语音生成功能
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.session import get_user_session
from bot.api_client import api_client

logger = logging.getLogger(__name__)


async def tts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /tts 命令 - 将最近一条 AI 回复转换为语音
    支持从命令直接调用或从回调按钮调用
    """
    user_id = update.effective_user.id
    session = get_user_session(user_id)

    # 判断是命令调用还是回调调用
    if update.callback_query:
        # 从回调按钮调用
        message = update.callback_query.message
        reply_func = message.reply_text
        reply_voice_func = message.reply_voice
    else:
        # 从命令调用
        message = update.message
        reply_func = message.reply_text
        reply_voice_func = message.reply_voice

    if not session or not session.messages:
        await reply_func(
            "❌ 还没有对话记录。\n请先使用 /start 选择角色并开始对话。"
        )
        return

    # 找到最近一条 AI 回复
    ai_messages = [m for m in session.messages if m['role'] == 'assistant']
    if not ai_messages:
        await reply_func(
            "❌ 还没有 AI 回复。\n请先发送消息开始对话。"
        )
        return

    last_ai_message = ai_messages[-1]
    ai_response = last_ai_message['content']

    # 获取角色声音设置
    voice_reference_id = None
    if session.profile:
        voice_reference_id = session.profile.get('voice_reference_id')
        if voice_reference_id:
            logger.info(f"使用角色声音: {voice_reference_id}")

    # 显示生成中状态
    processing_msg = await reply_func(
        "🔊 正在生成语音...",
        parse_mode='Markdown'
    )

    try:
        # 通过 Backend API 生成语音
        role_id = session.profile.get('id') if session.profile else None
        result = api_client.generate_tts(ai_response, role_id=role_id)

        if not result.get("success"):
            error_msg = result.get("error", "生成语音失败")
            await processing_msg.edit_text(f"❌ {error_msg}")
            return

        # 发送语音
        audio_data = result.get("audio_data")
        if audio_data:
            await processing_msg.delete()
            await reply_voice_func(
                voice=audio_data,
                caption="🔊 AI 的语音回复"
            )
        else:
            await processing_msg.edit_text("❌ 生成语音失败")

    except Exception as e:
        logger.error(f"TTS 错误: {e}")
        await processing_msg.edit_text(f"❌ 生成语音失败: {str(e)}")


async def tts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    内联按钮回调 - 生成指定消息的语音
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_user_session(user_id)

    if not session:
        await query.edit_message_text("❌ 会话已过期，请重新使用 /start")
        return

    # 从回调数据获取消息索引
    callback_data = query.data
    if not callback_data.startswith("tts:"):
        return

    try:
        msg_index = int(callback_data.split(":")[1])
        ai_response = session.messages[msg_index]['content']
    except (IndexError, ValueError):
        await query.edit_message_text("❌ 消息不存在或已过期")
        return

    # 显示生成中
    await query.edit_message_text("🔊 正在生成语音...")

    try:
        # 生成语音
        audio_path = generate_speech_from_ai_response(ai_response)

        if not audio_path:
            await query.edit_message_text(
                "❌ 生成语音失败。\nAI 回复中没有检测到说话内容。"
            )
            return

        # 发送语音（作为新消息）
        with open(audio_path, 'rb') as audio_file:
            await context.bot.send_voice(
                chat_id=update.effective_chat.id,
                voice=audio_file,
                caption="🔊 AI 的语音回复",
                parse_mode='Markdown'
            )

        # 恢复原来的消息（可选）
        await query.edit_message_text("✅ 语音已发送")

    except Exception as e:
        logger.error(f"TTS 回调错误: {e}")
        await query.edit_message_text(f"❌ 生成语音失败: {str(e)}")
