"""
角色路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlmodel import Session
from typing import List, Optional
import json
import re
import os
import uuid
from app.database import get_session
from app.models import (
    Role, RoleCreate, RoleUpdate, RoleResponse,
    RoleListResponse, User, CreditType
)
from app.services import RoleService, CreditService, ChatService, LLMService, LLMError
from app.dependencies import get_current_user, get_current_user_optional
from app.config import get_settings
from app.utils.prompts import get_appearance_tags_generator_prompt
from app.core.cache import (
    cache, CACHE_ROLES_LIST, CACHE_ROLE_DETAIL, CACHE_VOICE_PRESETS,
    TTL_ROLES_LIST, TTL_ROLE_DETAIL, TTL_VOICE_PRESETS, invalidate_role
)

settings = get_settings()

router = APIRouter(prefix="/roles", tags=["角色"])

# 头像存储目录
_BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
AVATAR_DIR = os.path.join(_BASE_DIR, '..', 'cache', 'avatars')
os.makedirs(AVATAR_DIR, exist_ok=True)


@router.get("/voice-presets")
async def get_voice_presets_api(
    session: Session = Depends(get_session)
):
    """获取激活的音色预设列表（公开接口，供前端角色编辑页使用）"""
    cached = cache.get(CACHE_VOICE_PRESETS)
    if cached is not None:
        return cached
    from app.services.tts_service import get_voice_presets
    presets = get_voice_presets(session)
    result = {"success": True, "data": presets}
    cache.set(CACHE_VOICE_PRESETS, result, TTL_VOICE_PRESETS)
    return result


@router.get("", response_model=RoleListResponse)
async def get_roles(
    mode: str = Query(default="public", description="public或my"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: Session = Depends(get_session)
):
    """获取角色列表"""
    user_id = current_user.id if current_user else None

    # mode=my 需要登录
    if mode == "my" and not user_id:
        return RoleListResponse(
            success=True,
            data=[],
            is_logged_in=False
        )

    # 公开列表走缓存（my列表因人而异不缓存）
    if mode == "public":
        cache_key = f"{CACHE_ROLES_LIST}public"
        cached = cache.get(cache_key)
        if cached is not None:
            # 填入当前用户的登录态（列表数据共享，登录态是实时的）
            cached["is_logged_in"] = current_user is not None
            return cached

    is_admin = current_user.is_admin if current_user else False
    roles = await RoleService.get_roles(session, user_id, mode, is_admin=is_admin)
    result = RoleListResponse(
        success=True,
        data=roles,
        is_logged_in=current_user is not None
    )

    if mode == "public":
        cache.set(f"{CACHE_ROLES_LIST}public",
                  result.model_dump(), TTL_ROLES_LIST)

    return result


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: Session = Depends(get_session)
):
    """获取单个角色详情"""
    # 先查缓存
    cache_key = f"{CACHE_ROLE_DETAIL}{role_id}"
    cached_role = cache.get(cache_key)
    if cached_role is None:
        cached_role = await RoleService.get_role(session, role_id)
        if cached_role and cached_role.is_active:
            cache.set(cache_key, cached_role, TTL_ROLE_DETAIL)

    role = cached_role
    if not role or not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 检查权限：私密角色需要登录且是创建者
    if role.visibility == "private":
        if not current_user or role.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此角色"
            )

    return RoleResponse.model_validate(role)


@router.post("", response_model=RoleResponse)
async def create_role(
    data: RoleCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """创建角色"""
    # 检查积分是否充足
    sufficient, balance, required = await CreditService.check_sufficient(
        session, current_user.id, CreditType.CREATE_ROLE
    )
    if not sufficient:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
        )

    # 创建角色
    role = await RoleService.create_role(session, current_user.id, data)

    # 扣除积分
    await CreditService.deduct(
        session, current_user.id, CreditType.CREATE_ROLE,
        description=f"创建角色: {role.name}",
        related_id=role.id
    )

    # 失效角色列表缓存
    invalidate_role(role.id)

    return RoleResponse.model_validate(role)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """更新角色"""
    try:
        role = await RoleService.update_role(
            session, role_id, current_user.id, data
        )
        invalidate_role(role_id)
        return RoleResponse.model_validate(role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """删除角色"""
    try:
        await RoleService.delete_role(session, role_id, current_user.id)
        invalidate_role(role_id)
        return {"success": True, "message": "角色已删除"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{role_id}/public")
async def get_role_public(
    role_id: int,
    session: Session = Depends(get_session)
):
    """获取角色公开信息（游客可访问）"""
    role = await RoleService.get_role(session, role_id)
    if not role or not role.is_active or role.visibility != "public":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    return {
        "id": role.id,
        "name": role.name,
        "public_summary": role.public_summary,
        "tags": role.tags,
        "public_avatar": role.public_avatar,
        "greeting": role.greeting
    }


@router.get("/{role_id}/states")
async def get_role_states(
    role_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取角色状态"""
    role = await RoleService.get_role(session, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 检查权限（公开角色或自己的角色）
    if role.visibility != "public" and role.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此角色"
        )

    # 返回用户隔离状态（与 /chat/states/{role_id} 一致）
    states = await ChatService.get_user_role_states(session, current_user.id, role_id)
    return {"states": states}


@router.post("/generate-tags")
async def generate_appearance_tags(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    使用 LLM 将中文外貌描述转换为英文 Stable Diffusion Tags
    """
    description = data.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="描述不能为空")

    try:
        system_prompt = get_appearance_tags_generator_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Description: {description}"}
        ]
        tags = await LLMService.call(messages, max_tokens=200, temperature=0.7, timeout=30)
        tags = tags.replace('"', '').replace("'", "")
        return {"success": True, "tags": tags}
    except LLMError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate")
async def generate_role(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    使用自然语言描述生成角色信息
    用户输入描述，LLM 生成完整的角色配置
    """
    description = data.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="描述不能为空")

    try:
        from app.utils.prompts import get_role_generator_prompt
        system_prompt = get_role_generator_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": description}
        ]
        content = await LLMService.call(messages, max_tokens=2000, temperature=0.8, timeout=60)

        # 解析 JSON（可能被 markdown 包裹）
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            role_data = json.loads(json_match.group())
        else:
            role_data = json.loads(content)

        return {"success": True, "data": role_data}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON 解析失败: {str(e)}")
    except LLMError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    上传角色头像图片
    支持格式：JPEG, PNG, WebP，大小限制 5MB
    """
    # 校验 MIME 类型
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片格式，请上传 JPEG/PNG/WebP"
        )

    # 读取内容并校验大小
    content = await file.read()
    max_size = 5 * 1024 * 1024  # 5MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="图片大小不能超过 5MB"
        )

    # 生成唯一文件名
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(file.content_type, "jpg")
    filename = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(AVATAR_DIR, filename)

    # 保存文件
    with open(save_path, "wb") as f:
        f.write(content)

    return {"success": True, "url": f"/cache/avatars/{filename}"}


@router.post("/{role_id}/generate-avatar")
async def generate_avatar(
    role_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    为角色 AI 生成头像（调用 Z-image，消耗积分）
    基于角色的 appearance_tags 和 image_style 生成竖版立绘
    """
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 权限校验：只有创建者可以生成
    if role.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此角色")

    # 检查积分是否充足（复用文生图积分类型）
    sufficient, balance, required = await CreditService.check_sufficient(
        session, current_user.id, CreditType.TTI
    )
    if not sufficient:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，需要 {required} 积分，当前余额 {balance}"
        )

    # 构建立绘 prompt
    from app.utils.prompts import get_image_generation_config
    appearance_tags = role.appearance_tags or ""
    image_style = role.image_style or "anime"

    # 中文画风名称映射到英文 key
    _style_name_map = {
        "动漫": "anime", "二次元": "anime",
        "写实": "photorealistic", "超写实": "photorealistic",
        "插画": "oil_painting", "水彩": "oil_painting",
        "赛博朋克": "anime",
        "像素风": "anime",
        "昭和": "showa",
    }
    image_style_key = _style_name_map.get(image_style, image_style)

    config = get_image_generation_config()
    styles = config.get("styles", {})
    style_data = styles.get(image_style_key, styles.get("anime", {}))
    style_keywords = style_data.get(
        "style_desc", "(masterpiece, best quality, anime style:1.2)")

    # 如果没有 appearance_tags，使用角色名+通用描述生成基础 prompt
    if not appearance_tags:
        appearance_tags = f"1girl, {role.name}, anime character"

    # 竖版立绘构图
    prompt = (
        f"{appearance_tags}, "
        f"solo, full body, standing, looking at viewer, "
        f"simple background, white background, "
        f"{style_keywords}"
    ).strip(", ")

    # 调用 Z-image 异步生成
    from app.services.image_service import ImageService
    print(f"[Avatar] 生成头像，role={role.name}, prompt={prompt[:80]}...")
    zimage_task_id = ImageService.generate_image_async(prompt, "")
    print(f"[Avatar] Z-image 返回 task_id: {zimage_task_id}")
    if not zimage_task_id:
        raise HTTPException(
            status_code=500, detail="Z-image API 调用失败，请检查 API Key 配置")

    # 注册到本地任务系统，前端通过本地 task_id 轮询
    local_task_id = ImageService.register_zimage_task(zimage_task_id)

    # 扣除积分
    await CreditService.deduct(
        session, current_user.id, CreditType.TTI,
        description=f"生成角色头像: {role.name}",
        related_id=role.id
    )

    return {"success": True, "task_id": local_task_id}


@router.post("/{role_id}/save-avatar")
async def save_avatar(
    role_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    将生成完成的头像图片保存到角色
    image_url 为 Z-image 返回的外部 URL，会被下载到本地 cache/avatars/
    """
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此角色")

    image_url = data.get("image_url", "").strip()
    if not image_url:
        raise HTTPException(status_code=400, detail="image_url 不能为空")

    # 下载或复制图片到本地 cache/avatars/
    import hashlib
    import shutil
    import requests as req
    try:
        url_hash = hashlib.md5(image_url.encode()).hexdigest()
        ext = "jpg"
        for candidate in ("png", "webp", "gif"):
            if candidate in image_url.lower():
                ext = candidate
                break
        filename = f"{url_hash}.{ext}"
        local_path = os.path.join(AVATAR_DIR, filename)

        if not os.path.exists(local_path):
            if image_url.startswith("/cache/"):
                # 本地路径：直接复制文件（cache 目录在项目根，即 _BASE_DIR/..）
                src_path = os.path.normpath(os.path.join(
                    _BASE_DIR, '..', image_url.lstrip("/")))
                if os.path.exists(src_path):
                    shutil.copy2(src_path, local_path)
                else:
                    raise HTTPException(
                        status_code=500, detail=f"本地图片文件不存在: {src_path}")
            else:
                # 外部 URL：下载
                resp = req.get(image_url, timeout=30)
                if resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                else:
                    raise HTTPException(status_code=500, detail="下载图片失败")

        local_url = f"/cache/avatars/{filename}"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存头像失败: {str(e)}")

    # 更新角色头像
    role.public_avatar = local_url
    session.add(role)
    session.commit()

    # 失效该角色的缓存（头像更新了）
    invalidate_role(role_id)

    return {"success": True, "avatar_url": local_url}
