from backend.tests.support.helpers import assert_error_envelope


def test_search_suggestions_contract(client):
    resp = client.get("/api/v1/search/suggestions", params={"q": "123", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "request_id" in data
    assert "query" in data
    assert "suggestions" in data


def test_search_resolve_contract(client):
    resp = client.get("/api/v1/search/resolve", params={"q": "123 Main"})
    assert resp.status_code == 200
    data = resp.json()
    assert "request_id" in data
    assert "status" in data
    assert "location" in data
    assert "candidates" in data


def test_estimate_contract(client):
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in ["request_id", "estimate_id", "status", "baseline_value", "final_estimate", "warnings", "missing_factors", "approximations"]:
        assert key in data


def test_layers_contract(client):
    resp = client.get(
        "/api/v1/layers/schools",
        params={"west": -113.7, "south": 53.39, "east": -113.27, "north": 53.71, "zoom": 12},
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in ["request_id", "layer_id", "status", "coverage_status", "features", "warnings"]:
        assert key in data


def test_health_contract(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "request_id" in data
    assert "status" in data
    assert "dependencies" in data


def test_metrics_contract(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    for key in ["request_id", "request_count", "error_count", "cache_hit_ratio", "routing_fallback_usage", "avg_latency_ms", "valuation_time_ms"]:
        assert key in data


def test_error_contract(client):
    resp = client.get("/api/v1/search/suggestions", params={"q": "ab"})
    assert resp.status_code == 400
    assert_error_envelope(resp.json())
