"""Authentication tests covering TEST_PLAN TC-AUTH-01 through TC-AUTH-08."""

from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pytest
from app.api.v1.auth import get_auth_service
from app.core.config import get_settings
from app.main import app
from app.services.auth import AuthService
from fastapi.testclient import TestClient


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
def auth_client() -> Iterator[tuple[TestClient, FakeUsers]]:
    settings = get_settings()
    users = FakeUsers()
    service = AuthService(users, FakeRevocations(), settings)
    with TestClient(app) as client:
        previous_service = app.state.auth_service
        app.state.auth_service = service
        app.dependency_overrides[get_auth_service] = lambda: service
        yield client, users
        app.dependency_overrides.clear()
        app.state.auth_service = previous_service


def test_tc_auth_01_register_valid_details(auth_client: tuple[TestClient, FakeUsers]) -> None:
    client, users = auth_client
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Sanket Mali",
            "email": "user@example.com",
            "password": "StrongPassword123",
            "confirm_password": "StrongPassword123",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"] == {
        "user_id": "user-1",
        "full_name": "Sanket Mali",
        "email": "user@example.com",
    }
    assert users.users["user-1"]["password_hash"] != "StrongPassword123"


def test_tc_auth_02_duplicate_email(auth_client: tuple[TestClient, FakeUsers]) -> None:
    client, _ = auth_client
    payload = {
        "full_name": "Sanket Mali",
        "email": "user@example.com",
        "password": "StrongPassword123",
        "confirm_password": "StrongPassword123",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_tc_auth_03_invalid_registration_input(auth_client: tuple[TestClient, FakeUsers]) -> None:
    client, _ = auth_client
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "",
            "email": "not-an-email",
            "password": "short",
            "confirm_password": "different",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_tc_auth_04_valid_login(auth_client: tuple[TestClient, FakeUsers]) -> None:
    client, _ = auth_client
    register_payload = {
        "full_name": "Sanket Mali",
        "email": "user@example.com",
        "password": "StrongPassword123",
        "confirm_password": "StrongPassword123",
    }
    client.post("/api/v1/auth/register", json=register_payload)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["token_type"] == "bearer"
    assert response.json()["data"]["access_token"]


def test_tc_auth_05_invalid_login_is_ambiguous(auth_client: tuple[TestClient, FakeUsers]) -> None:
    client, _ = auth_client
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Registered User",
            "email": "user@example.com",
            "password": "StrongPassword123",
            "confirm_password": "StrongPassword123",
        },
    )
    response_unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "wrong-password"},
    )
    response_wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )
    assert response_unknown.status_code == response_wrong_password.status_code == 401
    assert response_unknown.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert (
        response_unknown.json()["error"]["message"]
        == response_wrong_password.json()["error"]["message"]
    )


def test_tc_auth_06_missing_token_is_rejected(auth_client: tuple[TestClient, FakeUsers]) -> None:
    client, _ = auth_client
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_tc_auth_07_logout_invalidates_token(auth_client: tuple[TestClient, FakeUsers]) -> None:
    client, _ = auth_client
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Sanket Mali",
            "email": "user@example.com",
            "password": "StrongPassword123",
            "confirm_password": "StrongPassword123",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "StrongPassword123"},
    ).json()["data"]["access_token"]
    response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Logout successful"}
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )


def test_tc_auth_08_current_user_cannot_be_selected_by_client(
    auth_client: tuple[TestClient, FakeUsers],
) -> None:
    client, _ = auth_client
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "User A",
            "email": "a@example.com",
            "password": "StrongPassword123",
            "confirm_password": "StrongPassword123",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "StrongPassword123"},
    ).json()["data"]["access_token"]
    response = client.get(
        "/api/v1/auth/me?user_id=user-2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["user_id"] == "user-1"


def test_login_rate_limit(auth_client: tuple[TestClient, FakeUsers]) -> None:
    client, _ = auth_client
    app.state.limiter.enabled = True
    try:
        for _ in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "unknown@example.com", "password": "wrong-password"},
            )
            if response.status_code == 429:
                break
            assert response.status_code == 401
        
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "unknown@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
    finally:
        app.state.limiter.enabled = False
