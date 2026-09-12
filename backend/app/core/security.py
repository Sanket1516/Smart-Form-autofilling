"""Password hashing and JWT access-token helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import Settings


class TokenError(ValueError):
    """Raised when an access token is missing, invalid, or expired."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "jti": str(uuid4()),
        "iat": now,
        "exp": expires_at,
        "typ": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "jti", "exp", "iat"]},
        )
    except jwt.PyJWTError as error:
        raise TokenError("invalid access token") from error
    if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("jti"), str):
        raise TokenError("invalid access token")
    return payload
