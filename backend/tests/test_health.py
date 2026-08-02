from fastapi.testclient import TestClient


def test_root_returns_metadata(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "name": "Project Elysia API",
        "version": "0.1.0",
        "status": "running",
    }


def test_health_uses_database(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
    assert response.json()["environment"] == "test"


def test_system_info_is_safe(client: TestClient) -> None:
    payload = client.get("/api/system/info").json()
    rendered = str(payload).lower()
    assert payload["ai_integration"] == "not_configured"
    assert payload["local_first"] is True
    assert "database_url" not in rendered
    assert "elysia.db" not in rendered
    assert "secret" not in rendered
