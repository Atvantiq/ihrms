"""Structured logging + per-request correlation IDs.

Every request gets a request_id (from the inbound X-Request-ID header or a
fresh uuid). It is attached to every log line for that request and returned
in the X-Request-ID response header so support can trace an issue end to end.
Logs are emitted as single-line JSON for ingestion by Loki/CloudWatch/etc.

Implemented as PURE ASGI middleware (not BaseHTTPMiddleware) so the
request_id contextvar propagates correctly to route handlers AND exception
handlers — BaseHTTPMiddleware runs the app in a separate task and would
break that propagation.
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("uvicorn.access").disabled = True


log = logging.getLogger("ihrms")


class RequestContextMiddleware:
    """Pure ASGI middleware: sets request_id contextvar, echoes the header,
    and logs one structured access line per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        inbound = headers.get(b"x-request-id")
        rid = inbound.decode() if inbound else uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = rid
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            log.info(
                "request",
                extra={
                    "extra_fields": {
                        "method": scope.get("method"),
                        "path": scope.get("path"),
                        "status": status,
                        "ms": elapsed_ms,
                    }
                },
            )
            request_id_ctx.reset(token)
