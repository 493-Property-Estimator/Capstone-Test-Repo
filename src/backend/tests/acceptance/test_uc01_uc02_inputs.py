from backend.tests.support.helpers import assert_validation_errors


def test_uc01_invalid_address_format(client):
    resp = client.post("/api/v1/estimates", json={"location": {"address": "Main"}})
    assert resp.status_code in (400, 422)
    assert_validation_errors(resp.json())


def test_uc02_lat_out_of_range(client):
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 95, "lng": -113.4}}},
    )
    assert resp.status_code == 422
    assert_validation_errors(resp.json())


def test_uc02_lng_out_of_range(client):
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5, "lng": -190}}},
    )
    assert resp.status_code == 422
    assert_validation_errors(resp.json())
