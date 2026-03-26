"""
聊天路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session
from typing import List, AsyncGenerator, Dict, Optional
import asyncio
import json
import uuid
import threading
from functools import partial
from app.database import get_session
from app.models import (
    ChatMessage, ChatMessageCreate, ChatRequest, ChatResponse,
    ChatMessageResponse, TTSRequest, TTSResponse, MessageRole, User
)
from app.services import ChatService, RoleService, CreditService, LLMService, LLMError
from app.services.tts_service import generate_speech, generate_voice_preview, get_voice_presets as _get_voice_presets
from app.services.ai_service import AIChatService
from app.services.image_service import ImageService
from app.utils.tts_utils import extract_speech_content
from app.dependencies import get_current_user
from app.models import CreditType
from app.core.limiter import limiter
from app.core.cache import cache

router = APIRouter(prefix="/chat", tags=["聊天"])

_CACHE_HISTORY_TTL = 30   # 历史缓存 30 秒（发消息后主动失效）
_TTS_TASK_TTL = 1800      # TTS 任务缓存 30 分钟
_TTS_KEY_PREFIX = "tts:task:"

# TTS 任务写锁（防止并发写缓存冲突，读可直接用 cache.get）
_tts_tasks_lock = threading.Lock()


def _history_cache_key(role_id: int, user_id: int, limit: int, before_id: int) -> str:
    return f"chat:history:{role_id}:{user_id}:{limit}:{before_id}"


def _invalidate_history_cache(role_id: int, user_id: int) -> None:
    """发消息后清空该用户该角色的所有历史缓存"""
    cache.delete_pattern(f"chat:history:{role_id}:{user_id}:")


@router.get("/history/{role_id}", response_model=List[ChatMessageResponse])
async def get_chat_history(
    role_id: int,
    limit: int = Query(default=20, le=100, description="每页条数，默认 20"),
    before_id: int = Query(default=0, description="加载此消息 ID 之前的消息，0 表示最新"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取聊天历史（支持分页，before_id=0 返回最新一页）"""
    # 先查缓存
    ck = _history_cache_key(role_id, current_user.id, limit, before_id)
    cached = cache.get(ck)
    if cached is not None:
        return cached

    # 检查角色是否存在（走 roles 缓存，基本无额外开销）
    role = await RoleService.get_role(session, role_id)
    if not role or not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    messages = await ChatService.get_chat_history(
        session, role_id, current_user.id, limit, before_id=before_id
    )
    result = [ChatMessageResponse.model_validate(msg) for msg in messages]
    cache.set(ck, result, _CACHE_HISTORY_TTL)
    return result


@router.post("/send/{role_id}", response_model=ChatResponse)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    role_id: int,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """发送消息"""
    # 检查积分是否充足
    sufficient, balance, required = await CreditService.check_sufficient(
        session, current_user.id, CreditType.CHAT
    )
    if not sufficient:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
        )

    # 检查角色是否存在
    role = await RoleService.get_role(session, role_id)
    if not role or not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 先扣除积分（防止并发请求重复消费）
    await CreditService.deduct(
        session, current_user.id, CreditType.CHAT,
        description=f"与角色 {role.name} 聊天"
    )

    # 保存用户消息
    # 若是该用户与该角色的第一条消息，先把开场白存为 assistant 消息
    existing_history = await ChatService.get_chat_history(
        session, role_id, current_user.id, limit=1
    )
    if not existing_history and role.greeting:
        await ChatService.create_message(
            session, role_id, current_user.id,
            MessageRole.ASSISTANT, role.greeting
        )

    user_msg = await ChatService.create_message(
        session, role_id, current_user.id,
        MessageRole.USER, data.message
    )

    # 调用AI生成回复
    try:
        # 获取历史消息
        history = await ChatService.get_chat_history(
            session, role_id, current_user.id, limit=10
        )

        # 调用AI服务
        result = await AIChatService.chat(
            role_id=role_id,
            user_id=current_user.id,
            message=data.message,
            history=history,
            story_mode=data.story_mode
        )

        # 保存AI回复
        ai_msg = await ChatService.create_message(
            session, role_id, current_user.id,
            MessageRole.ASSISTANT, result["content"]
        )

        # 失效历史缓存（新消息产生，旧缓存不再有效）
        _invalidate_history_cache(role_id, current_user.id)

        return ChatResponse(
            success=True,
            message="发送成功",
            data=ChatMessageResponse.model_validate(ai_msg),
            choices=result.get("choices", [])
        )

    except Exception as e:
        # AI 生成失败，退还积分
        await CreditService.recharge(
            session, current_user.id, required,
            description=f"AI生成失败退还 - 角色 {role.name}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI生成失败: {str(e)}"
        )


@router.post("/send-stream/{role_id}")
@limiter.limit("30/minute")
async def send_message_stream(
    request: Request,
    role_id: int,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """发送消息（SSE 流式输出）

    SSE 事件格式：
    - data: {"type": "token", "content": "..."} — 逐 token 推送
    - data: {"type": "done", "message_id": 123, "choices": [...]} — 完成
    - data: {"type": "error", "detail": "..."} — 错误
    """
    # 检查积分
    sufficient, balance, required = await CreditService.check_sufficient(
        session, current_user.id, CreditType.CHAT
    )
    if not sufficient:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
        )

    # 检查角色
    role = await RoleService.get_role(session, role_id)
    if not role or not role.is_active:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 扣积分
    await CreditService.deduct(
        session, current_user.id, CreditType.CHAT,
        description=f"与角色 {role.name} 聊天"
    )

    # 保存用户消息（若首条消息，先存开场白）
    existing_history = await ChatService.get_chat_history(
        session, role_id, current_user.id, limit=1
    )
    if not existing_history and role.greeting:
        await ChatService.create_message(
            session, role_id, current_user.id,
            MessageRole.ASSISTANT, role.greeting
        )
    await ChatService.create_message(
        session, role_id, current_user.id,
        MessageRole.USER, data.message
    )

    # 获取历史
    history = await ChatService.get_chat_history(
        session, role_id, current_user.id, limit=10
    )

    # 构建消息
    profile, states = AIChatService.get_agent_profile(role_id, current_user.id)
    messages = AIChatService.build_messages(
        role_id, data.message, history, profile, states, story_mode=data.story_mode
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        # 立即发送 ping，让浏览器确认流已打开，避免因等待 AI API 而超时或缓冲
        yield ": ping\n\n"
        full_text = ""
        try:
            async for token in AIChatService.send_chat_request_stream(messages):
                full_text += token
                payload = json.dumps(
                    {"type": "token", "content": token}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            # 流结束后：解析状态 + 保存消息
            clean_text, states_updated = AIChatService.extract_and_update_states(
                full_text, states)

            story_choices: list = []
            if data.story_mode:
                clean_text, story_choices = AIChatService.extract_story_choices(
                    clean_text)

            # 保存 AI 回复到数据库
            with Session(session.bind) as new_session:
                ai_msg = await ChatService.create_message(
                    new_session, role_id, current_user.id,
                    MessageRole.ASSISTANT, clean_text
                )
                msg_id = ai_msg.id

                if states_updated:
                    for state_name, state_data in states.items():
                        await ChatService.update_user_role_state(
                            new_session, current_user.id, role_id,
                            state_name, str(state_data["value"])
                        )

            _invalidate_history_cache(role_id, current_user.id)

            done_payload = json.dumps({
                "type": "done",
                "message_id": msg_id,
                "choices": story_choices
            }, ensure_ascii=False)
            yield f"data: {done_payload}\n\n"

        except Exception as e:
            # 失败退还积分
            with Session(session.bind) as new_session:
                await CreditService.recharge(
                    new_session, current_user.id, required,
                    description=f"AI生成失败退还 - 角色 {role.name}"
                )
            error_payload = json.dumps(
                {"type": "error", "detail": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/sessions")
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取用户的聊天会话列表"""
    from sqlmodel import select, func
    from app.models import Role

    # 查询用户有聊天记录的角色，并获取每个角色的消息数和最后消息时间
    statement = (
        select(
            ChatMessage.role_id,
            func.count(ChatMessage.id).label("message_count"),
            func.max(ChatMessage.created_at).label("last_message_time")
        )
        .where(ChatMessage.user_id == current_user.id)
        .group_by(ChatMessage.role_id)
        .order_by(func.max(ChatMessage.created_at).desc())
    )

    results = session.exec(statement).all()
    if not results:
        return {"success": True, "data": []}

    role_ids = [row[0] for row in results]

    # 一次批量获取所有角色信息（消除 N+1 问题）
    roles_stmt = select(Role).where(
        Role.id.in_(role_ids), Role.is_active == True)
    roles_list = session.exec(roles_stmt).all()
    roles_map = {r.id: r for r in roles_list}

    # 一次批量获取每个角色的最新一条消息
    # 通过子查询：ROW_NUMBER() 排序取每个 role_id 的最新一条
    from sqlalchemy import text
    last_msgs_stmt = (
        select(ChatMessage)
        .where(
            ChatMessage.user_id == current_user.id,
            ChatMessage.role_id.in_(role_ids)
        )
        .order_by(ChatMessage.role_id, ChatMessage.created_at.desc())
    )
    all_msgs = session.exec(last_msgs_stmt).all()
    # 取每个 role_id 的第一条（已按 created_at desc 排序，即最新的）
    last_msg_map: dict = {}
    for msg in all_msgs:
        if msg.role_id not in last_msg_map:
            last_msg_map[msg.role_id] = msg

    sessions = []
    for role_id, message_count, last_time in results:
        role = roles_map.get(role_id)
        if not role:
            continue
        last_msg = last_msg_map.get(role_id)
        sessions.append({
            "role_id": role_id,
            "character": {
                "id": role_id,
                "name": role.name,
                "avatar": role.public_avatar,
                "greeting": role.greeting or ""
            },
            "message_count": message_count,
            "last_message": {
                "content": last_msg.content if last_msg else "",
                "timestamp": last_msg.created_at.isoformat() if last_msg else last_time.isoformat()
            } if last_msg else None
        })

    return {"success": True, "data": sessions}


@router.delete("/history/{role_id}")
async def clear_history(
    role_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """清空聊天历史"""
    await ChatService.clear_history(session, role_id, current_user.id)
    return {"success": True, "message": "聊天记录已清空"}


@router.post("/tts", response_model=TTSResponse)
@limiter.limit("10/minute")
async def generate_tts(
    request: Request,
    data: TTSRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """生成TTS语音"""
    try:
        # 检查积分是否充足
        sufficient, balance, required = await CreditService.check_sufficient(
            session, current_user.id, CreditType.TTS
        )
        if not sufficient:
            return TTSResponse(
                success=False,
                error=f"积分不足，需要 {required} 积分，当前余额 {balance}"
            )

        # 提取说话内容
        speech_text = extract_speech_content(data.text)

        if not speech_text:
            return TTSResponse(
                success=False,
                error="AI回复中没有检测到说话内容"
            )

        # 获取角色声音设置：优先级 聊天设置 voice_ref > 角色自带 > 系统默认
        voice_reference_id = data.voice_ref or None
        if not voice_reference_id and data.role_id:
            role = await RoleService.get_role(session, data.role_id)
            if role and role.voice_reference_id:
                voice_reference_id = role.voice_reference_id

        # 如果没有设置角色声音，使用系统默认声音
        if not voice_reference_id:
            from app.config import get_settings
            settings = get_settings()
            voice_reference_id = settings.SYSTEM_ROLE_VOICE_ID

        # 先扣除积分，生成失败时退还
        await CreditService.deduct(
            session, current_user.id, CreditType.TTS,
            description="生成TTS语音"
        )

        # 生成语音（在线程池执行，避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        audio_path, oss_url = await loop.run_in_executor(
            None, partial(generate_speech, speech_text, voice_reference_id)
        )

        if not audio_path:
            # 生成失败，退还积分
            await CreditService.recharge(
                session, current_user.id, required,
                description="TTS生成失败退还"
            )
            return TTSResponse(
                success=False,
                error="生成语音失败"
            )

        # 优先返回 OSS URL，避免 base64 大包传输
        if oss_url:
            # 异步写回 audio_url 到消息记录（不阻塞响应）
            if data.message_id:
                try:
                    msg = session.get(ChatMessage, data.message_id)
                    if msg and msg.user_id == current_user.id:
                        msg.audio_url = oss_url
                        session.add(msg)
                        session.commit()
                except Exception:
                    pass
            return TTSResponse(success=True, audio_url=oss_url, format='mp3')

        # 回退：读取本地文件以 base64 返回
        import base64
        with open(audio_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')

        return TTSResponse(
            success=True,
            audio=audio_data,
            format='mp3'
        )

    except Exception as e:
        # 若已扣积分则退还（deduct 成功后的异常）
        try:
            await CreditService.recharge(
                session, current_user.id, required,
                description="TTS生成异常退还"
            )
        except Exception:
            pass
        return TTSResponse(
            success=False,
            error=f"TTS生成错误: {str(e)}"
        )


@router.post("/tts-async")
@limiter.limit("10/minute")
async def generate_tts_async(
    request: Request,
    data: TTSRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """异步 TTS：立即返回 task_id，后台生成语音"""
    try:
        sufficient, balance, required = await CreditService.check_sufficient(
            session, current_user.id, CreditType.TTS
        )
        if not sufficient:
            return {"success": False, "error": f"积分不足，需要 {required} 积分，当前余额 {balance}"}

        speech_text = extract_speech_content(data.text)
        if not speech_text:
            return {"success": False, "error": "AI回复中没有检测到说话内容"}

        voice_reference_id = data.voice_ref or None
        if not voice_reference_id and data.role_id:
            role = await RoleService.get_role(session, data.role_id)
            if role and role.voice_reference_id:
                voice_reference_id = role.voice_reference_id
        if not voice_reference_id:
            from app.config import get_settings
            settings = get_settings()
            voice_reference_id = settings.SYSTEM_ROLE_VOICE_ID

        # 先扣积分
        await CreditService.deduct(
            session, current_user.id, CreditType.TTS,
            description="生成TTS语音"
        )

        task_id = str(uuid.uuid4())
        message_id = data.message_id
        user_id = current_user.id

        # 写入 cache（TTL=30分钟，重启也能通过 DB audio_url 兜底）
        with _tts_tasks_lock:
            cache.set(f"{_TTS_KEY_PREFIX}{task_id}", {
                'status': 'PROCESSING',
                'audio_url': None,
                'error': None,
            }, _TTS_TASK_TTL)

        def _run():
            try:
                audio_path, oss_url = generate_speech(
                    speech_text, voice_reference_id)
                if not audio_path and not oss_url:
                    with _tts_tasks_lock:
                        cache.set(f"{_TTS_KEY_PREFIX}{task_id}", {
                            'status': 'ERROR', 'audio_url': None, 'error': '生成语音失败'
                        }, _TTS_TASK_TTL)
                    return

                result_url = oss_url or None
                if not result_url and audio_path:
                    import base64
                    with open(audio_path, 'rb') as f:
                        result_url = 'data:audio/mp3;base64,' + \
                            base64.b64encode(f.read()).decode()

                with _tts_tasks_lock:
                    cache.set(f"{_TTS_KEY_PREFIX}{task_id}", {
                        'status': 'COMPLETED', 'audio_url': result_url, 'error': None
                    }, _TTS_TASK_TTL)

                # 同步写入 DB，重启后前端仍可从消息记录获取
                if result_url and message_id:
                    try:
                        from app.database import engine as _engine
                        with Session(_engine) as db:
                            msg = db.get(ChatMessage, message_id)
                            if msg and msg.user_id == user_id:
                                msg.audio_url = result_url
                                db.add(msg)
                                db.commit()
                    except Exception:
                        pass

            except Exception as e:
                with _tts_tasks_lock:
                    cache.set(f"{_TTS_KEY_PREFIX}{task_id}", {
                        'status': 'ERROR', 'audio_url': None, 'error': str(e)
                    }, _TTS_TASK_TTL)

        threading.Thread(target=_run, daemon=True).start()
        return {"success": True, "task_id": task_id}

    except Exception as e:
        return {"success": False, "error": f"TTS提交失败: {str(e)}"}


@router.get("/tts-status/{task_id}")
async def get_tts_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """查询 TTS 异步任务状态"""
    task = cache.get(f"{_TTS_KEY_PREFIX}{task_id}")
    if not task:
        return {"status": "ERROR", "error": "任务不存在或已过期"}
    return {
        "status": task["status"],
        "audio_url": task.get("audio_url"),
        "error": task.get("error"),
    }


@router.post("/generate-image/{message_id}")
@limiter.limit("10/minute")
async def generate_image(
    request: Request,
    message_id: int,
    data: dict = {},
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """为消息生成配图，data 可含 appearance_tags 覆盖默认角色外貌"""
    try:
        # 检查积分是否充足
        sufficient, balance, required = await CreditService.check_sufficient(
            session, current_user.id, CreditType.TTI
        )
        if not sufficient:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
            )

        # 获取消息
        message = session.get(ChatMessage, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="消息不存在")

        # 获取角色配置
        role = await RoleService.get_role(session, message.role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 读取用户对该角色的当前动态状态（聊天中动态更新的衣物等）
        current_user_states = await ChatService.get_user_role_states(
            session, current_user.id, message.role_id
        )
        current_clothing = current_user_states.get(
            'clothing_state', {}).get('value') or None

        # 读取用户聊天设置面板保存的自定义设置（DB持久化）
        db_chat_settings = await ChatService.get_user_chat_settings(
            session, current_user.id, message.role_id
        )

        # 构建角色配置：优先级 request data覆盖 > DB聊天设置 > UserRoleState当前値 > 角色默认値
        db_appearance = db_chat_settings.appearance_tags if db_chat_settings else None
        db_voice_ref = db_chat_settings.voice_ref if db_chat_settings else None
        db_image_style = db_chat_settings.image_style if db_chat_settings else None
        role_config = {
            "appearance_tags": data.get("appearance_tags") or db_appearance or role.appearance_tags or "",
            "clothing_state": data.get("clothing_state") or current_clothing or role.clothing_state or "整洁的衣服",
            "image_style": data.get("image_style") or db_image_style or role.image_style or "anime",
            "default_scene": role.scenario or "",  # 角色默认场景/环境
        }

        # 获取被点击消息的前一条（用户输入）和当前消息（AI回复）
        # 构成最新一轮对话
        history = await ChatService.get_chat_history(
            session, message.role_id, current_user.id, limit=10
        )

        # 找到被点击的消息在历史中的位置
        chat_history = ""
        for i, msg in enumerate(history):
            if msg.id == message_id:
                # 找到AI回复，同时包含前一条用户消息（如果有）
                if msg.role == "assistant":
                    user_msg = ""
                    if i > 0 and history[i-1].role == "user":
                        user_msg = f"user: {history[i-1].content}\n"
                    ai_msg = f"assistant: {msg.content}"
                    chat_history = user_msg + ai_msg
                else:
                    # 如果点击的是用户消息，只取这条
                    chat_history = f"user: {msg.content}"
                break

        # 如果没找到，默认使用最新消息
        if not chat_history and history:
            latest = history[-1]
            chat_history = f"{latest.role}: {latest.content}"

        # 扣除积分
        await CreditService.deduct(
            session, current_user.id, CreditType.TTI,
            description="生成场景图片",
            related_id=message_id
        )

        # 创建生成任务
        try:
            task_id = ImageService.create_generation_task(
                chat_history, role_config)
        except Exception as task_err:
            # 任务创建失败，退还积分
            await CreditService.recharge(
                session, current_user.id, required,
                description="文生图创建失败退还"
            )
            raise HTTPException(
                status_code=500, detail=f"创建任务失败: {str(task_err)}")

        return {"success": True, "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/image-status/{task_id}")
async def check_image_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """查询图像生成任务状态"""
    try:
        status = ImageService.get_task_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-image/{message_id}")
async def save_image(
    message_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """保存生成的图片URL到消息"""
    try:
        message = session.get(ChatMessage, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="消息不存在")

        # 安全校验：只能操作自己的消息
        if message.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权操作此消息")

        message.image_url = data.get("image_url")
        session.commit()

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-states/{role_id}")
async def reset_role_states(
    role_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """重置用户对特定角色的所有状态为默认值"""
    try:
        # 检查角色是否存在
        role = await RoleService.get_role(session, role_id)
        if not role or not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )

        # 重置用户状态
        success = await ChatService.reset_user_role_states(
            session, current_user.id, role_id
        )

        if success:
            return {
                "success": True,
                "message": f"角色 '{role.name}' 的状态已重置为默认值"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重置状态失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置状态失败: {str(e)}")


@router.get("/states/{role_id}")
async def get_role_states(
    role_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取用户对特定角色的当前状态（用户隔离）"""
    try:
        # 检查角色是否存在
        role = await RoleService.get_role(session, role_id)
        if not role or not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )

        # 获取用户隔离的状态
        states = await ChatService.get_user_role_states(
            session, current_user.id, role_id
        )

        return {
            "success": True,
            "role_id": role_id,
            "role_name": role.name,
            "states": states
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/settings/{role_id}")
async def get_chat_settings(
    role_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取用户聊天自定义设置（外貌、声音等）"""
    try:
        settings = await ChatService.get_user_chat_settings(
            session, current_user.id, role_id
        )
        return {
            "success": True,
            "data": {
                "appearance_tags": settings.appearance_tags if settings else None,
                "voice_ref": settings.voice_ref if settings else None,
                "image_style": settings.image_style if settings else None,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设置失败: {str(e)}")


@router.post("/settings/{role_id}")
async def save_chat_settings(
    role_id: int,
    data: dict = {},
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """保存用户聊天自定义设置（外貌、声音等）"""
    try:
        await ChatService.save_user_chat_settings(
            session,
            current_user.id,
            role_id,
            appearance_tags=data.get("appearance_tags"),
            voice_ref=data.get("voice_ref"),
            image_style=data.get("image_style")
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")


@router.post("/polish-appearance")
async def polish_appearance(
    data: dict,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """AI润色外貌描述，消耗 5 积分"""
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="外貌描述不能为空")

    # 检查积分是否充足
    sufficient, balance, required = await CreditService.check_sufficient(
        session, current_user.id, CreditType.POLISH
    )
    if not sufficient:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
        )

    system_prompt = (
        "You are an expert at writing character appearance descriptions for AI image generation "
        "using Z-Image Turbo (Flux/DiT architecture). Your task is to polish and improve the user's "
        "description into a professional, detailed natural language appearance description.\n\n"
        "RULES:\n"
        "1. Output ONLY the polished description — no explanations, no prefixes, no quotes\n"
        "2. Focus ONLY on fixed physical features: hair color/style/length, eye color, skin tone, "
        "face shape, body type, age range, distinctive facial features\n"
        "3. Do NOT include clothing, pose, action, scene, or background\n"
        "4. Use fluent English natural language sentences (NOT comma-separated tags)\n"
        "5. Target length: 40-80 words\n"
        "6. Preserve all original features — only improve wording and add missing details logically"
    )
    user_content = f"Polish this appearance description:\n{text}"

    # 先扣除积分，LLM 调用失败时退还
    await CreditService.deduct(
        session, current_user.id, CreditType.POLISH,
        description="AI润色外貌描述",
    )

    try:
        polished = await LLMService.call(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=300,
            temperature=0.7,
            timeout=30,
        )
    except (LLMError, Exception) as e:
        # LLM 调用失败，退还积分
        await CreditService.recharge(
            session, current_user.id, required,
            description="AI润色失败退还"
        )
        raise HTTPException(status_code=500, detail=f"AI润色失败: {str(e)}")

    return {"success": True, "polished": polished}


@router.get("/voice-presets")
async def get_voice_presets(session: Session = Depends(get_session)):
    """获取音色预设列表"""
    presets = [
        {
            "id": v["id"],
            "name": v["name"],
            "description": v["description"],
            "reference_id": v["reference_id"],
            "preview_url": f"/api/chat/voice-preview/{v['id']}",
        }
        for v in _get_voice_presets(session)
    ]
    return {"success": True, "presets": presets}


@router.get("/voice-preview/{voice_id}")
async def get_voice_preview(voice_id: str):
    """获取音色试听音频，按需生成并缓存"""
    audio_path = generate_voice_preview(voice_id)
    if not audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"音色 {voice_id} 不存在或生成失败"
        )
    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"preview_{voice_id}.mp3",
    )
