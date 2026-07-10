"""Health endpoint tests (no live database required)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_exact_payload():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "quantcouncil-api",
        "version": "0.1.0",
    }


def test_health_db_returns_ok_or_unreachable():
    # 200 when Postgres is up, 503 when it is not; both are valid outcomes
    # for this test since it must pass without a live database.
    response = client.get("/health/db")
    assert response.status_code in (200, 503)
    assert "database" in response.json()
