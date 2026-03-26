"""
文生图处理器模块
"""
import asyncio
import logging
import io
import requests as sync_requests
from telegram import Update
from telegram.ext import ContextTypes
from bot.api_client import api_client
from bot.session import get_user_session
from bot.config import BACKEND_URL


logger = logging.getLogger(__name__)


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/image 命令 - 根据对话生成图片"""
    user_id = update.effective_user.id
    await run_image_command(update.message, context, user_id)


async def run_image_command(message, context, user_id):
    """执行 image 命令的核心逻辑"""
    session = get_user_session(user_id)

    if not session.is_initialized:
        await message.reply_text(
            "⚠️ *请先选择角色*\n\n使用 /role 命令选择你想对话的角色。",
            parse_mode='Markdown'
        )
        return

    # 检查是否有对话历史
    if len(session.messages) < 2:
        await message.reply_text(
            "⚠️ *对话历史不足*\n\n请先与角色进行一些对话,然后再生成图片。",
            parse_mode='Markdown'
        )
        return

    # 更新活动时间
    session.update_activity()

    # 显示"正在上传照片"状态
    await context.bot.send_chat_action(
        chat_id=message.chat.id,
        action='upload_photo'
    )

    try:
        # 获取角色信息
        role_id = session.profile.get('id')
        if not role_id:
            await message.reply_text("⚠️ 角色信息丢失，请重新选择角色。")
            return

        # 构建聊天记录（最近一轮对话）
        chat_history = []
        for msg in session.messages[-4:]:  # 最近4条消息
            if msg['role'] != 'system':
                role_label = "user" if msg['role'] == 'user' else "assistant"
                chat_history.append(f"{role_label}: {msg['content'][:300]}")
        chat_history_text = "\n".join(chat_history)

        # 显示生成中状态
        status_msg = await message.reply_text(
            "🎨 *正在分析场景并生成图片...*",
            parse_mode='Markdown'
        )

        # 调用 Backend API 生成图片
        task_id = api_client.generate_image(role_id, chat_history_text)

        if not task_id:
            await status_msg.edit_text("❌ 创建图片生成任务失败")
            return

        # 轮询检查状态
        max_attempts = 30
        for attempt in range(max_attempts):
            await asyncio.sleep(2)

            status_result = api_client.get_image_status(task_id)
            if not status_result:
                continue

            status = status_result.get('status')

            if status in ('SUCCESS', 'COMPLETED'):
                image_url = status_result.get('image_url')
                if image_url:
                    # 若是相对路径，拼接完整后端地址
                    if image_url.startswith('/'):
                        full_url = f"{BACKEND_URL}{image_url}"
                    else:
                        full_url = image_url
                    try:
                        resp = sync_requests.get(full_url, timeout=30)
                        resp.raise_for_status()
                        image_bytes = io.BytesIO(resp.content)
                        image_bytes.name = 'image.jpg'
                        await status_msg.delete()
                        await message.reply_photo(
                            photo=image_bytes,
                            caption="🎨 *图片生成完成！*",
                            parse_mode='Markdown'
                        )
                        # 将图片 URL 写入最近一条 AI 消息，使 Web 端可见
                        if session.last_message_id:
                            api_client.save_image(
                                session.last_message_id, image_url)
                    except Exception as dl_err:
                        logger.error(f"下载图片失败: {dl_err}")
                        await status_msg.edit_text(f"❌ 下载图片失败: {dl_err}")
                else:
                    await status_msg.edit_text("❌ 获取图片 URL 失败")
                return

            elif status == 'FAILED':
                error = status_result.get('error', '未知错误')
                await status_msg.edit_text(f"❌ 图片生成失败: {error}")
                return

            # 更新进度
            if attempt % 5 == 0:
                await status_msg.edit_text(
                    f"⏳ *图片生成中* ({attempt * 2}秒/预计 30-60 秒)...",
                    parse_mode='Markdown'
                )

        # 超时
        await status_msg.edit_text("⏰ *图片生成超时*\n\n请稍后重试。")

    except Exception as e:
        logger.error(f"生成图片时出错: {e}", exc_info=True)
        await message.reply_text(
            f"❌ *图片生成失败*\n\n错误: {str(e)}",
            parse_mode='Markdown'
        )
