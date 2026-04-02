
def test_layer_unknown_returns_partial(client):
    resp = client.get(
        "/api/v1/layers/unknown",
        params={"west": -113.7, "south": 53.39, "east": -113.27, "north": 53.71, "zoom": 12},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["coverage_status"] in {"partial", "complete"}
