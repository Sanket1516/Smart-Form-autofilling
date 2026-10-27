"""Authentication endpoints."""

import hmac
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.api_errors import APIError
from app.core.rate_limit import limiter
from app.schemas.auth import CurrentUser, LoginData, LoginRequest, RegisterData, RegisterRequest
from app.schemas.responses import MessageResponse, SuccessResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
SESSION_COOKIE = "smart_form_session"
CSRF_COOKIE = "smart_form_csrf"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


async def get_current_user(request: Request, credentials: Credentials) -> CurrentUser:
    """Resolve an extension bearer token or a CSRF-protected dashboard cookie."""
    bearer_token = None
    if credentials is not None:
        if credentials.scheme.lower() != "bearer" or not credentials.credentials:
            raise APIError("UNAUTHORIZED", "Authentication required", 401)
        bearer_token = credentials.credentials

    cookie_authenticated = bearer_token is None
    token = bearer_token or request.cookies.get(SESSION_COOKIE)
    if not token:
        raise APIError("UNAUTHORIZED", "Authentication required", 401)

    if cookie_authenticated and request.method.upper() not in _SAFE_METHODS:
        origin = request.headers.get("origin", "")
        csrf_cookie = request.cookies.get(CSRF_COOKIE, "")
        csrf_header = request.headers.get("x-csrf-token", "")
        if origin not in request.app.state.settings.cors_origin_list:
            raise APIError("CSRF_VALIDATION_FAILED", "Request origin is not allowed", 403)
        if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise APIError("CSRF_VALIDATION_FAILED", "CSRF token is missing or invalid", 403)

    user, payload = await get_auth_service(request).current_user(token)
    request.state.token_payload = payload
    request.state.cookie_authenticated = cookie_authenticated
    return user


User = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/register", response_model=SuccessResponse[RegisterData], status_code=201)
@limiter.limit("10/minute")
async def register(
    request: Request, body: RegisterRequest, auth: Annotated[AuthService, Depends(get_auth_service)]
) -> SuccessResponse[RegisterData]:
    return SuccessResponse(data=await auth.register(body), message="User registered successfully")


@router.post("/login", response_model=SuccessResponse[LoginData])
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[LoginData]:
    from app.core.rate_limit import get_client_address

    client_host = get_client_address(request)
    data = await auth.login(
        str(credentials.email), credentials.password, f"{client_host}:{credentials.email.lower()}"
    )
    settings = request.app.state.settings
    secure = settings.app_env == "production"
    max_age = settings.jwt_access_token_expire_minutes * 60
    response.set_cookie(
        SESSION_COOKIE,
        data.access_token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1",
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )
    return SuccessResponse(data=data, message="Login successful")


@router.get("/me", response_model=SuccessResponse[CurrentUser])
async def me(current_user: User) -> SuccessResponse[CurrentUser]:
    return SuccessResponse(data=current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, response: Response, _: User) -> MessageResponse:
    await get_auth_service(request).logout(request.state.token_payload)
    _clear_auth_cookies(request, response)
    return MessageResponse(message="Logout successful")


@router.delete("/me", response_model=MessageResponse)
async def delete_me(request: Request, response: Response, current_user: User) -> MessageResponse:
    """Delete the account and every record, file and vector the user owns."""
    await get_auth_service(request).logout(request.state.token_payload)
    await request.app.state.user_data_service.delete_all(current_user.user_id, delete_account=True)
    _clear_auth_cookies(request, response)
    return MessageResponse(message="Account and all data deleted")


def _clear_auth_cookies(request: Request, response: Response) -> None:
    secure = request.app.state.settings.app_env == "production"
    response.delete_cookie(
        SESSION_COOKIE, path="/api/v1", secure=secure, httponly=True, samesite="lax"
    )
    response.delete_cookie(CSRF_COOKIE, path="/", secure=secure, httponly=False, samesite="lax")
