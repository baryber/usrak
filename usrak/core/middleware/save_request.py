import json
from io import BytesIO
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request
from starlette.responses import Response
from usrak.core.logger import logger


class SaveRequestBodyASGIMiddleware:
    PROTECTED_PATH_PREFIXES = ["/auth"]
    MAX_BODY_SIZE = 1024 * 1024  # 1MB

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        method = scope["method"]
        headers = {k.decode(): v.decode() for k, v in scope["headers"]}
        content_type = headers.get("content-type", "")

        if (
            not any(path.startswith(prefix) for prefix in self.PROTECTED_PATH_PREFIXES)
            or method != "POST"
            or "application/json" not in content_type
        ):
            await self.app(scope, receive, send)
            return

        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

            if len(body) > self.MAX_BODY_SIZE:
                logger.warning(f"Request body too large for {path}")
                response = Response("Request body too large", status_code=413)
                await response(scope, receive, send)
                return

        # Save body in scope for later
        async def inner_receive():
            nonlocal body
            yield_body = body
            body = b""
            return {"type": "http.request", "body": yield_body, "more_body": False}

        scope["receive"] = inner_receive

        # Hack: set request.state.body manually
        request = Request(scope, receive=inner_receive)
        try:
            request.state.body = json.loads(body.decode())
            logger.debug(f"[ASGI] Parsed JSON body on {path}")
        except json.JSONDecodeError:
            request.state.body = {}
            logger.warning(f"[ASGI] Failed to parse JSON body on {path}")

        await self.app(scope, inner_receive, send)
