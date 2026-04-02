def test_search_resolve_estimate_flow(client):
    search = client.get("/api/v1/search/suggestions", params={"q": "123", "limit": 5})
    assert search.status_code == 200
    resolve = client.get("/api/v1/search/resolve", params={"q": "123 Main"})
    assert resolve.status_code == 200
    estimate = client.post(
        "/api/v1/estimates",
        json={"location": {"address": "123 Main"}},
    )
    assert estimate.status_code in (200, 422, 424)


def test_layers_then_estimate(client):
    layer = client.get(
        "/api/v1/layers/schools",
        params={"west": -113.7, "south": 53.39, "east": -113.27, "north": 53.71, "zoom": 12},
    )
    assert layer.status_code == 200
    estimate = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert estimate.status_code == 200
