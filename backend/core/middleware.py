import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.config import settings

logger = logging.getLogger("whitfield.request")


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send, status_code=400, detail="Invalid Content-Length")
                return

        consumed = 0

        async def limited_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.max_bytes:
                    raise _BodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLarge:
            await self._reject(send)

    @staticmethod
    async def _reject(send: Send, status_code: int = 413, detail: str = "Request body too large") -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send({"type": "http.response.start", "status": status_code, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


class _BodyTooLarge(Exception):
    pass


class RequestSecurityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        request_id = self._request_id(scope)
        scope.setdefault("state", {})["request_id"] = request_id
        client_ip = scope.get("client", ("unknown", 0))[0]
        if await self._rate_limited(client_ip):
            body = b'{"detail":"Rate limit exceeded"}'
            await send({"type": "http.response.start", "status": 429, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"retry-after", str(settings.rate_limit_window_seconds).encode()), (b"x-request-id", request_id.encode())]})
            await send({"type": "http.response.body", "body": body})
            return

        status_code = 500

        async def secure_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (b"cache-control", b"no-store"),
                ])
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, secure_send)
        finally:
            logger.info(json.dumps({"request_id": request_id, "method": scope.get("method"), "path": scope.get("path"), "status": status_code, "duration_ms": round((time.perf_counter() - started) * 1000, 2), "client_ip": client_ip}))

    async def _rate_limited(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - settings.rate_limit_window_seconds
        async with self._lock:
            bucket = self._requests[client_ip]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= settings.rate_limit_requests:
                return True
            bucket.append(now)
            if len(self._requests) > 10_000:
                for key in list(self._requests)[:1_000]:
                    if not self._requests[key] or self._requests[key][-1] < cutoff:
                        self._requests.pop(key, None)
            return False

    @staticmethod
    def _request_id(scope: Scope) -> str:
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                candidate = value.decode("ascii", errors="ignore")
                if 8 <= len(candidate) <= 64 and all(char.isalnum() or char in "-_." for char in candidate):
                    return candidate
        return str(uuid4())
