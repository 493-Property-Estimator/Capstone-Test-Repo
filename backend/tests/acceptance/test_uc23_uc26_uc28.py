from backend.tests.support.helpers import assert_error_envelope


def test_uc23_estimate_success(client):
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["baseline_value"] > 0
    assert data["range"]["low"] <= data["final_estimate"] <= data["range"]["high"]


def test_uc26_warning_arrays_present(client):
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["warnings"], list)
    assert isinstance(data["missing_factors"], list)
    assert isinstance(data["approximations"], list)


def test_uc28_baseline_missing_returns_424(client, monkeypatch):
    from backend.src.api import estimates as estimate_api

    def no_baseline(*args, **kwargs):
        return None

    monkeypatch.setattr(estimate_api, "get_location_by_id", lambda *args, **kwargs: None)
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"canonical_location_id": "loc_missing"}},
    )
    assert resp.status_code == 424
    assert_error_envelope(resp.json())


def test_uc28_strict_mode_missing_factor(client, monkeypatch):
    from backend.src.api import estimates as estimate_api
    from backend.src.services.features import FactorResult

    def fake_compute(point, db_path):
        return [
            FactorResult("school_distance", "Distance to schools", 0.0, "missing", "Missing"),
        ], ["crime_statistics"]

    monkeypatch.setattr(estimate_api, "compute_proximity_factors", fake_compute)
    resp = client.post(
        "/api/v1/estimates",
        json={
            "location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}},
            "options": {"strict": True, "required_factors": ["crime_statistics"]},
        },
    )
    assert resp.status_code == 424
    data = resp.json()
    assert data["error"]["code"] == "REQUIRED_FACTOR_MISSING"
