"""Provider-neutral operational events with an explicit safe field allowlist."""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from enum import StrEnum

from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("loadx.operations")
_FIELDS = frozenset(
    {
        "request_id",
        "method",
        "route",
        "status_code",
        "duration_ms",
        "reason",
        "exception_type",
    }
)
_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})


class OperationalEvent(StrEnum):
    APP_STARTED = "APP_STARTED"
    APP_STOPPED = "APP_STOPPED"
    HTTP_REQUEST_COMPLETED = "HTTP_REQUEST_COMPLETED"
    HTTP_REQUEST_FAILED = "HTTP_REQUEST_FAILED"
    READINESS_FAILED = "READINESS_FAILED"
    INTEGRATION_HEALTH_FAILED = "INTEGRATION_HEALTH_FAILED"
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"


def emit_operational_event(
    event: OperationalEvent,
    *,
    level: int = logging.INFO,
    alert: bool = False,
    **details: str | float | None,
) -> None:
    if set(details) - _FIELDS:
        raise ValueError("unsupported operational event fields")
    if any(
        not isinstance(value, str | int | float | type(None))
        for value in details.values()
    ):
        raise TypeError("unsupported operational event value")
    payload = {
        "event": event.value,
        "occurred_at": datetime.now(UTC).isoformat(),
        "service": "loadx-api",
        "level": logging.getLevelName(level),
        "alert": alert,
        "request_id": request_id_context.get(),
        **details,
    }
    logger.log(level, json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


class SafeServerErrorFilter(logging.Filter):
    """Uvicorn must not reprint the exception payload suppressed by API handlers."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info or record.exc_text:
            record.msg = (
                "Unhandled ASGI exception; see HTTP_REQUEST_FAILED operational event"
            )
            record.args = ()
            record.exc_info = None
            record.exc_text = None
        return True


def configure_observability(level: str) -> None:
    for name, configured_level in (
        ("loadx.operations", level),
        ("loadx.security", "INFO"),
    ):
        target = logging.getLogger(name)
        target.setLevel(configured_level)
        if not any(
            getattr(handler, "loadx_stdout", False) for handler in target.handlers
        ):
            handler = logging.StreamHandler(sys.__stdout__)
            handler.loadx_stdout = True
            handler.setFormatter(logging.Formatter("%(message)s"))
            target.addHandler(handler)
    server_logger = logging.getLogger("uvicorn.error")
    if not any(
        isinstance(item, SafeServerErrorFilter) for item in server_logger.filters
    ):
        server_logger.addFilter(SafeServerErrorFilter())


def safe_route(scope: Scope) -> str:
    route = scope.get("route")
    return getattr(route, "path", "__unmatched__")


class OperationalContextMiddleware:
    def __init__(self, app: ASGIApp, *, log_requests: bool = True) -> None:
        self.app = app
        self.log_requests = log_requests

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)
        started = time.monotonic()
        status_code = 500

        async def send_with_context(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message["headers"] = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != b"x-request-id"
                ] + [(b"x-request-id", request_id.encode("ascii"))]
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            try:
                if self.log_requests:
                    emit_operational_event(
                        OperationalEvent.HTTP_REQUEST_COMPLETED,
                        level=logging.ERROR if status_code >= 500 else logging.INFO,
                        alert=status_code >= 500,
                        method=scope["method"]
                        if scope["method"] in _METHODS
                        else "OTHER",
                        route=safe_route(scope),
                        status_code=status_code,
                        duration_ms=round((time.monotonic() - started) * 1000, 3),
                    )
            finally:
                request_id_context.reset(token)
