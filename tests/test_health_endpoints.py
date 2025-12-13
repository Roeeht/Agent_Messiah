from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_health_ready():
    resp = client.get("/health/ready")
    # health/ready returns (checks, status_code)
    assert resp.status_code == 200
    data = resp.json()

    # Some implementations return the tuple directly, which FastAPI serializes as a 2-item list.
    checks = data[0] if isinstance(data, list) and data else data
    assert "database" in checks
    assert "ready" in checks
    assert checks["database"] is True
    assert checks["ready"] is True


def test_health_info():
    resp = client.get("/health/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "agent-messiah"
    assert "configuration" in data
    assert "features" in data


def test_metrics_endpoint():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    # Should include at least one metric name from app.main
    assert "api_requests_total" in resp.text
