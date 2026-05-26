from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_returns_service_info() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "app": "Text To Doc Builder",
        "status": "ok",
        "health_url": "/health",
        "docs_url": "/docs",
    }
