from app.main import app
from fastapi.testclient import TestClient


def test_application_starts() -> None:
    with TestClient(app) as client:
        assert client.app.title == "Smart Form Auto-Filling System"


def test_health_reports_unavailable_dependencies_without_false_success(monkeypatch) -> None:
    monkeypatch.setenv("MONGODB_URL", "mongodb://127.0.0.1:1")
    monkeypatch.setenv("CHROMADB_URL", "http://127.0.0.1:1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/api/v1/health/services")
    get_settings.cache_clear()
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["mongodb"] == "unhealthy"
    assert body["data"]["chromadb"] == "unhealthy"
    assert body["data"]["llm"] == "not_configured"


def test_health_uses_success_envelope_and_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.json() == {
        "success": True,
        "data": {"status": "healthy", "application_version": "0.1.0"},
        "message": "API is healthy",
    }


def test_not_found_uses_error_envelope() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/missing", headers={"X-Request-ID": "error-request"})
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "HTTP_404"
    assert body["error"]["details"]["request_id"] == "error-request"


def test_cors_allows_frontend_and_extension_origins() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
