
def test_click_missing_coords(client):
    resp = client.post(
        "/api/v1/locations/resolve-click",
        json={"click_id": "c3"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolution_error"
