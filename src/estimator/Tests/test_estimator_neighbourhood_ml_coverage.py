from __future__ import annotations

import os
import sqlite3

import pytest

from src.estimator import proximity as prox
from src.estimator import property_estimator as pe
from src.estimator import runtime_services as rs


def _mk_min_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE property_locations_prod (
            canonical_location_id TEXT PRIMARY KEY,
            assessment_year INTEGER,
            assessment_value REAL,
            house_number TEXT,
            street_name TEXT,
            neighbourhood_id TEXT,
            neighbourhood TEXT,
            ward TEXT,
            zoning TEXT,
            lot_size REAL,
            total_gross_area REAL,
            year_built INTEGER,
            tax_class TEXT,
            garage TEXT,
            assessment_class_1 TEXT,
            assessment_class_2 TEXT,
            assessment_class_3 TEXT,
            lat REAL,
            lon REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE assessments_prod (
            canonical_location_id TEXT PRIMARY KEY,
            assessment_year INTEGER,
            assessment_value REAL,
            chosen_record_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE property_attributes_prod (
            canonical_location_id TEXT PRIMARY KEY,
            bedrooms_estimated REAL,
            bathrooms_estimated REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE dataset_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_type TEXT, version_id TEXT, promoted_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE census_prod (
            area_id TEXT,
            population INTEGER,
            households INTEGER,
            area_sq_km REAL,
            population_density REAL,
            limited_accuracy INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO dataset_versions (dataset_type, version_id, promoted_at) VALUES ('a','v1','2026-01-01')"
    )
    conn.execute(
        """
        INSERT INTO property_locations_prod (
            canonical_location_id, assessment_year, assessment_value, house_number, street_name,
            neighbourhood_id, neighbourhood, ward, zoning, lot_size, total_gross_area, year_built,
            tax_class, garage, assessment_class_1, assessment_class_2, assessment_class_3, lat, lon
        ) VALUES (
            'loc_1', 2026, 410000.0, '123', 'Main St',
            'N1090', 'Downtown', 'Ward 1', 'DC1', 300.0, 175.0, 2005,
            'Residential', 'Y', 'Residential', NULL, NULL, 53.5461, -113.4938
        )
        """
    )
    conn.execute(
        "INSERT INTO property_attributes_prod (canonical_location_id, bedrooms_estimated, bathrooms_estimated) VALUES ('loc_1', 3, 2.0)"
    )
    conn.commit()
    conn.close()


def test_estimate_can_disable_neighbourhood_value_model(tmp_path, monkeypatch):
    db_path = tmp_path / "est.db"
    _mk_min_db(db_path)

    monkeypatch.setattr(pe, "get_nearest_parks", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_playgrounds", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_schools", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_libraries", lambda *a, **k: [])
    monkeypatch.setattr(pe, "group_comparables_by_attributes", lambda *a, **k: {"matching": [], "non_matching": []})
    monkeypatch.setattr(pe.PropertyEstimator, "_load_employment_centers", lambda *_a, **_k: [])

    est = pe.PropertyEstimator(db_path)
    result = est.estimate(lat=53.5461, lon=-113.4938, enable_neighbourhood_value_model=False)
    assert "neighbourhood_value_model_disabled" in (result.get("fallback_flags") or [])


def test_distance_bundle_speed_mps_zero_leaves_car_time_none(tmp_path):
    db_path = tmp_path / "est.db"
    _mk_min_db(db_path)
    est = pe.PropertyEstimator(db_path)

    class _FakeRoadGraph:
        def route_distance(self, *_a):
            return {"road_distance_m": 1000.0, "straight_line_m": 900.0, "routing_mode": "road"}

    class _FakeOsrm:
        def is_configured(self):
            return False

    class _Svc:
        @staticmethod
        def haversine_meters(*_a, **_k):
            return 0.0

        @staticmethod
        def get_estimated_car_speed_kmh():
            return 0.0

    est._road_graph = _FakeRoadGraph()
    est._osrm = _FakeOsrm()
    est._services_module = _Svc
    bundle = est._distance_bundle(
        point={"lat": 53.5, "lon": -113.5},
        target={"lat": 53.6, "lon": -113.6, "entity_id": "x"},
        label="X",
        fallback_flags=[],
        warnings=[],
    )
    assert bundle["car_travel_time_s"] is None


def test_neighbourhood_aggregates_and_closest_other_neighbourhoods_use_model_table(tmp_path):
    db_path = tmp_path / "est.db"
    _mk_min_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE neighbourhood_model_prod (
            neighbourhood TEXT PRIMARY KEY,
            average_assessment REAL,
            median_assessment REAL,
            property_count INTEGER,
            centroid_lat REAL,
            centroid_lon REAL,
            dataset_version TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO neighbourhood_model_prod VALUES ('Downtown', 410000, 400000, 10, 53.5, -113.5, 'v', 't')"
    )
    conn.execute(
        "INSERT INTO neighbourhood_model_prod VALUES ('Other', 300000, 280000, 8, 53.51, -113.51, 'v', 't')"
    )
    conn.commit()
    conn.close()

    est = pe.PropertyEstimator(db_path)
    agg = est._neighbourhood_aggregates_by_name("Downtown")
    assert agg["median_assessment"] == 400000
    assert agg["average_assessment"] == 410000
    missing = est._neighbourhood_aggregates_by_name("MissingName")
    assert missing["property_count"] == 0 and missing["average_assessment"] is None
    others = est._closest_other_neighbourhoods("Downtown", limit=4)
    assert others and others[0]["neighbourhood"] == "Other"


def test_proximity_fetch_neighbourhood_aggregates_prefers_model_table(tmp_path):
    db_path = tmp_path / "x.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE neighbourhood_model_prod (
            neighbourhood TEXT PRIMARY KEY,
            average_assessment REAL,
            property_count INTEGER,
            centroid_lat REAL,
            centroid_lon REAL
        )
        """
    )
    conn.execute(
        "INSERT INTO neighbourhood_model_prod VALUES ('Downtown', 1.0, 2, 53.5, -113.5)"
    )
    conn.commit()
    conn.close()

    rows = prox._fetch_neighbourhood_aggregates(db_path)
    assert rows and rows[0]["neighbourhood"] == "Downtown"


def test_runtime_services_estimated_speed_invalid_and_nonpositive(monkeypatch):
    monkeypatch.setenv("ESTIMATED_CAR_SPEED_KMH", "x")
    assert rs.get_estimated_car_speed_kmh() == 45.0
    monkeypatch.setenv("ESTIMATED_CAR_SPEED_KMH", "0")
    assert rs.get_estimated_car_speed_kmh() == 45.0


def test_neighbourhood_value_model_loader_handles_bad_json(tmp_path):
    db_path = tmp_path / "est.db"
    _mk_min_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE neighbourhood_value_models_prod (
            neighbourhood TEXT,
            model_type TEXT,
            model_version TEXT,
            feature_schema_json TEXT,
            payload_json TEXT,
            train_count INTEGER,
            test_count INTEGER,
            r2 REAL,
            mae REAL,
            dataset_version TEXT,
            created_at TEXT,
            PRIMARY KEY (neighbourhood, model_type, model_version)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO neighbourhood_value_models_prod (
            neighbourhood, model_type, model_version, feature_schema_json, payload_json, created_at
        ) VALUES ('Downtown', 'ridge', 'v', '{bad', '{bad', 't')
        """
    )
    conn.commit()
    conn.close()

    est = pe.PropertyEstimator(db_path)
    assert est._load_neighbourhood_value_model(neighbourhood="Downtown", model_type="ridge") is None


def test_neighbourhood_ml_adjustment_cover_return_branches(tmp_path):
    db_path = tmp_path / "est.db"
    _mk_min_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE neighbourhood_value_models_prod (
            neighbourhood TEXT,
            model_type TEXT,
            model_version TEXT,
            feature_schema_json TEXT,
            payload_json TEXT,
            train_count INTEGER,
            test_count INTEGER,
            r2 REAL,
            mae REAL,
            dataset_version TEXT,
            created_at TEXT,
            PRIMARY KEY (neighbourhood, model_type, model_version)
        )
        """
    )
    # Insert a row for a different neighbourhood to ensure table row count > 0.
    conn.execute(
        """
        INSERT INTO neighbourhood_value_models_prod (
            neighbourhood, model_type, model_version, feature_schema_json, payload_json, created_at
        ) VALUES ('Other', 'ridge', 'v', '{"dummy_columns":["x"],"numeric":[],"categorical":[]}', '{"coefficients":[1],"intercept":0}', 't')
        """
    )
    conn.commit()
    conn.close()

    est = pe.PropertyEstimator(db_path)
    baseline = {
        "matched_property": True,
        "canonical_location_id": "loc_1",
        "assessment_value": 410000.0,
        "neighbourhood": None,
    }
    # no neighbourhood -> line 965
    assert est._neighbourhood_ml_adjustment(baseline=baseline, neighbourhood_context={"primary_neighbourhood": ""}) is None
    # no canonical_location_id -> line 969
    assert est._neighbourhood_ml_adjustment(
        baseline={**baseline, "canonical_location_id": None}, neighbourhood_context={"primary_neighbourhood": "Downtown"}
    ) is None
    # missing feature row -> line 972
    assert est._neighbourhood_ml_adjustment(
        baseline={**baseline, "canonical_location_id": "missing"}, neighbourhood_context={"primary_neighbourhood": "Downtown"}
    ) is None
    # models not found -> line 977
    assert est._neighbourhood_ml_adjustment(
        baseline={**baseline, "neighbourhood": "Downtown"}, neighbourhood_context={"primary_neighbourhood": "Downtown"}
    ) is None


def test_neighbourhood_ml_adjustment_preds_empty_branch(tmp_path):
    db_path = tmp_path / "est.db"
    _mk_min_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE neighbourhood_value_models_prod (
            neighbourhood TEXT,
            model_type TEXT,
            model_version TEXT,
            feature_schema_json TEXT,
            payload_json TEXT,
            train_count INTEGER,
            test_count INTEGER,
            r2 REAL,
            mae REAL,
            dataset_version TEXT,
            created_at TEXT,
            PRIMARY KEY (neighbourhood, model_type, model_version)
        )
        """
    )
    # Schema/payload that will make predict_ridge return None -> preds empty -> line 983.
    conn.execute(
        """
        INSERT INTO neighbourhood_value_models_prod (
            neighbourhood, model_type, model_version, feature_schema_json, payload_json, created_at
        ) VALUES ('Downtown', 'ridge', 'v', '{"dummy_columns":[],"numeric":[],"categorical":[]}', '{"coefficients":[],"intercept":0}', 't')
        """
    )
    conn.commit()
    conn.close()

    est = pe.PropertyEstimator(db_path)
    baseline = {
        "matched_property": True,
        "canonical_location_id": "loc_1",
        "assessment_value": 410000.0,
        "neighbourhood": "Downtown",
    }
    assert est._neighbourhood_ml_adjustment(baseline=baseline, neighbourhood_context={"primary_neighbourhood": "Downtown"}) is None


def test_closest_other_neighbourhoods_anchor_missing_returns_empty(tmp_path):
    db_path = tmp_path / "est.db"
    _mk_min_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE neighbourhood_model_prod (
            neighbourhood TEXT PRIMARY KEY,
            average_assessment REAL,
            median_assessment REAL,
            property_count INTEGER,
            centroid_lat REAL,
            centroid_lon REAL,
            dataset_version TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO neighbourhood_model_prod VALUES ('Other', 300000, 280000, 8, 53.51, -113.51, 'v', 't')"
    )
    conn.commit()
    conn.close()

    est = pe.PropertyEstimator(db_path)
    assert est._closest_other_neighbourhoods("Downtown", limit=4) == []


@pytest.mark.parametrize(
    "baseline, context",
    [
        ({"matched_property": False}, {"primary_neighbourhood": "Downtown"}),
        ({"matched_property": True, "canonical_location_id": None}, {"primary_neighbourhood": "Downtown"}),
        ({"matched_property": True, "canonical_location_id": "loc_1"}, {"primary_neighbourhood": ""}),
    ],
)
def test_neighbourhood_ml_adjustment_early_returns(tmp_path, baseline, context):
    db_path = tmp_path / "est.db"
    _mk_min_db(db_path)
    est = pe.PropertyEstimator(db_path)
    assert est._neighbourhood_ml_adjustment(baseline=baseline, neighbourhood_context=context) is None
