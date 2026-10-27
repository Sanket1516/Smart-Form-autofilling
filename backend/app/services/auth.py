"""Authentication service and login rate limiter."""

import asyncio
import hashlib
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any, Protocol

from pymongo.errors import DuplicateKeyError
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import CurrentUser, LoginData, PublicUser, RegisterData, RegisterRequest

_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


class AuthError(Exception):
    def __init__(
        self, code: str, message: str, status_code: int, details: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class UserStore(Protocol):
    async def get_by_email(self, email: str) -> dict[str, Any] | None: ...
    async def get(self, user_id: str) -> dict[str, Any] | None: ...
    async def create(self, document: Any) -> dict[str, Any]: ...


class RevocationStore(Protocol):
    async def revoke(self, token_id: str, expires_at: datetime) -> None: ...
    async def is_revoked(self, token_id: str) -> bool: ...


class LoginRateLimiter:
    def __init__(self, attempts: int, window_seconds: int, storage_uri: str = "") -> None:
        self.attempts = attempts
        self.window_seconds = window_seconds
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._redis = Redis.from_url(storage_uri, decode_responses=True) if storage_uri else None

    async def allow(self, key: str) -> bool:
        if self._redis is not None:
            redis_key = self._redis_key(key)
            count = await self._redis.eval(
                "local n=redis.call('INCR',KEYS[1]); "
                "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n",
                1,
                redis_key,
                self.window_seconds,
            )
            return int(count) <= self.attempts

        now = time.monotonic()
        async with self._lock:
            if len(self._events) >= 10_000:
                for stored_key, stored_events in list(self._events.items()):
                    if not stored_events or now - stored_events[-1] >= self.window_seconds:
                        self._events.pop(stored_key, None)
                if len(self._events) >= 10_000:
                    self._events.pop(next(iter(self._events)))
            events = self._events[key]
            while events and now - events[0] >= self.window_seconds:
                events.popleft()
            if len(events) >= self.attempts:
                return False
            events.append(now)
            return True

    async def clear(self, key: str) -> None:
        if self._redis is not None:
            await self._redis.delete(self._redis_key(key))
            return
        async with self._lock:
            self._events.pop(key, None)

    @staticmethod
    def _redis_key(key: str) -> str:
        return f"smart-form:login:{hashlib.sha256(key.encode()).hexdigest()}"

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()


class AuthService:
    def __init__(self, users: UserStore, revocations: RevocationStore, settings: Settings) -> None:
        self.users = users
        self.revocations = revocations
        self.settings = settings
        self.rate_limiter = LoginRateLimiter(
            settings.auth_login_rate_limit_attempts,
            settings.auth_login_rate_limit_window_seconds,
            settings.rate_limit_storage_uri,
        )

    async def close(self) -> None:
        await self.rate_limiter.close()

    @staticmethod
    def _public_user(document: dict[str, Any]) -> PublicUser:
        return PublicUser(
            user_id=str(document["_id"]),
            full_name=document["full_name"],
            email=document["email"],
        )

    async def register(self, request: RegisterRequest) -> RegisterData:
        existing = await self.users.get_by_email(str(request.email).lower())
        if existing is not None:
            raise AuthError(
                "EMAIL_ALREADY_EXISTS", "An account with this email already exists", 409
            )
        now = datetime.now(UTC)
        from app.models.documents import UserDocument

        document = UserDocument(
            full_name=request.full_name,
            email=str(request.email).lower(),
            password_hash=hash_password(request.password),
            status="active",
            created_at=now,
            updated_at=now,
        )
        try:
            created = await self.users.create(document)
        except DuplicateKeyError as error:
            raise AuthError(
                "EMAIL_ALREADY_EXISTS", "An account with this email already exists", 409
            ) from error
        return RegisterData(
            user_id=str(created["_id"]),
            full_name=created["full_name"],
            email=created["email"],
        )

    async def login(self, email: str, password: str, rate_key: str) -> LoginData:
        if not await self.rate_limiter.allow(rate_key):
            raise AuthError("RATE_LIMITED", "Too many login attempts", 429)
        user = await self.users.get_by_email(email.lower())
        # Always run one bcrypt comparison so response time does not reveal
        # whether the email is registered.
        stored_hash = user.get("password_hash", "") if user else _DUMMY_HASH
        password_ok = verify_password(password, stored_hash)
        if user is None or not password_ok:
            raise AuthError("INVALID_CREDENTIALS", "Invalid email or password", 401)
        if user.get("status") != "active":
            raise AuthError("INVALID_CREDENTIALS", "Invalid email or password", 401)
        await self.rate_limiter.clear(rate_key)
        return LoginData(
            access_token=create_access_token(str(user["_id"]), self.settings),
            user=self._public_user(user),
        )

    async def current_user(self, token: str) -> tuple[CurrentUser, dict[str, Any]]:
        try:
            payload = decode_access_token(token, self.settings)
            if await self.revocations.is_revoked(payload["jti"]):
                raise TokenError("revoked access token")
        except TokenError as error:
            raise AuthError("UNAUTHORIZED", "Authentication required", 401) from error
        user = await self.users.get(payload["sub"])
        if user is None or user.get("status") != "active":
            raise AuthError("UNAUTHORIZED", "Authentication required", 401)
        return (
            CurrentUser(
                user_id=str(user["_id"]),
                full_name=user["full_name"],
                email=user["email"],
                status=user["status"],
            ),
            payload,
        )

    async def logout(self, payload: dict[str, Any]) -> None:
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        await self.revocations.revoke(payload["jti"], expires_at)
