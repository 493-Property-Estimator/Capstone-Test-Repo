from backend.tests.support.helpers import assert_error_envelope


def test_unresolvable_address_returns_422(client):
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"address": "No Such Address 000"}},
    )
    assert resp.status_code in (422, 424)
    assert_error_envelope(resp.json())
