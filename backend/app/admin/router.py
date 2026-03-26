"""
管理后台路由 - Jinja2 模板渲染，无需前端框架
"""
import os
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlmodel import Session, select, func, delete

from app.database import get_session
from app.models import (
    User, Role, ChatMessage, UserCredits,
    CreditTransaction,
    RoleState, UserRoleState, UserChatSettings,
    VoicePreset
)
from app.services import CreditService
from app.services.audit_service import AuditService
from app.admin.auth import create_admin_cookie, get_admin_user_id
from app.core.cache import invalidate_role, cache
from app.config import get_settings

# 登录限流 cache key 前缀
_FAIL_KEY_PREFIX = "admin_login_fail:"
_FAIL_LIMIT = 10      # 最多失败次数
_LOCK_SECS = 120      # 锁定时长（秒）

# 模板目录（相对于 backend/ 根目录运行）
_BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(
    directory=os.path.join(_BASE_DIR, "app", "templates"))

_settings = get_settings()
_ADMIN_PREFIX = _settings.ADMIN_PATH  # 从配置读取隐秘路径
router = APIRouter(prefix=_ADMIN_PREFIX, tags=["管理后台"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 将 admin_path 注入为 Jinja2 全局变量，模板中可直接使用 {{ admin_path }}
templates.env.globals["admin_path"] = _ADMIN_PREFIX


# ────────────────────────────────
# 辅助：获取当前管理员 User 对象
# ────────────────────────────────
def _get_admin(user_id: int | None, session: Session) -> User | None:
    if user_id is None:
        return None
    user = session.get(User, user_id)
    if user is None or not user.is_admin or not user.is_active:
        return None
    return user


def _require_admin(user_id: int | None, session: Session):
    """返回管理员 User，或者返回重定向 Response"""
    admin = _get_admin(user_id, session)
    if admin is None:
        return None, RedirectResponse(f"{_ADMIN_PREFIX}/login", status_code=302)
    return admin, None


# ────────────────────────────────
# 登录 / 登出
# ────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "error": error
    })


@router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    client_ip = request.client.host if request.client else "unknown"
    fail_key = f"{_FAIL_KEY_PREFIX}{client_ip}"
    fail_count: int = cache.get(fail_key) or 0

    if fail_count >= _FAIL_LIMIT:
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": f"登录尝试过于频繁，请 {_LOCK_SECS} 秒后再试"
        }, status_code=429)

    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not user.is_admin or not user.is_active:
        cache.set(fail_key, fail_count + 1, _LOCK_SECS)
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": "用户名或密码错误，或无管理员权限"
        })
    if not pwd_context.verify(password, user.password_hash):
        cache.set(fail_key, fail_count + 1, _LOCK_SECS)
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": "用户名或密码错误，或无管理员权限"
        })
    # 登录成功，清除失败计数
    cache.delete(fail_key)

    # 记录登录审计日志
    AuditService.log_admin_login(
        session=session,
        admin_id=user.id,
        admin_username=user.username,
        success=True,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent")
    )

    cookie_val = create_admin_cookie(user.id)
    response = RedirectResponse(_ADMIN_PREFIX, status_code=302)
    response.set_cookie(
        "admin_session", cookie_val,
        httponly=True, samesite="lax", max_age=86400
    )
    return response


@router.get("/logout")
async def logout(
    request: Request,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    # 记录登出审计日志
    admin = _get_admin(user_id, session)
    if admin:
        AuditService.log_admin_logout(
            session=session,
            admin_id=admin.id,
            admin_username=admin.username,
            ip_address=request.client.host if request.client else None
        )

    response = RedirectResponse(f"{_ADMIN_PREFIX}/login", status_code=302)
    response.delete_cookie("admin_session")
    return response


# ────────────────────────────────
# 仪表盘
# ────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir

    total_users = session.exec(select(func.count(User.id))).first() or 0
    total_roles = session.exec(select(func.count(Role.id))).first() or 0
    total_messages = session.exec(
        select(func.count(ChatMessage.id))).first() or 0
    total_credits_spent = session.exec(
        select(func.sum(CreditTransaction.amount)).where(
            CreditTransaction.amount < 0)
    ).first() or 0

    # 今日新增用户（UTC，与 created_at 时区一致）
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0)
    today_users = session.exec(
        select(func.count(User.id)).where(User.created_at >= today_start)
    ).first() or 0

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "admin": admin,
        "stats": {
            "total_users": total_users,
            "total_roles": total_roles,
            "total_messages": total_messages,
            "total_credits_spent": abs(total_credits_spent),
            "today_users": today_users,
        }
    })


# ────────────────────────────────
# 用户管理
# ────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    q: str = "",
    page: int = 1,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir

    PAGE_SIZE = 20
    stmt = select(User)
    if q:
        stmt = stmt.where(User.username.contains(q))
    stmt = stmt.order_by(User.id.desc()).offset(
        (page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    users = session.exec(stmt).all()

    # 批量查积分
    user_ids = [u.id for u in users]
    credits_map: dict[int, int] = {}
    if user_ids:
        credits_rows = session.exec(
            select(UserCredits).where(UserCredits.user_id.in_(user_ids))
        ).all()
        credits_map = {c.user_id: c.balance for c in credits_rows}

    total = session.exec(
        select(func.count(User.id)).where(
            User.username.contains(q) if q else True)
    ).first() or 0

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "admin": admin,
        "users": users,
        "credits_map": credits_map,
        "q": q,
        "page": page,
        "total": total,
        "page_size": PAGE_SIZE,
        "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
    })


@router.post("/users/{uid}/toggle")
async def user_toggle(
    request: Request,
    uid: int,
    q: str = Form(""),
    page: int = Form(1),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    target = session.get(User, uid)
    if target and target.id != admin.id:  # 不能封禁自己
        target.is_active = not target.is_active
        session.add(target)
        session.commit()

        # 记录审计日志
        AuditService.log_user_ban(
            session=session,
            admin_id=admin.id,
            admin_username=admin.username,
            user_id=target.id,
            username=target.username,
            is_banned=not target.is_active,
            ip_address=request.client.host if request.client else None
        )
    return RedirectResponse(f"{_ADMIN_PREFIX}/users?q={q}&page={page}", status_code=302)


@router.post("/users/{uid}/recharge")
async def user_recharge(
    request: Request,
    uid: int,
    amount: int = Form(...),
    description: str = Form("管理员充值"),
    q: str = Form(""),
    page: int = Form(1),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    if amount > 0:
        target = session.get(User, uid)
        await CreditService.recharge(session, uid, amount, description)

        # 记录审计日志
        if target:
            AuditService.log_user_recharge(
                session=session,
                admin_id=admin.id,
                admin_username=admin.username,
                user_id=target.id,
                username=target.username,
                amount=amount,
                description=description,
                ip_address=request.client.host if request.client else None
            )
    return RedirectResponse(f"{_ADMIN_PREFIX}/users?q={q}&page={page}", status_code=302)


# ────────────────────────────────
# 头像上传 / 生成（管理员专用）
# ────────────────────────────────

_BASE_DIR_ADMIN = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
_AVATAR_DIR = os.path.join(_BASE_DIR_ADMIN, 'cache', 'avatars')
os.makedirs(_AVATAR_DIR, exist_ok=True)


@router.post("/upload-avatar")
async def admin_upload_avatar(
    file: UploadFile = File(...),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """管理员上传头像图片（返回 JSON）"""
    admin, redir = _require_admin(user_id, session)
    if redir:
        return JSONResponse({"success": False, "detail": "未登录"}, status_code=401)

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        return JSONResponse({"success": False, "detail": "不支持的图片格式"}, status_code=400)

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return JSONResponse({"success": False, "detail": "图片不能超过 5MB"}, status_code=400)

    import uuid as _uuid
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(file.content_type, "jpg")
    filename = f"{_uuid.uuid4().hex}.{ext}"
    with open(os.path.join(_AVATAR_DIR, filename), "wb") as f:
        f.write(content)

    return JSONResponse({"success": True, "url": f"/cache/avatars/{filename}"})


@router.post("/roles/{rid}/generate-avatar")
async def admin_generate_avatar(
    rid: int,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """管理员为角色 AI 生成头像（不扣积分）"""
    admin, redir = _require_admin(user_id, session)
    if redir:
        return JSONResponse({"success": False, "detail": "未登录"}, status_code=401)

    role = session.get(Role, rid)
    if not role:
        return JSONResponse({"success": False, "detail": "角色不存在"}, status_code=404)

    from app.services.image_service import ImageService
    from app.utils.prompts import get_image_generation_config

    appearance_tags = role.appearance_tags or f"1girl, {role.name}, anime character"
    image_style = role.image_style or "anime"

    _style_map = {
        "动漫": "anime", "二次元": "anime",
        "写实": "photorealistic", "超写实": "photorealistic",
        "插画": "oil_painting", "水彩": "oil_painting",
        "赛博朋克": "anime", "像素风": "anime", "昭和": "showa",
    }
    image_style_key = _style_map.get(image_style, image_style)
    config = get_image_generation_config()
    styles = config.get("styles", {})
    style_data = styles.get(image_style_key, styles.get("anime", {}))
    style_keywords = style_data.get(
        "style_desc", "(masterpiece, best quality, anime style:1.2)")

    prompt = (
        f"{appearance_tags}, "
        f"solo, full body, standing, looking at viewer, "
        f"simple background, white background, "
        f"{style_keywords}"
    ).strip(", ")

    zimage_task_id = ImageService.generate_image_async(prompt, "")
    if not zimage_task_id:
        return JSONResponse({"success": False, "detail": "Z-image API 调用失败"}, status_code=500)

    local_task_id = ImageService.register_zimage_task(zimage_task_id)
    return JSONResponse({"success": True, "task_id": local_task_id})


@router.get("/image-status/{task_id}")
async def admin_image_status(
    task_id: str,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """查询头像生成任务状态"""
    admin, redir = _require_admin(user_id, session)
    if redir:
        return JSONResponse({"success": False, "detail": "未登录"}, status_code=401)

    from app.services.image_service import ImageService
    result = ImageService.get_task_status(task_id)
    return JSONResponse(result)


@router.post("/roles/{rid}/save-avatar")
async def admin_save_avatar(
    rid: int,
    image_url: str = Form(...),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """管理员将生成的图片保存为角色头像"""
    admin, redir = _require_admin(user_id, session)
    if redir:
        return JSONResponse({"success": False, "detail": "未登录"}, status_code=401)

    role = session.get(Role, rid)
    if not role:
        return JSONResponse({"success": False, "detail": "角色不存在"}, status_code=404)

    import hashlib
    import shutil
    try:
        import requests as _req
        url_hash = hashlib.md5(image_url.encode()).hexdigest()
        ext = "jpg"
        for candidate in ("png", "webp", "gif"):
            if candidate in image_url.lower():
                ext = candidate
                break
        filename = f"{url_hash}.{ext}"
        local_path = os.path.join(_AVATAR_DIR, filename)
        if not os.path.exists(local_path):
            if image_url.startswith("/cache/"):
                src = os.path.normpath(os.path.join(
                    _BASE_DIR_ADMIN, '..', image_url.lstrip("/")))
                if os.path.exists(src):
                    shutil.copy2(src, local_path)
                else:
                    return JSONResponse({"success": False, "detail": "本地图片不存在"}, status_code=500)
            else:
                resp = _req.get(image_url, timeout=30)
                if resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                else:
                    return JSONResponse({"success": False, "detail": "下载图片失败"}, status_code=500)
        avatar_url = f"/cache/avatars/{filename}"
    except Exception as e:
        return JSONResponse({"success": False, "detail": f"保存失败: {e}"}, status_code=500)

    role.public_avatar = avatar_url
    session.add(role)
    session.commit()
    return JSONResponse({"success": True, "avatar_url": avatar_url})


# ────────────────────────────────
# 角色管理
# ────────────────────────────────

@router.get("/roles", response_class=HTMLResponse)
async def roles_page(
    request: Request,
    q: str = "",
    page: int = 1,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir

    PAGE_SIZE = 20
    stmt = select(Role)
    if q:
        stmt = stmt.where(Role.name.contains(q))
    stmt = stmt.order_by(Role.id.desc()).offset(
        (page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    roles = session.exec(stmt).all()

    # 批量查创建者用户名
    creator_ids = list({r.user_id for r in roles})
    creators_map: dict[int, str] = {}
    if creator_ids:
        creators = session.exec(select(User).where(
            User.id.in_(creator_ids))).all()
        creators_map = {u.id: u.username for u in creators}

    total = session.exec(
        select(func.count(Role.id)).where(Role.name.contains(q) if q else True)
    ).first() or 0

    # 音色预设列表（供角色音色设置下拉框使用）
    voice_presets = session.exec(
        select(VoicePreset).where(VoicePreset.is_active ==
                                  True).order_by(VoicePreset.sort_order)
    ).all()

    # 构建 reference_id -> name 映射，方便模板显示
    voice_map = {v.reference_id: v.name for v in voice_presets}

    return templates.TemplateResponse("admin/roles.html", {
        "request": request,
        "admin": admin,
        "roles": roles,
        "creators_map": creators_map,
        "q": q,
        "page": page,
        "total": total,
        "page_size": PAGE_SIZE,
        "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        "voice_presets": voice_presets,
        "voice_map": voice_map,
    })


@router.post("/roles/create")
async def role_create(
    request: Request,
    name: str = Form(...),
    title: str = Form(""),
    public_summary: str = Form(""),
    persona: str = Form(""),
    user_persona: str = Form(""),
    scenario: str = Form(""),
    greeting: str = Form(""),
    storyline: str = Form(""),
    world_setting: str = Form(""),
    plot_milestones: str = Form(""),
    tags: str = Form(""),
    visibility: str = Form("public"),
    is_system: bool = Form(False),
    appearance_tags: str = Form(""),
    image_style: str = Form("anime"),
    clothing_state: str = Form(""),
    voice_reference_id: str = Form(""),
    public_avatar: str = Form(""),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    now = datetime.utcnow()
    role = Role(
        user_id=admin.id,
        name=name.strip(),
        title=title.strip() or None,
        public_summary=public_summary.strip() or None,
        persona=persona.strip(),
        user_persona=user_persona.strip() or None,
        scenario=scenario.strip() or None,
        greeting=greeting.strip() or None,
        storyline=storyline.strip() or None,
        world_setting=world_setting.strip() or None,
        plot_milestones=plot_milestones.strip() or None,
        tags=tags.strip() or None,
        visibility=visibility if visibility in (
            "public", "private") else "public",
        is_system=is_system,
        is_active=True,
        appearance_tags=appearance_tags.strip() or None,
        image_style=image_style.strip() or "anime",
        clothing_state=clothing_state.strip() or None,
        voice_reference_id=voice_reference_id.strip() or None,
        public_avatar=public_avatar.strip() or None,
        created_at=now,
        updated_at=now,
    )
    session.add(role)
    session.commit()
    return RedirectResponse(f"{_ADMIN_PREFIX}/roles", status_code=302)


@router.post("/roles/create-json")
async def role_create_json(
    request: Request,
    name: str = Form(...),
    title: str = Form(""),
    public_summary: str = Form(""),
    persona: str = Form(""),
    user_persona: str = Form(""),
    scenario: str = Form(""),
    greeting: str = Form(""),
    storyline: str = Form(""),
    world_setting: str = Form(""),
    plot_milestones: str = Form(""),
    tags: str = Form(""),
    visibility: str = Form("public"),
    is_system: bool = Form(False),
    appearance_tags: str = Form(""),
    image_style: str = Form("anime"),
    clothing_state: str = Form(""),
    voice_reference_id: str = Form(""),
    public_avatar: str = Form(""),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """创建角色并返回 JSON（供 AI 生成封面的两步流程使用）"""
    admin, redir = _require_admin(user_id, session)
    if redir:
        return JSONResponse({"success": False, "detail": "未登录"}, status_code=401)
    now = datetime.utcnow()
    role = Role(
        user_id=admin.id,
        name=name.strip(),
        title=title.strip() or None,
        public_summary=public_summary.strip() or None,
        persona=persona.strip(),
        user_persona=user_persona.strip() or None,
        scenario=scenario.strip() or None,
        greeting=greeting.strip() or None,
        storyline=storyline.strip() or None,
        world_setting=world_setting.strip() or None,
        plot_milestones=plot_milestones.strip() or None,
        tags=tags.strip() or None,
        visibility=visibility if visibility in (
            "public", "private") else "public",
        is_system=is_system,
        is_active=True,
        appearance_tags=appearance_tags.strip() or None,
        image_style=image_style.strip() or "anime",
        clothing_state=clothing_state.strip() or None,
        voice_reference_id=voice_reference_id.strip() or None,
        public_avatar=public_avatar.strip() or None,
        created_at=now,
        updated_at=now,
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    return JSONResponse({"success": True, "role_id": role.id})


@router.post("/roles/{rid}/toggle")
async def role_toggle(
    request: Request,
    rid: int,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    role = session.get(Role, rid)
    if role:
        role.is_active = not role.is_active
        session.add(role)
        session.commit()
        invalidate_role(rid)

        # 记录审计日志
        AuditService.log_role_toggle(
            session=session,
            admin_id=admin.id,
            admin_username=admin.username,
            role_id=role.id,
            role_name=role.name,
            is_active=role.is_active,
            ip_address=request.client.host if request.client else None
        )
    return RedirectResponse(f"{_ADMIN_PREFIX}/roles", status_code=302)


@router.post("/roles/{rid}/delete")
async def role_delete(
    request: Request,
    rid: int,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    role = session.get(Role, rid)
    if role:
        role_name = role.name  # 保存角色名用于审计日志
        try:
            # 批量 DELETE 关联表（高效，避免逐行加载）
            for model_cls, field in [
                (RoleState, RoleState.role_id),
                (UserRoleState, UserRoleState.role_id),
                (UserChatSettings, UserChatSettings.role_id),
                (ChatMessage, ChatMessage.role_id),
            ]:
                session.exec(delete(model_cls).where(field == rid))
            session.delete(role)
            session.commit()
            invalidate_role(rid)

            # 记录审计日志
            AuditService.log_role_delete(
                session=session,
                admin_id=admin.id,
                admin_username=admin.username,
                role_id=rid,
                role_name=role_name,
                ip_address=request.client.host if request.client else None
            )
        except Exception:
            session.rollback()
            raise
    return RedirectResponse(f"{_ADMIN_PREFIX}/roles", status_code=302)


# ────────────────────────────────
# 积分管理
# ────────────────────────────────

@router.get("/credits", response_class=HTMLResponse)
async def credits_page(
    request: Request,
    q: str = "",
    page: int = 1,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir

    PAGE_SIZE = 20

    # 积分从高到低排列所有用户
    base_stmt = (
        select(User, UserCredits)
        .join(UserCredits, UserCredits.user_id == User.id, isouter=True)
    )
    if q:
        base_stmt = base_stmt.where(User.username.contains(q))

    total = session.exec(
        select(func.count(User.id)).where(
            User.username.contains(q) if q else True
        )
    ).first() or 0

    rows = session.exec(
        base_stmt
        .order_by(UserCredits.balance.desc().nulls_last(), User.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()

    # rows 是 (User, UserCredits|None) 元组列表
    user_credits_list = [
        {"user": u, "credits": c}
        for u, c in rows
    ]

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    return templates.TemplateResponse("admin/credits.html", {
        "request": request,
        "admin": admin,
        "q": q,
        "page": page,
        "total": total,
        "page_size": PAGE_SIZE,
        "total_pages": total_pages,
        "user_credits_list": user_credits_list,
    })


@router.post("/credits/recharge")
async def credits_recharge(
    target_uid: int = Form(...),
    amount: int = Form(...),
    description: str = Form("管理员充值"),
    q: str = Form(""),
    page: int = Form(1),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    if amount > 0:
        target = session.get(User, target_uid)
        await CreditService.recharge(session, target_uid, amount, description)
        if target:
            AuditService.log_user_recharge(
                session=session,
                admin_id=admin.id,
                admin_username=admin.username,
                user_id=target.id,
                username=target.username,
                amount=amount,
                description=description,
                ip_address=request.client.host if request.client else None
            )
    return RedirectResponse(f"{_ADMIN_PREFIX}/credits?q={q}&page={page}", status_code=302)


@router.post("/credits/deduct")
async def credits_deduct(
    request: Request,
    target_uid: int = Form(...),
    amount: int = Form(...),
    description: str = Form("管理员扣减"),
    q: str = Form(""),
    page: int = Form(1),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """管理员扣减用户积分（amount 为正数，实际扣减）"""
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    if amount > 0:
        target = session.get(User, target_uid)
        if target:
            # 使用专用 admin_deduct（防止余额变负）
            await CreditService.admin_deduct(session, target_uid, amount, description)
            AuditService.log_user_recharge(
                session=session,
                admin_id=admin.id,
                admin_username=admin.username,
                user_id=target.id,
                username=target.username,
                amount=-amount,
                description=description,
                ip_address=request.client.host if request.client else None
            )
    return RedirectResponse(f"{_ADMIN_PREFIX}/credits?q={q}&page={page}", status_code=302)


# ────────────────────────────────
# 音色管理
# ────────────────────────────────

@router.get("/voices", response_class=HTMLResponse)
async def voices_page(
    request: Request,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    voices = session.exec(
        select(VoicePreset).order_by(VoicePreset.sort_order, VoicePreset.id)
    ).all()
    return templates.TemplateResponse("admin/voices.html", {
        "request": request,
        "admin": admin,
        "voices": voices,
    })


@router.post("/voices/create")
async def voice_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    reference_id: str = Form(...),
    preview_text: str = Form(""),
    sort_order: int = Form(0),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    from datetime import datetime
    import re as _re
    # 自动生成 preset_id（英文小写+下划线）
    preset_id = _re.sub(r'[^a-z0-9_]', '_', name.lower().strip()
                        )[:64] or f"voice_{int(datetime.utcnow().timestamp())}"
    # 确保唯一
    existing = session.exec(select(VoicePreset).where(
        VoicePreset.preset_id == preset_id)).first()
    if existing:
        preset_id = f"{preset_id}_{int(datetime.utcnow().timestamp())}"
    now = datetime.utcnow()
    voice = VoicePreset(
        preset_id=preset_id,
        name=name.strip(),
        description=description.strip() or None,
        reference_id=reference_id.strip(),
        preview_text=preview_text.strip() or None,
        sort_order=sort_order,
        is_active=True,
        is_default=False,
        created_at=now,
        updated_at=now,
    )
    session.add(voice)
    session.commit()
    return RedirectResponse(f"{_ADMIN_PREFIX}/voices", status_code=302)


@router.post("/voices/{vid}/edit")
async def voice_edit(
    request: Request,
    vid: int,
    name: str = Form(...),
    description: str = Form(""),
    reference_id: str = Form(...),
    preview_text: str = Form(""),
    sort_order: int = Form(0),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    voice = session.get(VoicePreset, vid)
    if voice:
        from datetime import datetime
        voice.name = name.strip()
        voice.description = description.strip() or None
        voice.reference_id = reference_id.strip()
        voice.preview_text = preview_text.strip() or None
        voice.sort_order = sort_order
        voice.updated_at = datetime.utcnow()
        session.add(voice)
        session.commit()
    return RedirectResponse(f"{_ADMIN_PREFIX}/voices", status_code=302)


@router.post("/voices/{vid}/toggle")
async def voice_toggle(
    request: Request,
    vid: int,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    voice = session.get(VoicePreset, vid)
    if voice:
        from datetime import datetime
        voice.is_active = not voice.is_active
        voice.updated_at = datetime.utcnow()
        session.add(voice)
        session.commit()
    return RedirectResponse(f"{_ADMIN_PREFIX}/voices", status_code=302)


@router.post("/voices/{vid}/set-default")
async def voice_set_default(
    request: Request,
    vid: int,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    # 清除所有 is_default，再设置目标
    from datetime import datetime
    all_voices = session.exec(select(VoicePreset)).all()
    now = datetime.utcnow()
    for v in all_voices:
        if v.is_default:
            v.is_default = False
            v.updated_at = now
            session.add(v)
    target = session.get(VoicePreset, vid)
    if target:
        target.is_default = True
        target.updated_at = now
        session.add(target)
    session.commit()
    return RedirectResponse(f"{_ADMIN_PREFIX}/voices", status_code=302)


@router.post("/voices/{vid}/delete")
async def voice_delete(
    request: Request,
    vid: int,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    voice = session.get(VoicePreset, vid)
    if voice and not voice.is_default:
        session.delete(voice)
        session.commit()
    return RedirectResponse(f"{_ADMIN_PREFIX}/voices", status_code=302)


# ────────────────────────────────
# 角色音色设置
# ────────────────────────────────

# ────────────────────────────────
# 充值方案管理
# ────────────────────────────────

@router.get("/packages", response_class=HTMLResponse)
async def packages_page(
    request: Request,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """充值方案管理页面"""
    from app.models.payment import PaymentPackage
    from sqlmodel import select as sm_select
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    packages = list(session.exec(
        sm_select(PaymentPackage).order_by(PaymentPackage.sort_order)
    ).all())
    return templates.TemplateResponse("admin/packages.html", {
        "request": request,
        "admin": admin,
        "packages": packages,
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type", "success"),
    })


@router.post("/packages")
async def packages_save(
    request: Request,
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """保存充值方案配置（写入数据库，重启后持久有效）"""
    from app.models.payment import PaymentPackage
    from sqlmodel import select as sm_select
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir

    form = await request.form()
    try:
        # 获取提交的所有 package_id（支持动态数量）
        pkg_ids = form.getlist("package_ids")
        if not pkg_ids:
            # 兼容旧模板：固定三档
            pkg_ids = ["starter", "standard", "pro"]

        for pkg_id in pkg_ids:
            name = str(form.get(f"{pkg_id}__name", "")).strip()
            plan_id = str(form.get(f"{pkg_id}__plan_id", "")).strip()
            amount = float(form.get(f"{pkg_id}__amount", 0))
            credits = int(form.get(f"{pkg_id}__credits", 0))
            desc = str(form.get(f"{pkg_id}__desc", "")).strip()
            popular = f"{pkg_id}__popular" in form
            sort_order = int(form.get(f"{pkg_id}__sort_order", 0))

            if not name or not plan_id or amount <= 0 or credits <= 0:
                raise ValueError(
                    f"{pkg_id} 数据不合法（名称、plan_id 不能为空，金额/积分必须 > 0）")

            # upsert：已存在则更新，不存在则创建
            pkg = session.exec(
                sm_select(PaymentPackage).where(
                    PaymentPackage.package_id == pkg_id)
            ).first()
            if pkg:
                pkg.name = name
                pkg.plan_id = plan_id
                pkg.amount = amount
                pkg.credits = credits
                pkg.desc = desc
                pkg.popular = popular
                pkg.sort_order = sort_order
            else:
                pkg = PaymentPackage(
                    package_id=pkg_id,
                    name=name,
                    plan_id=plan_id,
                    amount=amount,
                    credits=credits,
                    desc=desc,
                    popular=popular,
                    sort_order=sort_order,
                    is_active=True,
                )
            session.add(pkg)

        session.commit()
        return RedirectResponse(f"{_ADMIN_PREFIX}/packages?msg=保存成功&msg_type=success", status_code=302)
    except Exception as e:
        return RedirectResponse(f"{_ADMIN_PREFIX}/packages?msg=保存失败：{e}&msg_type=error", status_code=302)


@router.post("/roles/{rid}/set-voice")
async def role_set_voice(
    request: Request,
    rid: int,
    voice_reference_id: str = Form(...),
    user_id: int | None = Depends(get_admin_user_id),
    session: Session = Depends(get_session)
):
    """设置角色绑定的音色（voice_reference_id）"""
    admin, redir = _require_admin(user_id, session)
    if redir:
        return redir
    role = session.get(Role, rid)
    if role:
        # 空字符串表示清除绑定（使用默认音色）
        role.voice_reference_id = voice_reference_id.strip() or None
        session.add(role)
        session.commit()
    return RedirectResponse(f"{_ADMIN_PREFIX}/roles", status_code=302)
