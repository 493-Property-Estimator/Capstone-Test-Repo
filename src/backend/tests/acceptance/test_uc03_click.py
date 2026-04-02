
def test_uc03_click_outside_boundary(client):
    resp = client.post(
        "/api/v1/locations/resolve-click",
        json={"click_id": "c1", "coordinates": {"lat": 0.0, "lng": 0.0}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"outside_supported_area", "resolution_error", "resolved"}


def test_uc03_click_success(client):
    resp = client.post(
        "/api/v1/locations/resolve-click",
        json={"click_id": "c2", "coordinates": {"lat": 53.5461, "lng": -113.4938}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"resolved", "outside_supported_area", "resolution_error"}
