"""
安全中间件
- 安全响应头
- 请求体大小限制

使用纯 ASGI 中间件实现，避免 BaseHTTPMiddleware 缓冲 StreamingResponse（SSE破坏问题）
"""
from starlette.types import ASGIApp, Receive, Scope, Send
from fastapi.responses import JSONResponse


class SecurityHeadersMiddleware:
    """安全响应头中间件（纯 ASGI）"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy",
                     b"accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
                     b"magnetometer=(), microphone=(), payment=(), usb=()"),
                ]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestSizeLimitMiddleware:
    """请求体大小限制中间件（纯 ASGI）"""

    def __init__(self, app: ASGIApp, max_size: int = 10 * 1024 * 1024):
        self.app = app
        self.max_size = max_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode()
                   for k, v in scope.get("headers", [])}
        method = scope.get("method", "")
        if method in ("POST", "PUT", "PATCH"):
            content_length = headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "请求体过大，最大支持 10MB"}
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
