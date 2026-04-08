import json
import sqlite3

import pytest

from src.backend.src.api import estimates as estimates_api
from src.backend.src.api import search as search_api


def test_search_suggestions_provider_and_osrm(client):
    resp = client.get("/api/v1/search/suggestions", params={"q": "a"})
    assert resp.status_code == 400
    resp = client.get("/api/v1/search/suggestions", params={"q": "123", "provider": "invalid"})
    assert resp.status_code == 200
    assert resp.json()["provider_requested"] == "db"

    resp = client.get("/api/v1/search/suggestions", params={"q": "123", "provider": "osrm"})
    assert resp.status_code == 200
    assert resp.json()["provider_effective"] == "db_fallback"


def test_search_resolve_statuses(client, test_db_path):
    resp = client.get("/api/v1/search/resolve", params={"q": "a"})
    assert resp.status_code == 400
    resp = client.get("/api/v1/search/resolve", params={"q": "zzz"})
    assert resp.json()["status"] == "not_found"

    resp = client.get("/api/v1/search/resolve", params={"q": "123", "provider": "invalid"})
    assert resp.status_code == 200
    resp = client.get("/api/v1/search/resolve", params={"q": "123", "provider": "osrm"})
    assert resp.status_code == 200

    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "INSERT INTO property_locations_prod (canonical_location_id, assessment_year, assessment_value, suite, house_number, street_name, neighbourhood_id, neighbourhood, ward, zoning, lot_size, total_gross_area, year_built, tax_class, garage, assessment_class_1, assessment_class_2, assessment_class_3, point_location, lat, lon) VALUES ('loc_002', 2026, 410000, NULL, '123', 'Main St', 'N1090', 'Downtown', 'Ward 1', 'DC1', 300.0, 175.0, 2005, 'Residential', 'Y', 'Residential', NULL, NULL, NULL, 0.0, 0.0)"
    )
    conn.commit()
    conn.close()

    resp = client.get("/api/v1/search/resolve", params={"q": "123"})
    assert resp.json()["status"] == "ambiguous"

    record = type("Rec", (), {"house_number": None, "street_name": "Main"})
    assert search_api._format_address(record) == "Main"
    assert search_api._in_bounds(None, None) is False


def test_layers_disabled_and_invalid_bbox(client):
    resp = client.get("/api/v1/layers/not_enabled", params={"west": -114, "south": 53, "east": -113, "north": 54, "zoom": 10})
    assert resp.status_code == 404

    resp = client.get("/api/v1/layers/schools", params={"west": -113, "south": 54, "east": -114, "north": 53, "zoom": 10})
    assert resp.status_code == 400


def test_locations_resolve_click_branches(client, monkeypatch):
    resp = client.post("/api/v1/locations/resolve-click", json={"click_id": "c1", "coordinates": {}})
    assert resp.json()["status"] == "resolution_error"

    resp = client.post(
        "/api/v1/locations/resolve-click",
        json={"click_id": "c2", "coordinates": {"lat": 0, "lng": 0}},
    )
    assert resp.json()["status"] == "outside_supported_area"

    from src.backend.src.api import locations as locations_api
    monkeypatch.setattr(locations_api.proximity, "get_top_closest_properties", lambda *_a, **_k: [])
    resp = client.post(
        "/api/v1/locations/resolve-click",
        json={"click_id": "c3", "coordinates": {"lat": 53.5461, "lng": -113.4938}},
    )
    assert resp.json()["status"] == "resolution_error"
    record = type("Rec", (), {"house_number": None, "street_name": "Main"})
    assert locations_api._format_address(record) == "Main"
    assert locations_api._format_address(None) is None


def test_properties_cache_and_detail(client, test_db_path):
    from dataclasses import replace
    settings = client.app.state.settings
    client.app.state.settings = replace(
        settings,
        enabled_layers=tuple(set(settings.enabled_layers) | {"assessment_properties"}),
    )
    resp1 = client.get(
        "/api/v1/properties",
        params={"west": -114, "south": 53, "east": -113, "north": 54, "zoom": 10},
    )
    assert resp1.status_code == 200

    resp2 = client.get(
        "/api/v1/properties",
        params={"west": -114, "south": 53, "east": -113, "north": 54, "zoom": 10},
    )
    assert resp2.status_code == 200

    resp = client.get("/api/v1/properties/missing")
    assert resp.status_code == 404

    resp = client.get("/api/v1/properties/loc_001")
    assert resp.status_code == 200

    from src.backend.src.api import properties as properties_api
    assert properties_api._parse_cursor("bad") == 0
    assert properties_api._parse_cursor("offset:bad") == 0


def test_properties_detail_disabled_layer(client):
    resp = client.get("/api/v1/properties/loc_001")
    assert resp.status_code == 404


def test_estimate_helper_functions():
    assert estimates_api._derive_affected_factors(None) == []
    assert estimates_api._derive_affected_factors("park_warning") == ["park_access"]
    assert estimates_api._derive_affected_factors("playground_warning") == ["playground_access"]
    assert estimates_api._derive_affected_factors("school_warning") == ["school_access"]
    assert estimates_api._derive_affected_factors("library_warning") == ["library_access"]
    assert estimates_api._derive_affected_factors("crime_warning") == ["crime_statistics"]

    factor = estimates_api._adapt_factor({"code": "x", "label": "X", "value": 1, "metadata": {}})
    assert "Derived" in factor["summary"]

    centroid = estimates_api._polygon_centroid({"coordinates": [[]]})
    assert centroid is None
    assert estimates_api._polygon_centroid({"coordinates": ["bad"]}) is None
    centroid = estimates_api._polygon_centroid(
        {"coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    )
    assert centroid == {"lat": 0.5, "lng": 0.5}
    centroid = estimates_api._polygon_centroid({"coordinates": [[[0, 0], [0, 0]]]})
    assert centroid == {"lat": 0.0, "lng": 0.0}
    centroid = estimates_api._polygon_centroid({"coordinates": [[[0, 0]]]})
    assert centroid == {"lat": 0.0, "lng": 0.0}

    normalized, usage = estimates_api._normalize_property_details({"bedrooms": "x", "bathrooms": "2"})
    assert "bedrooms" in usage["rejected_fields"]
    normalized, usage = estimates_api._normalize_property_details({"bathrooms": "2"})
    assert usage["mode"] == "full"
    normalized, usage = estimates_api._normalize_property_details({"bathrooms": None})
    assert usage["provided_count"] == 0

    factors = estimates_api._adapt_factors(
        {"feature_breakdown": {"valuation_adjustments": [{"code": "schools", "label": "Schools", "value": 1}]}},
        ["schools", "parks"],
    )
    assert any(item["factor_id"] == "schools" for item in factors)
    assert any(item["factor_id"] == "parks" and item["status"] == "missing" for item in factors)

    record = type("Rec", (), {"house_number": "123", "street_name": "Main"})
    assert estimates_api._format_address(record) == "123 Main, Edmonton, AB"
    record = type("Rec", (), {"house_number": None, "street_name": "Main"})
    assert estimates_api._format_address(record) == "Main"
    assert estimates_api._format_address(None) is None
    assert estimates_api._in_bounds(None, None) is False


def test_estimates_unavailable_and_strict_mode(client, monkeypatch, test_db_path):
    resp = client.post("/api/v1/estimates", json={"location": {"canonical_location_id": "missing"}})
    assert resp.status_code == 424

    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "INSERT INTO property_locations_prod (canonical_location_id, assessment_year, assessment_value, suite, house_number, street_name, neighbourhood_id, neighbourhood, ward, zoning, lot_size, total_gross_area, year_built, tax_class, garage, assessment_class_1, assessment_class_2, assessment_class_3, point_location, lat, lon) VALUES ('loc_003', 2026, 410000, NULL, '123', 'Main St', 'N1090', 'Downtown', 'Ward 1', 'DC1', 300.0, 175.0, 2005, 'Residential', 'Y', 'Residential', NULL, NULL, NULL, 53.5461, -113.4938)"
    )
    conn.commit()
    conn.close()

    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"address": "123 Main St"}},
    )
    assert resp.status_code == 422

    monkeypatch.setattr(estimates_api, "compute_proximity_factors", lambda *_a, **_k: ([], ["schools"]))
    resp = client.post(
        "/api/v1/estimates",
        json={
            "location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}},
            "options": {"strict": True, "required_factors": ["schools"]},
        },
    )
    assert resp.status_code == 424

    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"address": "9999 Unknown St"}},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 0, "lng": 0}}},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"property_id": "loc_001"}},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/estimates",
        json={
            "location": {
                "polygon": {"coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]}
            }
        },
    )
    assert resp.status_code in (400, 422)


def test_estimates_polygon_centroid_and_strict_pass(client, monkeypatch):
    monkeypatch.setattr(estimates_api, "compute_proximity_factors", lambda *_a, **_k: ([], ["parks"]))
    monkeypatch.setattr(estimates_api, "estimate_property_value", lambda *_a, **_k: {"final_estimate": 1})
    class _Record:
        canonical_location_id = "loc_001"
        house_number = "123"
        street_name = "Main St"

    monkeypatch.setattr(estimates_api, "resolve_coordinates_to_location", lambda *_a, **_k: _Record())

    payload = {
        "location": {
            "polygon": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-113.4940, 53.5460],
                        [-113.4936, 53.5460],
                        [-113.4936, 53.5463],
                        [-113.4940, 53.5463],
                        [-113.4940, 53.5460],
                    ]
                ]
            }
        },
        "options": {"strict": True, "required_factors": ["schools"]},
    }
    resp = client.post("/api/v1/estimates", json=payload)
    assert resp.status_code in (200, 424)


def test_estimates_timeout_and_cached(client, monkeypatch):
    cached = {
        "request_id": "x",
        "status": "ok",
    }
    monkeypatch.setattr(client.app.state.cache, "get", lambda *_a, **_k: (cached, "hit"))
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 200
    assert resp.headers.get("X-Cache-Status") == "HIT"

    monkeypatch.setattr(client.app.state.cache, "get", lambda *_a, **_k: (None, "miss"))

    async def _dummy_to_thread(*_a, **_k):
        return {}

    async def _raise_timeout(coro, timeout=None):
        await coro
        raise TimeoutError

    monkeypatch.setattr(estimates_api.asyncio, "to_thread", _dummy_to_thread)
    monkeypatch.setattr(estimates_api.asyncio, "wait_for", _raise_timeout)
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 503


def test_estimates_cache_exception_and_value_error(client, monkeypatch):
    def _raise_cache(*_a, **_k):
        raise RuntimeError("cache error")

    monkeypatch.setattr(client.app.state.cache, "get", _raise_cache)

    def _raise_value(*_a, **_k):
        raise ValueError("boom")

    monkeypatch.setattr(estimates_api.asyncio, "to_thread", _raise_value)
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 424


def test_estimates_cache_set_exception(client, monkeypatch):
    def _raise_set(*_a, **_k):
        raise RuntimeError("cache set")

    monkeypatch.setattr(client.app.state.cache, "set", _raise_set)
    resp = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert resp.status_code == 200
