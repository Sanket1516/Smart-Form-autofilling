"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.api_errors import APIError
from app.schemas.auth import (
    CurrentUser,
    LoginData,
    LoginRequest,
    RegisterData,
    RegisterRequest,
)
from app.schemas.responses import MessageResponse, SuccessResponse
from app.schemas.responses import MessageResponse, SuccessResponse
from app.services.auth import AuthService
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


async def get_current_user(
    request: Request,
    credentials: Credentials,
) -> CurrentUser:
    token_str = None
    if credentials and credentials.scheme.lower() == "bearer":
        token_str = credentials.credentials
    elif "token" in request.query_params:
        token_str = request.query_params["token"]

    if not token_str:
        raise APIError("UNAUTHORIZED", "Authentication required", 401)
    user, _ = await get_auth_service(request).current_user(token_str)
    return user


@router.post("/register", response_model=SuccessResponse[RegisterData], status_code=201)
@limiter.limit("10/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)]
) -> SuccessResponse[RegisterData]:
    return SuccessResponse(
        data=await auth.register(body), message="User registered successfully"
    )


@router.post("/login", response_model=SuccessResponse[LoginData])
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[LoginData]:
    client_host = request.client.host if request.client else "unknown"
    data = await auth.login(
        str(credentials.email), credentials.password, f"{client_host}:{credentials.email.lower()}"
    )
    return SuccessResponse(data=data, message="Login successful")


@router.get("/me", response_model=SuccessResponse[CurrentUser])
async def me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> SuccessResponse[CurrentUser]:
    return SuccessResponse(data=current_user)


@router.delete("/me", response_model=MessageResponse)
async def delete_me(
    request: Request,
    credentials: Credentials,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MessageResponse:
    if credentials is None:
        raise APIError("UNAUTHORIZED", "Authentication required", 401)
    
    # Delete account logic
    auth = get_auth_service(request)
    await auth.delete_account(current_user.user_id)
    
    # Also log out
    _, payload = await request.app.state.auth_service.current_user(credentials.credentials)
    await request.app.state.auth_service.logout(payload)
    
    return MessageResponse(message="Account deleted successfully")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    credentials: Credentials,
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> MessageResponse:
    if credentials is None:
        raise APIError("UNAUTHORIZED", "Authentication required", 401)
    _, payload = await request.app.state.auth_service.current_user(credentials.credentials)
    await request.app.state.auth_service.logout(payload)
    return MessageResponse(message="Logout successful")
