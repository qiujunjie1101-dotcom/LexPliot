def test_live_health_returns_ok(client) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_live_health_sets_request_id(client) -> None:
    response = client.get("/health/live")
    assert response.headers["x-request-id"]


def test_ready_health_returns_ok(client) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
