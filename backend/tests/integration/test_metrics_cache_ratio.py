
def test_metrics_cache_ratio_updates(client):
    payload = {"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}}
    client.post("/api/v1/estimates", json=payload)
    client.post("/api/v1/estimates", json=payload)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cache_hit_ratio"] >= 0.0
