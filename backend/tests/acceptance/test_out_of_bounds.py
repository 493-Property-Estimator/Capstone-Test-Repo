from backend.tests.support.helpers import assert_error_envelope


def test_coords_out_of_bounds_returns_422(client):
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 0.0, "lng": 0.0}}},
    )
    assert resp.status_code == 422
    assert_error_envelope(resp.json())
