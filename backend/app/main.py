"""
FastAPI主入口
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import create_db_and_tables
from app.routers import auth_router, roles_router, chat_router, bot_router, credits_router, payment_router, checkin_router
from app.admin.router import router as admin_router
from app.core.limiter import limiter
from app.core.logger import setup_logging, get_logger
from app.middleware.security import SecurityHeadersMiddleware, RequestSizeLimitMiddleware
from app.middleware.logging import RequestLoggingMiddleware

logger = get_logger("main")


settings = get_settings()

# ── 启动安全检查 ──────────────────────────────────────────────────────────
_UNSAFE_KEYS = {"CHANGE-ME-IN-PRODUCTION-USE-RANDOM-64-CHAR-STRING",
                "your-secret-key-change-in-production"}
if settings.SECRET_KEY in _UNSAFE_KEYS:
    import sys
    if settings.DEBUG:
        logger.warning(
            "⚠️  SECRET_KEY 使用默认值，仅允许在 DEBUG 模式下运行，生产环境请在 .env 中设置强随机密钥")
    else:
        logger.critical(
            "🚨 SECRET_KEY 使用不安全的默认值！生产环境拒绝启动，请在 .env 中设置 SECRET_KEY")
        sys.exit(1)
# ─────────────────────────────────────────────────────────────────────────

# 初始化日志系统
setup_logging(
    level="DEBUG" if settings.DEBUG else "INFO",
    json_format=not settings.DEBUG,  # 开发环境用文本格式，生产用JSON
    log_file="logs/nyx_ai.log" if not settings.DEBUG else None
)

# 本地 cache 目录（存放 TTS 音频 + 文生图图片）
CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))),
    'cache'
)
os.makedirs(os.path.join(CACHE_DIR, 'tts'), exist_ok=True)
os.makedirs(os.path.join(CACHE_DIR, 'images'), exist_ok=True)
os.makedirs(os.path.join(CACHE_DIR, 'avatars'), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    create_db_and_tables()
    logger.info("✅ 数据库表已创建")
    yield
    # 关闭时的清理工作
    logger.info("👋 应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="Nyx AI Backend API - Next.js + FastAPI",
    version="2.0.0",
    lifespan=lifespan
)

# 注册限流器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 请求日志中间件（最先注册，记录所有请求）
app.add_middleware(RequestLoggingMiddleware)

# 安全中间件
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 根路由
@app.get("/")
async def root():
    """根路由"""
    return {
        "name": settings.APP_NAME,
        "version": "2.0.0",
        "status": "running"
    }


# Prometheus 指标端点（需要 METRICS_TOKEN 鉴权，防止监控数据泄露）
@app.get("/metrics")
async def metrics(request: Request):
    """Prometheus 监控指标（Bearer token 鉴权）"""
    metrics_token = settings.METRICS_TOKEN
    if metrics_token:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != metrics_token:
            from fastapi.responses import Response as _Resp
            return _Resp(status_code=401, content="Unauthorized")
    from app.core.metrics import get_metrics, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)


# 健康检查
@app.get("/health")
async def health_check():
    """
    健康检查端点

    检查内容：
    - 数据库连接
    - Redis 连接（如配置了）
    - 外部 API 可用性（降级标记）
    """
    from sqlalchemy import text
    from app.core.cache import cache as app_cache

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0",
        "checks": {}
    }

    # 检查数据库
    try:
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "ok"}
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error", "message": str(e)}
        health_status["status"] = "unhealthy"

    # 内存缓存状态
    health_status["checks"]["cache"] = {
        "status": "ok",
        "type": "memory",
        "size": app_cache.size
    }

    # 检查外部 API（仅检查配置，不实际调用）
    external_apis = {
        "openrouter": bool(settings.OPENROUTER_API_KEY),
        "zimage": bool(settings.ZIMAGE_API_KEY),
        "fish_audio": bool(settings.FISH_AUDIO_API_KEY),
    }
    health_status["checks"]["external_apis"] = {
        "status": "ok",
        "configured": external_apis
    }

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


# 挂载本地缓存目录为静态文件（/cache/images 和 /cache/tts）
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")

# 注册路由
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(roles_router, prefix=settings.API_PREFIX)
app.include_router(chat_router, prefix=settings.API_PREFIX)
app.include_router(bot_router, prefix=settings.API_PREFIX)
app.include_router(credits_router, prefix=settings.API_PREFIX)
app.include_router(payment_router, prefix=settings.API_PREFIX)
app.include_router(checkin_router, prefix=settings.API_PREFIX)

# 管理后台（无 /api 前缀，直接挂载到 /admin）
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
