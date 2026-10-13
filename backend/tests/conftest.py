"""Shared pytest fixtures for the backend test suite."""

from collections.abc import Iterator
from datetime import datetime
from typing import Any
import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["AUTH_LOGIN_RATE_LIMIT_ATTEMPTS"] = "100"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.v1.auth import get_auth_service  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.auth import AuthService  # noqa: E402

class MockSentenceTransformer:
    def __init__(self, model_name: str, *args, **kwargs):
        pass
    def encode(self, texts, **kwargs):
        class DummyVec:
            def tolist(self):
                return [0.1] * 1024
        
        if isinstance(texts, str):
            return DummyVec()
        return [DummyVec() for _ in texts]
        
    def get_sentence_embedding_dimension(self):
        return 1024

@pytest.fixture(autouse=True)
def mock_sentence_transformers(monkeypatch):
    import sys
    import types
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = MockSentenceTransformer # type: ignore
    sys.modules["sentence_transformers"] = module
    yield
    del sys.modules["sentence_transformers"]


class FakeUsers:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self.next_id = 1

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return next((user for user in self.users.values() if user["email"] == email), None)

    async def get(self, user_id: str) -> dict[str, Any] | None:
        return self.users.get(user_id)

    async def create(self, document: Any) -> dict[str, Any]:
        user_id = f"user-{self.next_id}"
        self.next_id += 1
        user = {"_id": user_id, **document.model_dump(exclude_none=True)}
        self.users[user_id] = user
        return user


class FakeRevocations:
    def __init__(self) -> None:
        self.revoked: set[str] = set()

    async def revoke(self, token_id: str, expires_at: datetime) -> None:
        self.revoked.add(token_id)

    async def is_revoked(self, token_id: str) -> bool:
        return token_id in self.revoked


@pytest.fixture
def test_client() -> Iterator[TestClient]:
    """Provide a FastAPI TestClient backed by fake in-memory services."""
    settings = get_settings()
    users = FakeUsers()
    service = AuthService(users, FakeRevocations(), settings)
    with TestClient(app) as client:
        app.state.limiter.enabled = False
        previous_service = app.state.auth_service
        app.state.auth_service = service
        app.dependency_overrides[get_auth_service] = lambda: service
        yield client
        app.dependency_overrides.clear()
        app.state.auth_service = previous_service


@pytest.fixture
def auth_headers(test_client: TestClient) -> dict[str, str]:
    """Register a test user and return Bearer auth headers for use in requests."""
    test_client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "testuser@example.com",
            "password": "StrongPassword123",
            "confirm_password": "StrongPassword123",
        },
    )
    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "StrongPassword123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
