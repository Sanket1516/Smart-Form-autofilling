"""Structured JSON logging, request correlation and PII/secret redaction.

Every log line passes through ``redact``: bearer tokens, JWTs, email addresses
and long digit runs (phone, account and ID numbers) are masked. Code must still
avoid logging document text, field values or passwords at all.
"""

import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

_REDACTIONS = (
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[JWT]"),
    (
        re.compile(r"(?i)(api[_-]?key|password|secret|token)(\"?\s*[:=]\s*\"?)[^\s\",}]+"),
        r"\1\2[REDACTED]",
    ),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[EMAIL]"),
    (re.compile(r"(?<!\d)\+?\d[\d -]{7,}\d(?!\d)"), "[NUMBER]"),
)
_SENSITIVE_KEY = re.compile(r"(?i)(authorization|api[_-]?key|password|secret|token|credential)")
_STRUCTURAL_KEYS = {"timestamp", "level", "logger", "request_id", "status_code", "duration_ms"}
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}


def redact(text: str) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def _redact_value(value: Any) -> Any:
    """Redact recognizable secrets and values stored under secret keys."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return redact(value)
    return value


class JsonFormatter(logging.Formatter):
    """Render log records as compact, redacted JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in payload.items():
            if key not in _STRUCTURAL_KEYS:
                payload[key] = "[REDACTED]" if _SENSITIVE_KEY.search(key) else _redact_value(value)
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
    for noisy in ("httpx", "httpcore", "pymongo", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_request_id() -> str:
    return _request_id.get()


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add a request ID and one structured completion log line per request."""
    supplied = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = supplied if _SAFE_REQUEST_ID.match(supplied) else str(uuid.uuid4())
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
