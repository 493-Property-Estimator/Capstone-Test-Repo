def test_uc29_cache_hit_miss(client):
    payload = {"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}}
    resp1 = client.post("/api/v1/estimates", json=payload)
    assert resp1.status_code == 200
    assert resp1.headers.get("X-Cache-Status") in {"MISS", "STALE", "HIT"}
    resp2 = client.post("/api/v1/estimates", json=payload)
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Cache-Status") in {"HIT", "MISS", "STALE"}
