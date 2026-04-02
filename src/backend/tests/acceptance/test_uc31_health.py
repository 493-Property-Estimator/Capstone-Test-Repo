def test_uc31_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"healthy", "degraded", "unhealthy"}
    assert isinstance(data["dependencies"], list)


def test_uc31_metrics(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "request_count" in data
    assert "error_count" in data
