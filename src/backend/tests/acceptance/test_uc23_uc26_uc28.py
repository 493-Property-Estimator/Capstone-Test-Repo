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
    from src.backend.src.api import estimates as estimate_api

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
    from src.backend.src.api import estimates as estimate_api
    from src.backend.src.services.features import FactorResult

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


def test_confidence_percentage_and_completeness_mapping(client, monkeypatch):
    from src.backend.src.api import estimates as estimate_api

    def fake_estimate_property_value(*args, **kwargs):
        return {
            "request_id": "est-test",
            "query_point": {"lat": 53.5461, "lon": -113.4938},
            "matched_property": None,
            "baseline": {
                "canonical_location_id": "loc_001",
                "assessment_year": 2026,
                "assessment_value": 410000.0,
                "baseline_type": "nearest_neighbour_assessment",
                "source_table": "property_locations_prod",
                "distance_to_query_m": 5.0,
                "address": "123 Main St, Edmonton, AB",
                "neighbourhood": "Downtown",
                "matched_property": False,
            },
            "final_estimate": 400000.0,
            "low_estimate": 360000.0,
            "high_estimate": 440000.0,
            "confidence_score": 99.0,
            "confidence_label": "high",
            "completeness_score": 92.0,
            "warnings": [],
            "missing_factors": [],
            "fallback_flags": [],
            "feature_breakdown": {"amenities": {}, "commute_accessibility": {}, "valuation_adjustments": []},
            "top_positive_factors": [],
            "top_negative_factors": [],
            "comparables_matching": [],
            "comparables_non_matching": [],
            "neighbourhood_context": {},
        }

    monkeypatch.setattr(estimate_api, "estimate_property_value", fake_estimate_property_value)
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence"]["percentage"] == 99
    assert data["confidence"]["completeness"] == "partial"


def test_factor_breakdown_preserves_negative_values(client, monkeypatch):
    from src.backend.src.api import estimates as estimate_api

    def fake_estimate_property_value(*args, **kwargs):
        return {
            "request_id": "est-test",
            "query_point": {"lat": 53.5461, "lon": -113.4938},
            "matched_property": None,
            "baseline": {
                "canonical_location_id": "loc_001",
                "assessment_year": 2026,
                "assessment_value": 410000.0,
                "baseline_type": "nearest_neighbour_assessment",
                "source_table": "property_locations_prod",
                "distance_to_query_m": 5.0,
                "address": "123 Main St, Edmonton, AB",
                "neighbourhood": "Downtown",
                "matched_property": False,
            },
            "final_estimate": 390000.0,
            "low_estimate": 340000.0,
            "high_estimate": 430000.0,
            "confidence_score": 85.0,
            "confidence_label": "high",
            "completeness_score": 99.0,
            "warnings": [],
            "missing_factors": [],
            "fallback_flags": [],
            "feature_breakdown": {
                "amenities": {},
                "commute_accessibility": {},
                "valuation_adjustments": [
                    {
                        "code": "nearby_comparables",
                        "label": "Nearby assessments",
                        "value": -47000.0,
                        "metadata": {"median_assessment": 397000.0, "sample_size": 8},
                    }
                ],
            },
            "top_positive_factors": [],
            "top_negative_factors": [
                {
                    "code": "nearby_comparables",
                    "label": "Nearby assessments",
                    "value": -47000.0,
                    "metadata": {"median_assessment": 397000.0, "sample_size": 8},
                }
            ],
            "comparables_matching": [],
            "comparables_non_matching": [],
            "neighbourhood_context": {},
        }

    monkeypatch.setattr(estimate_api, "estimate_property_value", fake_estimate_property_value)
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 200
    data = resp.json()
    matching = [item for item in data["factor_breakdown"] if item["factor_id"] == "nearby_comparables"]
    assert len(matching) == 1
    assert matching[0]["value"] == -47000.0
