"""
回调处理器模块
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.api_client import api_client
from bot.session import get_user_session
from bot.formatters import format_character_info, format_states_display, format_ai_response


logger = logging.getLogger(__name__)


async def role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """角色选择回调处理 - 显示角色详情和开始对话按钮"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    if callback_data.startswith("select_role:"):
        role_id = int(callback_data.split(":")[1])

        # 通过 API 获取角色详情
        role_data = api_client.get_role(role_id)
        if not role_data:
            await query.edit_message_text("⚠️ 获取角色信息失败。")
            return

        # 构建 profile 和 states
        profile = {
            'id': role_data.get('id'),
            'name': role_data.get('name'),
            'persona': role_data.get('persona'),
            'scenario': role_data.get('scenario'),
            'user_persona': role_data.get('user_persona'),
            'greeting': role_data.get('greeting'),
            'appearance_tags': role_data.get('appearance_tags'),
            'image_style': role_data.get('image_style', 'anime'),
            'clothing_state': role_data.get('clothing_state', '整洁的服装'),
        }

        # 获取角色状态
        states = role_data.get('states', {})

        # 存储角色信息到上下文，供后续使用
        context.user_data['pending_role_id'] = role_id
        context.user_data['pending_profile'] = profile
        context.user_data['pending_states'] = states

        # 显示角色详细信息
        info_text = format_character_info(profile, full=True)

        # 构建消息文本
        message_text = f"🎭 *角色详情*\n\n{info_text}"

        # 创建按钮：开始对话 + 返回列表
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton(
                    "💬 开始对话", callback_data=f"start_chat:{role_id}"),
                InlineKeyboardButton("🔙 返回列表", callback_data="back_to_roles")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 如果消息太长，简化显示
        if len(message_text) > 4000:
            message_text = f"🎭 *{profile['name']}*\n\n📖 {profile['persona'][:500]}..."

        await query.edit_message_text(
            message_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    elif callback_data.startswith("start_chat:"):
        # 开始对话
        role_id = int(callback_data.split(":")[1])
        profile = context.user_data.get('pending_profile')
        states = context.user_data.get('pending_states')

        if not profile:
            # 如果没有缓存，通过 API 重新获取
            role_data = api_client.get_role(role_id)
            if not role_data:
                await query.edit_message_text("⚠️ 获取角色信息失败。")
                return

            profile = {
                'id': role_data.get('id'),
                'name': role_data.get('name'),
                'persona': role_data.get('persona'),
                'scenario': role_data.get('scenario'),
                'user_persona': role_data.get('user_persona'),
                'greeting': role_data.get('greeting'),
                'appearance_tags': role_data.get('appearance_tags'),
                'image_style': role_data.get('image_style', 'anime'),
                'clothing_state': role_data.get('clothing_state', '整洁的服装'),
            }

            # 获取用户隔离的状态
            try:
                states = api_client.get_role_states(role_id)
                if not states:
                    states = role_data.get('states', {})
            except Exception as e:
                logger.error(f"获取用户隔离状态失败: {e}")
                states = role_data.get('states', {})

        # 初始化用户会话
        session = get_user_session(user_id)
        session.role_id = role_id
        session.initialize(profile, states)

        # 清除待选状态
        context.user_data.pop('pending_role_id', None)
        context.user_data.pop('pending_profile', None)
        context.user_data.pop('pending_states', None)

        # 拉取后端历史消息，填充本地 session（供 /image 等命令使用）
        history = api_client.get_chat_history(role_id, limit=10)
        if history:
            for msg in history:
                role_label = 'user' if msg.get(
                    'role') == 'user' else 'assistant'
                session.messages.append(
                    {'role': role_label, 'content': msg.get('content', '')})
            # 保存最新一条 AI 消息的 ID
            ai_msgs = [m for m in history if m.get('role') == 'assistant']
            if ai_msgs:
                session.last_message_id = ai_msgs[-1].get('id')

        # 发送问候语（格式化，区分动作/说话/内心）
        greeting = profile.get('greeting', f"你好，我是{profile['name']}。让我们开始对话吧！")
        formatted_greeting = format_ai_response(greeting)

        # 如果有历史记录，显示续聊提示 + 最新一条 AI 消息
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = [
            [
                InlineKeyboardButton("🔊 语音（5分）", callback_data="cmd:tts"),
                InlineKeyboardButton("🖼️ 生图（10分）", callback_data="cmd:image")
            ],
            [
                InlineKeyboardButton("📊 /status", callback_data="cmd:status"),
                InlineKeyboardButton("💎 查积分", callback_data="cmd:credits")
            ]
        ]
        greeting_markup = InlineKeyboardMarkup(kb)

        if history and session.messages:
            # 取最新一条 AI 消息作为续聊提示
            last_ai = next((m for m in reversed(history)
                           if m.get('role') == 'assistant'), None)
            if last_ai:
                last_content = last_ai.get('content', '')
                formatted_last = format_ai_response(last_content)
                await query.edit_message_text(
                    f"✅ *已选择角色: {profile['name']}*\n"
                    f"💬 *上次对话续聊中...*\n\n"
                    f"{formatted_last}",
                    parse_mode='Markdown',
                    reply_markup=greeting_markup
                )
                return

        # 无历史则发送开场白

        await query.edit_message_text(
            f"✅ *已选择角色: {profile['name']}*\n\n{formatted_greeting}",
            parse_mode='Markdown',
            reply_markup=greeting_markup
        )

    elif callback_data == "back_to_roles":
        # 返回角色列表
        from .commands import role_command
        await role_command(update, context)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """快捷命令按钮回调处理"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    if callback_data == "cmd:image":
        await query.message.reply_text("🎨 *正在生成图片...*", parse_mode='Markdown')
        # 导入 image 模块的函数
        from .image import run_image_command
        await run_image_command(query.message, context, user_id)

    elif callback_data == "cmd:status":
        session = get_user_session(user_id)

        if not session.is_initialized:
            await query.message.reply_text("⚠️ 你还没有选择角色,请使用 /role 选择角色。")
            return

        # 实时拉取用户隔离状态
        try:
            fresh_states = api_client.get_role_states(session.role_id)
            if fresh_states:
                session.states = fresh_states
        except Exception:
            pass

        states_text = format_states_display(session.states)
        character_name = session.profile['name']

        await query.message.reply_text(
            f"🎭 *当前角色*: {character_name}\n\n{states_text}",
            parse_mode='Markdown'
        )

    elif callback_data == "cmd:tts":
        # 调用 TTS 命令
        from .tts import tts_command
        await tts_command(update, context)

    elif callback_data == "cmd:credits":
        # 查询积分余额
        try:
            user_info = api_client.get_me()
            credits = user_info.get('credits', 0)
            await query.message.reply_text(
                f"💎 *你的积分余额*: `{credits}` 分\n\n"
                f"_消费标准：聊天 1分 / 语音 5分 / 生图 10分_",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"查询积分失败: {e}")
            await query.message.reply_text("⚠️ 查询积分失败，请稍后重试。")
