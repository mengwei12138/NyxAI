"""
请求日志中间件
记录所有请求的详细信息

使用纯 ASGI 中间件实现，避免 BaseHTTPMiddleware 缓冲 StreamingResponse（SSE破坏问题）
"""
import time
import uuid
from starlette.types import ASGIApp, Receive, Scope, Send
from app.core.logger import get_logger

logger = get_logger("http")


class RequestLoggingMiddleware:
    """请求日志中间件（纯 ASGI，不缓冲响应体）"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        method = scope.get("method", "")
        path = scope.get("path", "")
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        headers_list = scope.get("headers", [])
        headers = {k.decode().lower(): v.decode() for k, v in headers_list}
        user_agent = headers.get("user-agent", "")

        # 尝试获取用户ID
        user_id = None
        try:
            auth_header = headers.get("authorization", "")
            if auth_header.startswith("bearer "):
                token = auth_header[7:]
                from jose import jwt
                from app.config import get_settings
                settings = get_settings()
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[
                                     settings.ALGORITHM])
                user_id = payload.get("sub")
        except Exception:
            pass

        extra = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }
        if user_id:
            extra["user_id"] = user_id

        logger.info(f"→ {method} {path}", extra=extra)

        status_code_holder = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code_holder[0] = message.get("status", 200)
                # 注入 X-Request-ID 头
                headers_out = list(message.get("headers", []))
                headers_out.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers_out}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            extra.update(
                {"status_code": 500, "duration_ms": duration_ms, "error": str(e)})
            logger.exception(
                f"✕ {method} {path} ERROR ({duration_ms}ms)", extra=extra)
            raise

        duration_ms = round((time.time() - start_time) * 1000, 2)
        status_code = status_code_holder[0]
        extra.update({"status_code": status_code, "duration_ms": duration_ms})
        log_msg = f"← {method} {path} {status_code} ({duration_ms}ms)"
        if status_code >= 500:
            logger.error(log_msg, extra=extra)
        elif status_code >= 400:
            logger.warning(log_msg, extra=extra)
        else:
            logger.info(log_msg, extra=extra)
