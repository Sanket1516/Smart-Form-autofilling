"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.api_errors import APIError
from app.core.rate_limit import limiter
from app.schemas.auth import CurrentUser, LoginData, LoginRequest, RegisterData, RegisterRequest
from app.schemas.responses import MessageResponse, SuccessResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


async def get_current_user(request: Request, credentials: Credentials) -> CurrentUser:
    """Resolve the bearer token. Tokens are only accepted in the Authorization header."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise APIError("UNAUTHORIZED", "Authentication required", 401)
    user, payload = await get_auth_service(request).current_user(credentials.credentials)
    request.state.token_payload = payload
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
    credentials: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[LoginData]:
    client_host = request.client.host if request.client else "unknown"
    data = await auth.login(
        str(credentials.email), credentials.password, f"{client_host}:{credentials.email.lower()}"
    )
    return SuccessResponse(data=data, message="Login successful")


@router.get("/me", response_model=SuccessResponse[CurrentUser])
async def me(current_user: User) -> SuccessResponse[CurrentUser]:
    return SuccessResponse(data=current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, _: User) -> MessageResponse:
    await get_auth_service(request).logout(request.state.token_payload)
    return MessageResponse(message="Logout successful")


@router.delete("/me", response_model=MessageResponse)
async def delete_me(request: Request, current_user: User) -> MessageResponse:
    """Delete the account and every record, file and vector the user owns."""
    await get_auth_service(request).logout(request.state.token_payload)
    await request.app.state.user_data_service.delete_all(current_user.user_id, delete_account=True)
    return MessageResponse(message="Account and all data deleted")
