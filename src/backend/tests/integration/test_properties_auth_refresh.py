from __future__ import annotations

import sqlite3
from dataclasses import replace

from src.backend.src.api import estimates as estimates_api
from src.backend.src.api import properties as properties_api
from src.backend.src.services import property_viewport as viewport


def _enable_assessment_properties(client):
    settings = client.app.state.settings
    enabled = tuple(set(settings.enabled_layers) | {"assessment_properties"})
    client.app.state.settings = replace(settings, enabled_layers=enabled)


def _auth_enabled(client, token: str = "token-123"):
    settings = client.app.state.settings
    client.app.state.settings = replace(
        settings,
        estimate_auth_required=True,
        estimate_api_token=token,
    )


def _mock_estimate_result():
    return {
        "request_id": "est-id",
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
        "confidence_score": 80.0,
        "confidence_label": "high",
        "completeness_score": 99.0,
        "warnings": [],
        "missing_factors": [],
        "fallback_flags": [],
        "feature_breakdown": {"amenities": {}, "downtown_accessibility": {}, "valuation_adjustments": []},
        "top_positive_factors": [],
        "top_negative_factors": [],
        "comparables_matching": [],
        "comparables_non_matching": [],
        "neighbourhood_context": {},
    }


def test_properties_disabled_layer_returns_404(client):
    response = client.get(
        "/api/v1/properties",
        params={"west": -114, "south": 53.3, "east": -113.2, "north": 53.8, "zoom": 17},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "LAYER_DISABLED"


def test_properties_invalid_bbox_returns_400(client):
    _enable_assessment_properties(client)
    response = client.get(
        "/api/v1/properties",
        params={"west": -113.2, "south": 53.8, "east": -114, "north": 53.3, "zoom": 17},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_BBOX"


def test_properties_cluster_mode_uses_optimized_viewport(client, monkeypatch):
    _enable_assessment_properties(client)

    monkeypatch.setattr(
        properties_api,
        "fetch_property_viewport",
        lambda *_args, **_kwargs: {
            "status": "ok",
            "coverage_status": "complete",
            "viewport": {},
            "render_mode": "cluster",
            "legend": {"title": "Assessment Properties", "items": []},
            "clusters": [{"cluster_id": "c-1"}],
            "properties": [],
            "page": {"has_more": False, "next_cursor": None},
            "warnings": [],
        },
    )

    response = client.get(
        "/api/v1/properties",
        params={"west": -114, "south": 53.3, "east": -113.2, "north": 53.8, "zoom": 12},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["render_mode"] == "cluster"
    assert payload["request_id"]
    assert payload["clusters"][0]["cluster_id"] == "c-1"


def test_properties_property_mode_formats_response_and_pagination(client, monkeypatch):
    _enable_assessment_properties(client)
    client.app.state.settings = replace(
        client.app.state.settings,
        properties_limit_min=1,
        properties_limit_max=2,
    )

    rows = [
        {
            "canonical_location_id": "loc_001",
            "house_number": "123",
            "street_name": "Main St",
            "lat": 53.5461,
            "lon": -113.4938,
            "assessment_value": 410000.0,
            "neighbourhood": "Downtown",
            "ward": "Ward 1",
            "tax_class": "Residential",
            "suite": None,
            "assessment_year": 2026,
            "legal_description": None,
            "zoning": "DC1",
            "lot_size": 300.0,
            "total_gross_area": 175.0,
            "year_built": 2005,
            "garage": "Y",
            "assessment_class_1": "Residential",
            "assessment_class_2": None,
            "assessment_class_3": None,
            "assessment_class_pct_1": None,
            "assessment_class_pct_2": None,
            "assessment_class_pct_3": None,
            "bedrooms": 3,
            "bathrooms": 2,
            "bedrooms_estimated": None,
            "bathrooms_estimated": None,
            "attribute_source_type": None,
            "attribute_source_name": None,
            "attribute_confidence": None,
            "location_confidence": None,
            "point_location": None,
            "source_ids_json": None,
            "record_ids_json": None,
            "link_method": None,
        },
        {
            "canonical_location_id": "loc_002",
            "house_number": "",
            "street_name": "",
            "lat": 53.5462,
            "lon": -113.4939,
            "assessment_value": None,
            "neighbourhood": None,
            "ward": None,
            "tax_class": None,
            "suite": None,
            "assessment_year": None,
            "legal_description": None,
            "zoning": None,
            "lot_size": None,
            "total_gross_area": None,
            "year_built": None,
            "garage": None,
            "assessment_class_1": None,
            "assessment_class_2": None,
            "assessment_class_3": None,
            "assessment_class_pct_1": None,
            "assessment_class_pct_2": None,
            "assessment_class_pct_3": None,
            "bedrooms": None,
            "bathrooms": None,
            "bedrooms_estimated": None,
            "bathrooms_estimated": None,
            "attribute_source_type": None,
            "attribute_source_name": None,
            "attribute_confidence": None,
            "location_confidence": None,
            "point_location": None,
            "source_ids_json": None,
            "record_ids_json": None,
            "link_method": None,
        },
    ]
    monkeypatch.setattr(properties_api, "fetch_property_locations_bbox", lambda *_args, **_kwargs: rows)

    response = client.get(
        "/api/v1/properties",
        params={"west": -114, "south": 53.3, "east": -113.2, "north": 53.8, "zoom": 18, "limit": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["render_mode"] == "property"
    assert payload["status"] == "partial"
    assert payload["page"]["has_more"] is True
    assert payload["page"]["next_cursor"] == "offset:1"
    assert payload["properties"][0]["canonical_address"] == "123 Main St, Edmonton, AB"
    assert "Assessment:" in payload["properties"][0]["description"]


def test_properties_helpers_cover_cursor_cluster_and_detail_functions():
    assert properties_api._parse_cursor(None) == 0
    assert properties_api._parse_cursor("bad") == 0
    assert properties_api._parse_cursor("offset:-10") == 0
    assert properties_api._parse_cursor("offset:7") == 7

    row = {"assessment_value": 123456.7, "neighbourhood": "N", "ward": "W", "tax_class": "T"}
    assert "Assessment: $123,457" in properties_api._format_property_description(row)
    assert properties_api._property_details({"assessment_year": 2026})["assessment_year"] == 2026

    clusters = properties_api._cluster_properties(
        [
            {
                "canonical_location_id": "loc-1",
                "canonical_address": "A",
                "assessment_value": 1,
                "coordinates": {"lat": 53.5, "lng": -113.4},
            }
        ],
        zoom=11.5,
    )
    assert len(clusters) == 1
    assert clusters[0]["count"] == 1


def test_refresh_status_handles_missing_table(client):
    response = client.get("/api/v1/jobs/refresh-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["recent_runs"] == []
    assert payload["request_id"]


def test_refresh_status_returns_recent_runs_when_table_exists(client, test_db_path):
    client.app.state.refresh_scheduler_active = True
    client.app.state.last_refresh_run = {"status": "ok"}
    with sqlite3.connect(test_db_path) as conn:
        conn.execute(
            """
            CREATE TABLE workflow_runs (
                run_id TEXT,
                trigger_type TEXT,
                status TEXT,
                started_at TEXT,
                completed_at TEXT,
                correlation_id TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO workflow_runs (run_id, trigger_type, status, started_at, completed_at, correlation_id)
            VALUES ('run-1', 'on_demand', 'succeeded', '2026-01-01T00:00:00Z', '2026-01-01T00:10:00Z', 'corr-1')
            """
        )
        conn.commit()

    response = client.get("/api/v1/jobs/refresh-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduler_active"] is True
    assert payload["last_refresh_run"]["status"] == "ok"
    assert payload["recent_runs"][0]["run_id"] == "run-1"


def test_estimate_auth_requires_credentials(client, monkeypatch):
    _auth_enabled(client)
    monkeypatch.setattr(estimates_api, "estimate_property_value", lambda *_a, **_k: _mock_estimate_result())

    response = client.post(
        "/api/v1/estimates",
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert response.status_code == 401


def test_estimate_auth_rejects_invalid_credentials(client, monkeypatch):
    _auth_enabled(client)
    monkeypatch.setattr(estimates_api, "estimate_property_value", lambda *_a, **_k: _mock_estimate_result())

    response = client.post(
        "/api/v1/estimates",
        headers={"X-API-Key": "wrong"},
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert response.status_code == 403


def test_estimate_auth_accepts_bearer_and_api_key(client, monkeypatch):
    _auth_enabled(client)
    monkeypatch.setattr(estimates_api, "estimate_property_value", lambda *_a, **_k: _mock_estimate_result())

    bearer_response = client.post(
        "/api/v1/estimates",
        headers={"Authorization": "Bearer token-123"},
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert bearer_response.status_code == 200

    key_response = client.post(
        "/api/v1/estimates",
        headers={"X-API-Key": "token-123"},
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert key_response.status_code == 200


def test_estimate_auth_returns_503_when_token_missing(client, monkeypatch):
    _auth_enabled(client, token="")
    monkeypatch.setattr(estimates_api, "estimate_property_value", lambda *_a, **_k: _mock_estimate_result())
    response = client.post(
        "/api/v1/estimates",
        headers={"Authorization": "Bearer any"},
        json={"location": {"coordinates": {"lat": 53.5461, "lng": -113.4938}}},
    )
    assert response.status_code == 503


def test_property_viewport_helpers_and_modes(test_db_path):
    viewport._INDEXES_READY = False
    viewport.ensure_property_indexes(test_db_path)
    viewport.ensure_property_indexes(test_db_path)

    assert viewport._cluster_bucket_size(11) == 0.03
    assert viewport._cluster_bucket_size(12) == 0.024
    assert viewport._cluster_bucket_size(13) == 0.018
    assert viewport._cluster_bucket_size(14) == 0.012
    assert viewport._cluster_bucket_size(15) == 0.008
    assert viewport._cluster_bucket_size(16) == 0.005
    assert viewport._cluster_bucket_size(18) == 0.003
    assert viewport._parse_cursor(None) == 0
    assert viewport._parse_cursor("offset:2") == 2
    assert viewport._parse_cursor("offset:bad") == 0
    assert viewport._format_address_from_values(None, None) == "Edmonton property"
    assert viewport._format_address_from_values("123", "Main St") == "123 Main St, Edmonton, AB"

    cluster_payload = viewport.fetch_property_viewport(
        test_db_path,
        west=-114,
        south=53.3,
        east=-113.2,
        north=53.8,
        zoom=10,
        limit=5,
    )
    assert cluster_payload["render_mode"] == "cluster"
    assert "clusters" in cluster_payload

    with sqlite3.connect(test_db_path) as conn:
        conn.execute(
            """
            INSERT INTO property_locations_prod (
                canonical_location_id, assessment_year, assessment_value, suite, house_number, street_name,
                neighbourhood_id, neighbourhood, ward, zoning, lot_size, total_gross_area,
                year_built, tax_class, garage, assessment_class_1, assessment_class_2, assessment_class_3,
                point_location, lat, lon
            ) VALUES (
                'loc_002', 2026, 420000, NULL, '124', 'Main St',
                'N1090', 'Downtown', 'Ward 1', 'DC1', 310.0, 180.0,
                2006, 'Residential', 'N', 'Residential', NULL, NULL,
                NULL, 53.5462, -113.4937
            )
            """
        )
        conn.commit()

    property_payload = viewport.fetch_property_viewport(
        test_db_path,
        west=-114,
        south=53.3,
        east=-113.2,
        north=53.8,
        zoom=18,
        limit=1,
        cursor="offset:0",
    )
    assert property_payload["render_mode"] == "property"
    assert property_payload["page"]["has_more"] is True
    assert property_payload["page"]["next_cursor"] == "offset:1"
