from backend.tests.support.helpers import assert_validation_errors


def test_uc32_multi_error(client):
    resp = client.post("/api/v1/estimates", json={})
    assert resp.status_code in (400, 422)
    assert_validation_errors(resp.json())


def test_uc32_invalid_coords(client):
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 91.5, "lng": -200.0}}},
    )
    assert resp.status_code == 422
    assert_validation_errors(resp.json())
