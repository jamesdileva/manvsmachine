"""Health check endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    """GET / returns {"status": "ok"} with a 200 status code."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
