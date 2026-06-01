from fastapi.testclient import TestClient

from app.main import create_app


def test_test_ui_returns_minimal_document_form() -> None:
    client = TestClient(create_app())

    response = client.get("/ui")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Text To Doc Builder" in response.text
    assert 'id="prompt"' in response.text
    assert 'id="overrides"' in response.text
    assert 'fetch("/documents"' in response.text
    assert "maybeStartPolling" in response.text
