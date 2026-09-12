"""Global API exception handlers."""

import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.api_errors import APIError
from app.schemas.responses import ErrorPayload, ErrorResponse
from app.services.auth import AuthError

logger = logging.getLogger(__name__)


def _error_response(
    request: Request,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorPayload(
            code=code,
            message=message,
            details={"request_id": request.state.request_id, **(details or {})},
        )
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error_response(
        request,
        "VALIDATION_ERROR",
        "Request validation failed",
        {"fields": jsonable_encoder(exc.errors())},
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def http_exception_handler(
    request: Request, exc: HTTPException | StarletteHTTPException
) -> JSONResponse:
    details = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return _error_response(
        request,
        f"HTTP_{exc.status_code}",
        "Request failed",
        details,
        exc.status_code,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception")
    return _error_response(request, "INTERNAL_SERVER_ERROR", "Internal server error")


async def application_error_handler(request: Request, exc: APIError | AuthError) -> JSONResponse:
    return _error_response(request, exc.code, exc.message, exc.details, exc.status_code)
