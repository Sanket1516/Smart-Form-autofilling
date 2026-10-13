import pytest

from tests.conftest import Harness

pytestmark = pytest.mark.mongo


def test_health_uses_success_envelope_and_request_id(harness: Harness) -> None:
    response = harness.client.get("/api/v1/health", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    body = response.json()
    assert body["success"] is True and body["data"]["database"] == "healthy"


def test_unsafe_request_id_is_replaced(harness: Harness) -> None:
    response = harness.client.get(
        "/api/v1/health", headers={"X-Request-ID": "bad id\nwith newline"}
    )
    assert response.headers["X-Request-ID"] != "bad id\nwith newline"


def test_service_health_reports_real_component_state(harness: Harness) -> None:
    body = harness.client.get("/api/v1/health/services").json()["data"]
    assert body["mongodb"] == "healthy"
    assert body["chromadb"] == "healthy"
    assert body["llm"] == "mock"
    harness.vectors.down = True
    body = harness.client.get("/api/v1/health/services").json()["data"]
    assert body["chromadb"] == "unhealthy"


def test_not_found_uses_error_envelope(harness: Harness) -> None:
    response = harness.client.get("/api/v1/missing", headers={"X-Request-ID": "error-request"})
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["details"]["request_id"] == "error-request"


def test_cors_allows_dashboard_and_patch_but_not_other_origins(harness: Harness) -> None:
    allowed = harness.client.options(
        "/api/v1/profile/facts/conflicts/x/resolve",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "PATCH"},
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = harness.client.options(
        "/api/v1/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in denied.headers
