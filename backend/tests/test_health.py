from fastapi.testclient import TestClient

from app.main import app


def test_application_starts() -> None:
    with TestClient(app) as client:
        assert client.app.title == "Smart Form Auto-Filling System"


def test_health_reports_unavailable_dependencies_without_false_success(monkeypatch) -> None:
    monkeypatch.setenv("MONGODB_URL", "mongodb://127.0.0.1:1")
    monkeypatch.setenv("CHROMADB_URL", "http://127.0.0.1:1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    with TestClient(app) as client:
        response = client.get("/health")
    get_settings.cache_clear()
    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["data"]["services"]["mongodb"]["available"] is False
    assert body["data"]["services"]["chromadb"]["available"] is False

