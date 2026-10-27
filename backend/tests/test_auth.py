"""Authentication and authorization (real MongoDB, throwaway database)."""

import time

import jwt
import pytest
from app.core.config import get_settings

from tests.conftest import Harness

pytestmark = pytest.mark.mongo

PASSWORD = "Str0ng-Passw0rd!"


def _register(harness: Harness, email: str, password: str = PASSWORD, confirm: str | None = None):
    return harness.client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Casey Sample",
            "email": email,
            "password": password,
            "confirm_password": confirm or password,
        },
    )


def test_register_login_me_logout(harness: Harness) -> None:
    email = f"casey_{time.time_ns()}@example.com"
    created = _register(harness, email)
    assert created.status_code == 201
    assert created.json()["data"]["email"] == email
    assert "password" not in created.text

    login = harness.client.post(
        "/api/v1/auth/login", json={"email": email.upper(), "password": PASSWORD}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    me = harness.client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["data"]["full_name"] == "Casey Sample"

    assert harness.client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert (
        harness.client.get("/api/v1/auth/me", headers=headers).status_code == 401
    )  # token revoked


def test_dashboard_cookie_session_requires_csrf_and_allowed_origin(harness: Harness) -> None:
    email = f"cookie_{time.time_ns()}@example.com"
    _register(harness, email)
    login = harness.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    session = login.cookies.get("smart_form_session")
    csrf = login.cookies.get("smart_form_csrf")
    assert session and csrf
    assert "httponly" in login.headers["set-cookie"].lower()
    assert harness.client.get("/api/v1/auth/me").status_code == 200

    assert harness.client.post("/api/v1/auth/logout").status_code == 403
    assert (
        harness.client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "https://attacker.example", "X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    logout = harness.client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:5173", "X-CSRF-Token": csrf},
    )
    assert logout.status_code == 200
    assert harness.client.get("/api/v1/auth/me").status_code == 401


def test_password_is_hashed_in_database(harness: Harness) -> None:
    email = f"hash_{time.time_ns()}@example.com"
    _register(harness, email)
    from pymongo import MongoClient

    settings = get_settings()
    client: MongoClient = MongoClient(settings.mongodb_url)
    stored = client[settings.mongodb_database]["users"].find_one({"email": email})
    client.close()
    assert stored["password_hash"].startswith("$2") and PASSWORD not in stored["password_hash"]


@pytest.mark.parametrize(
    ("password", "confirm"),
    [
        ("short1!", None),
        ("onlyletterspassword", None),
        ("Str0ng-Passw0rd!", "different-Passw0rd"),
        ("é" * 40 + "1", None),
    ],
)
def test_invalid_registrations_are_rejected(
    harness: Harness, password: str, confirm: str | None
) -> None:
    response = _register(harness, f"bad_{time.time_ns()}@example.com", password, confirm)
    assert response.status_code == 422
    assert password not in response.text  # submitted values are never echoed


def test_duplicate_email(harness: Harness) -> None:
    email = f"dup_{time.time_ns()}@example.com"
    assert _register(harness, email).status_code == 201
    response = _register(harness, email)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_wrong_password_and_unknown_user_give_the_same_error(harness: Harness) -> None:
    email = f"wrong_{time.time_ns()}@example.com"
    _register(harness, email)
    wrong = harness.client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Wrong-Passw0rd"}
    )
    unknown = harness.client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "Wrong-Passw0rd"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["code"] == unknown.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_missing_malformed_expired_and_wrong_type_tokens(harness: Harness) -> None:
    settings = get_settings()
    assert harness.client.get("/api/v1/profile").status_code == 401
    assert (
        harness.client.get("/api/v1/profile", headers={"Authorization": "Bearer nope"}).status_code
        == 401
    )
    now = int(time.time())
    expired = jwt.encode(
        {"sub": "x", "jti": "j", "iat": now - 7200, "exp": now - 3600, "typ": "access"},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    assert (
        harness.client.get(
            "/api/v1/profile", headers={"Authorization": f"Bearer {expired}"}
        ).status_code
        == 401
    )
    wrong_type = jwt.encode(
        {"sub": "x", "jti": "j", "iat": now, "exp": now + 3600, "typ": "refresh"},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    assert (
        harness.client.get(
            "/api/v1/profile", headers={"Authorization": f"Bearer {wrong_type}"}
        ).status_code
        == 401
    )
    forged = jwt.encode(
        {"sub": "x", "jti": "j", "iat": now, "exp": now + 3600, "typ": "access"},
        "other-secret" * 4,
        algorithm="HS256",
    )
    assert (
        harness.client.get(
            "/api/v1/profile", headers={"Authorization": f"Bearer {forged}"}
        ).status_code
        == 401
    )


def test_token_in_query_string_is_not_accepted(harness: Harness) -> None:
    headers = harness.register()
    token = headers["Authorization"].split()[1]
    assert harness.client.get(f"/api/v1/profile?token={token}").status_code == 401


def test_login_rate_limit(harness: Harness) -> None:
    email = f"limit_{time.time_ns()}@example.com"
    _register(harness, email)
    codes = [
        harness.client.post(
            "/api/v1/auth/login", json={"email": email, "password": "Wrong-Passw0rd"}
        ).status_code
        for _ in range(get_settings().auth_login_rate_limit_attempts + 1)
    ]
    assert codes[-1] == 429


def test_delete_account_removes_user_and_revokes_token(harness: Harness) -> None:
    headers = harness.register()
    response = harness.client.delete("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert harness.client.get("/api/v1/auth/me", headers=headers).status_code == 401
