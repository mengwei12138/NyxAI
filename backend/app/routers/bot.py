"""
Bot 专用路由 - 供 Telegram Bot 调用
这些接口使用 telegram_id 进行认证，不需要 JWT
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List, Optional
import hashlib
import time
import threading
import asyncio
from functools import partial

from app.database import get_session
from app.models import (
    User, UserCreate, UserLogin, TokenResponse,
    Role, ChatMessage, MessageRole, CreditType
)
from app.services import AuthService, RoleService, ChatService, CreditService
from app.services.ai_service import AIChatService
from app.services.tts_service import generate_speech
from app.services.image_service import ImageService
from app.utils.tts_utils import extract_speech_content
import base64
from app.config import get_settings
from app.dependencies.auth import create_access_token

router = APIRouter(prefix="/bot", tags=["Bot专用"])

# ========== telegram_id → User 内存缓存（TTL 10 分钟）==========
# {telegram_id: (user, expire_ts)}
_BOT_USER_CACHE: dict[int, tuple[User, float]] = {}
_BOT_USER_CACHE_TTL = 600  # 秒
_bot_user_cache_lock = threading.Lock()


def _get_cached_bot_user(telegram_id: int) -> User | None:
    """从缓存读取，过期则返回 None"""
    with _bot_user_cache_lock:
        entry = _BOT_USER_CACHE.get(telegram_id)
        if entry and time.time() < entry[1]:
            return entry[0]
        if entry:
            del _BOT_USER_CACHE[telegram_id]
    return None


def _set_cached_bot_user(telegram_id: int, user: User) -> None:
    """写入缓存，TTL 10 分钟"""
    with _bot_user_cache_lock:
        _BOT_USER_CACHE[telegram_id] = (
            user, time.time() + _BOT_USER_CACHE_TTL)


async def get_bot_user(telegram_id: int, session: Session) -> User:
    """根据 telegram_id 获取或创建用户（带内存缓存，减少 SELECT 查询）"""
    # 1. 命中缓存直接返回
    cached = _get_cached_bot_user(telegram_id)
    if cached:
        return cached

    # 2. 未命中，查询数据库
    bot_username = f"tg_{telegram_id}"
    statement = select(User).where(User.username == bot_username)
    user = session.exec(statement).first()

    if not user:
        # 自动创建用户
        password = hashlib.sha256(
            f"bot_{telegram_id}_secret".encode()).hexdigest()[:16]
        user = await AuthService.register(session, UserCreate(
            username=bot_username,
            password=password,
            confirm_password=password
        ))

    # 3. 写入缓存
    _set_cached_bot_user(telegram_id, user)
    return user


# ========== 用户相关 ==========

@router.post("/auth", response_model=TokenResponse)
async def bot_auth(
    telegram_id: int,
    first_name: str,
    username: str = None,
    session: Session = Depends(get_session)
):
    """Bot 认证：注册或登录"""
    try:
        bot_username = f"tg_{telegram_id}"
        password = hashlib.sha256(
            f"bot_{telegram_id}_secret".encode()).hexdigest()[:16]

        statement = select(User).where(User.username == bot_username)
        user = session.exec(statement).first()

        if user:
            # 登录
            return await AuthService.login(session, UserLogin(
                username=bot_username,
                password=password
            ))
        else:
            # 注册
            await AuthService.register(session, UserCreate(
                username=bot_username,
                password=password,
                confirm_password=password
            ))

            # 注册后直接登录获取完整 TokenResponse
            return await AuthService.login(session, UserLogin(
                username=bot_username,
                password=password
            ))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bot 认证失败: {str(e)}"
        )


@router.get("/me")
async def bot_get_me(
    telegram_id: int,
    session: Session = Depends(get_session)
):
    """获取 Bot 用户信息（包含 Web 登录密码）"""
    user = await get_bot_user(telegram_id, session)

    # 生成 Web 端登录密码（与认证时一致）
    web_password = hashlib.sha256(
        f"bot_{telegram_id}_secret".encode()).hexdigest()[:16]

    # 获取积分余额
    credit_balance = await CreditService.get_balance(session, user.id)

    return {
        "id": user.id,
        "username": user.username,
        "password": web_password,
        "created_at": user.created_at,
        "credits": credit_balance.balance,
    }


# ========== 角色相关 ==========

@router.get("/roles")
async def bot_get_roles(
    telegram_id: int,
    mode: str = "public",
    session: Session = Depends(get_session)
):
    """获取角色列表"""
    user = await get_bot_user(telegram_id, session)
    roles = await RoleService.get_roles(session, user.id, mode)
    return [{"id": r.id, "name": r.name, "greeting": r.greeting} for r in roles]


@router.get("/roles/{role_id}")
async def bot_get_role(
    telegram_id: int,
    role_id: int,
    session: Session = Depends(get_session)
):
    """获取角色详情"""
    user = await get_bot_user(telegram_id, session)
    role = await RoleService.get_role(session, role_id)

    if not role or not role.is_active:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查权限
    if role.visibility != "public" and role.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此角色")

    # 获取用户隔离状态（与 /bot/states 一致）
    states_dict = await ChatService.get_user_role_states(session, user.id, role_id)

    return {
        "id": role.id,
        "name": role.name,
        "persona": role.persona,
        "scenario": role.scenario,
        "user_persona": role.user_persona,
        "greeting": role.greeting,
        "appearance_tags": role.appearance_tags,
        "image_style": role.image_style,
        "clothing_state": role.clothing_state,
        "voice_reference_id": role.voice_reference_id,
        "states": states_dict
    }


# ========== 聊天相关 ==========

@router.post("/chat/{role_id}")
async def bot_chat(
    telegram_id: int,
    role_id: int,
    message: str,
    session: Session = Depends(get_session)
):
    """发送消息并获取 AI 回复"""
    user = await get_bot_user(telegram_id, session)

    # 检查角色
    role = await RoleService.get_role(session, role_id)
    if not role or not role.is_active:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查权限
    if role.visibility != "public" and role.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此角色")

    # 积分检查
    sufficient, balance, required = await CreditService.check_sufficient(
        session, user.id, CreditType.CHAT
    )
    if not sufficient:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
        )

    # 保存用户消息
    user_msg = await ChatService.create_message(
        session, role_id, user.id, MessageRole.USER, message
    )

    # 获取历史
    history = await ChatService.get_chat_history(session, role_id, user.id, limit=10)

    # 调用 AI
    result = await AIChatService.chat(
        role_id=role_id,
        user_id=user.id,
        message=message,
        history=history
    )

    # 保存 AI 回复
    ai_msg = await ChatService.create_message(
        session, role_id, user.id, MessageRole.ASSISTANT, result["content"]
    )

    # 扣除积分
    await CreditService.deduct(
        session, user.id, CreditType.CHAT,
        description=f"Bot 与角色 {role.name} 聊天",
        related_id=ai_msg.id
    )

    # 获取最新用户隔离状态（与 Web 端保持一致）
    states = await ChatService.get_user_role_states(session, user.id, role_id)

    return {
        "message_id": ai_msg.id,
        "content": result["content"],
        "states": states,
        "role_name": role.name
    }


@router.get("/chat/history/{role_id}")
async def bot_get_history(
    telegram_id: int,
    role_id: int,
    limit: int = Query(default=20, le=200, description="最多返回 200 条"),
    session: Session = Depends(get_session)
):
    """获取聊天历史"""
    user = await get_bot_user(telegram_id, session)

    history = await ChatService.get_chat_history(session, role_id, user.id, limit)
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }
        for msg in history
    ]


@router.delete("/chat/history/{role_id}")
async def bot_clear_history(
    telegram_id: int,
    role_id: int,
    session: Session = Depends(get_session)
):
    """清空聊天历史"""
    user = await get_bot_user(telegram_id, session)
    await ChatService.clear_history(session, role_id, user.id)
    return {"success": True}


# ========== TTS 相关 ==========

@router.post("/tts")
async def bot_tts(
    telegram_id: int,
    text: str,
    role_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """生成 TTS 语音（消耗 5 积分）"""
    user = await get_bot_user(telegram_id, session)

    # 积分检查
    sufficient, balance, required = await CreditService.check_sufficient(
        session, user.id, CreditType.TTS
    )
    if not sufficient:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
        )

    # 提取说话内容
    speech_text = extract_speech_content(text)
    if not speech_text:
        return {"success": False, "error": "没有检测到说话内容"}

    # 获取声音：优先级 用户聊天设置 > 角色默认 > 系统默认
    voice_reference_id = None
    if role_id:
        # 1. 先读用户聊天设置（Web 端保存的个性化配置）
        chat_settings = await ChatService.get_user_chat_settings(session, user.id, role_id)
        if chat_settings and chat_settings.voice_ref:
            voice_reference_id = chat_settings.voice_ref
        # 2. 角色默认声音
        if not voice_reference_id:
            role = await RoleService.get_role(session, role_id)
            if role and role.voice_reference_id:
                voice_reference_id = role.voice_reference_id

    # 3. 系统默认声音
    if not voice_reference_id:
        settings = get_settings()
        voice_reference_id = settings.SYSTEM_ROLE_VOICE_ID

    # 生成语音（在线程池执行，避免阻塞事件循环）
    loop = asyncio.get_event_loop()
    audio_path, oss_url = await loop.run_in_executor(
        None, partial(generate_speech, speech_text, voice_reference_id)
    )

    if not audio_path:
        return {"success": False, "error": "生成语音失败"}

    # 扣除积分
    await CreditService.deduct(
        session, user.id, CreditType.TTS,
        description=f"Bot TTS 语音生成"
    )

    # 优先返回 OSS URL
    if oss_url:
        return {"success": True, "audio_url": oss_url, "format": "mp3"}

    # 回退：base64
    with open(audio_path, 'rb') as f:
        audio_data = base64.b64encode(f.read()).decode('utf-8')

    return {
        "success": True,
        "audio": audio_data,
        "format": "mp3"
    }


# ========== 文生图相关 ==========

@router.post("/image/generate")
async def bot_generate_image(
    telegram_id: int,
    role_id: int,
    chat_history: str,
    session: Session = Depends(get_session)
):
    """生成图片（消耗 10 积分）"""
    user = await get_bot_user(telegram_id, session)

    # 积分检查
    sufficient, balance, required = await CreditService.check_sufficient(
        session, user.id, CreditType.TTI
    )
    if not sufficient:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
        )

    # 获取角色配置
    role = await RoleService.get_role(session, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 获取用户聊天设置（Web 端保存的个性化配置），优先级高于角色默认
    chat_settings = await ChatService.get_user_chat_settings(session, user.id, role_id)

    # 获取用户隔离的动态状态（含聊天中实时变化的 clothing_state）
    user_states = await ChatService.get_user_role_states(session, user.id, role_id)
    dynamic_clothing = user_states.get(
        'clothing_state', {}).get('value') or None

    role_config = {
        "appearance_tags": (chat_settings.appearance_tags if chat_settings and chat_settings.appearance_tags else None) or role.appearance_tags or "",
        # 优先级：动态衣物状态 > 角色默认衣物状态
        "clothing_state": dynamic_clothing or role.clothing_state or "整洁的衣服",
        "image_style": (chat_settings.image_style if chat_settings and chat_settings.image_style else None) or role.image_style or "anime",
        "default_scene": role.scenario or "",
    }

    # 先扣除积分，任务创建后不退款（生成结果异步，无法保证退款时机）
    await CreditService.deduct(
        session, user.id, CreditType.TTI,
        description=f"Bot 文生图 - 角色 {role.name}"
    )

    # 创建生成任务
    task_id = ImageService.create_generation_task(chat_history, role_config)

    return {"success": True, "task_id": task_id}


@router.get("/image/status/{task_id}")
async def bot_image_status(
    telegram_id: int,
    task_id: str,
    session: Session = Depends(get_session)
):
    """查询图片生成状态"""
    user = await get_bot_user(telegram_id, session)
    status = ImageService.get_task_status(task_id)
    return status


@router.post("/image/save")
async def bot_save_image(
    telegram_id: int,
    message_id: int,
    image_url: str,
    session: Session = Depends(get_session)
):
    """将生成的图片 URL 写入对应的聊天消息，使 Web 端可见"""
    user = await get_bot_user(telegram_id, session)
    message = session.get(ChatMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    # 安全校验：只能操作自己的消息
    if message.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作此消息")
    message.image_url = image_url
    session.add(message)
    session.commit()
    return {"success": True}


@router.get("/states/{role_id}")
async def bot_get_role_states(
    telegram_id: int,
    role_id: int,
    session: Session = Depends(get_session)
):
    """获取用户对特定角色的状态（用户隔离）"""
    user = await get_bot_user(telegram_id, session)

    # 检查角色是否存在
    role = await RoleService.get_role(session, role_id)
    if not role or not role.is_active:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查权限
    if role.visibility != "public" and role.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此角色")

    # 获取用户隔离的状态
    states = await ChatService.get_user_role_states(session, user.id, role_id)

    return {
        "success": True,
        "role_id": role_id,
        "role_name": role.name,
        "states": states
    }


@router.post("/reset-states/{role_id}")
async def bot_reset_role_states(
    telegram_id: int,
    role_id: int,
    session: Session = Depends(get_session)
):
    """重置用户对特定角色的状态为默认值"""
    user = await get_bot_user(telegram_id, session)

    # 检查角色是否存在
    role = await RoleService.get_role(session, role_id)
    if not role or not role.is_active:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 检查权限
    if role.visibility != "public" and role.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此角色")

    # 重置用户状态
    success = await ChatService.reset_user_role_states(session, user.id, role_id)

    if success:
        return {
            "success": True,
            "message": f"角色 '{role.name}' 的状态已重置为默认值"
        }
    else:
        raise HTTPException(status_code=500, detail="重置状态失败")
