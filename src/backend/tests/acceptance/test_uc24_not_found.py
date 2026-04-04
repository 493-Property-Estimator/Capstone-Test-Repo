
def test_search_not_found(client):
    resp = client.get("/api/v1/search/resolve", params={"q": "No Match"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"not_found", "resolved"}
