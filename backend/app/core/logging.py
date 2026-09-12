"""Structured application logging and request correlation."""

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    """Render log records as compact JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
        }
        for field in ("method", "path", "status_code", "duration_ms"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Configure one JSON stream handler for the application process."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    handler = next((item for item in root_logger.handlers if getattr(item, "_json", False)), None)
    if handler is None:
        handler = logging.StreamHandler()
        handler._json = True  # type: ignore[attr-defined]
        root_logger.addHandler(handler)
    handler.setFormatter(JsonFormatter())


def get_request_id() -> str:
    return _request_id.get()


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add request IDs and structured completion logs to every request."""
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
    token = _request_id.set(request_id)
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        logging.getLogger("app.request").info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response
    finally:
        _request_id.reset(token)
