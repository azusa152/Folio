"""Tests for GET /health endpoint."""


def test_health_check_should_return_ok(client):
    # Act
    resp = client.get("/health")

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "folio-backend"
