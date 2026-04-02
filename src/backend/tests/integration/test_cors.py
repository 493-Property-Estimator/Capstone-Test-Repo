def test_cors_preflight_allows_localhost_frontend(client):
    resp = client.options(
        "/api/v1/estimates",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:8080"


def test_cors_preflight_allows_loopback_frontend(client):
    resp = client.options(
        "/api/v1/search/suggestions?q=123&limit=5",
        headers={
            "Origin": "http://127.0.0.1:8080",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:8080"
