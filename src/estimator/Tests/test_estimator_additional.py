import builtins
import importlib
import sys
import sqlite3

from src.estimator import property_estimator as pe


def test_estimator_init_handles_missing_proximity(monkeypatch):
    original_import = builtins.__import__
    original_estimator = sys.modules.get("estimator") or importlib.import_module("types").ModuleType("estimator")
    original_proximity = sys.modules.get("estimator.proximity") or importlib.import_module("types").ModuleType("estimator.proximity")

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 1 and name == "proximity" and globals and globals.get("__package__") == "estimator":
            raise ModuleNotFoundError("No module named 'estimator.proximity'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("estimator", None)
    sys.modules.pop("estimator.proximity", None)
    module = importlib.import_module("estimator")
    assert "get_nearest_schools" not in module.__all__

    sys.modules["estimator"] = original_estimator
    sys.modules["estimator.proximity"] = original_proximity


def test_road_graph_router_returns_road_distance(monkeypatch, tmp_path):
    router = pe._RoadGraphRouter(tmp_path / "db.sqlite")

    monkeypatch.setattr(pe.proximity_module, "_load_road_graph", lambda _path: {"graph": True})
    monkeypatch.setattr(pe.proximity_module, "_road_distances_from_origin", lambda *_a, **_k: {"a": 1})
    monkeypatch.setattr(pe.proximity_module, "_road_distance_to_target", lambda *_a, **_k: 123.4)

    result = router.route_distance(53.5, -113.5, 53.6, -113.6)
    assert result["routing_mode"] == "road"
    assert result["road_distance_m"] == 123.4


def test_distance_bundle_estimates_car_time_without_osrm(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTIMATED_CAR_SPEED_KMH", "50")
    estimator = pe.PropertyEstimator(tmp_path / "db.sqlite")

    class _FakeRoadGraph:
        def route_distance(self, *_a):
            return {
                "road_distance_m": 10_000.0,
                "straight_line_m": 9_000.0,
                "routing_mode": "road",
            }

    class _FakeOsrm:
        def is_configured(self):
            return False

    estimator._road_graph = _FakeRoadGraph()
    estimator._osrm = _FakeOsrm()

    warnings: list[dict] = []
    flags: list[str] = []
    bundle = estimator._distance_bundle(
        point={"lat": 53.5, "lon": -113.5},
        target={"lat": 53.6, "lon": -113.6, "entity_id": "center"},
        label="Center",
        fallback_flags=flags,
        warnings=warnings,
    )
    assert bundle["car_travel_time_min"] == 12.0
    assert (bundle.get("car_time_source") or "").startswith("estimated:")


def test_neighbourhood_aggregates_prefer_precomputed_model(tmp_path):
    db_path = tmp_path / "est.db"
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
        """
        INSERT INTO neighbourhood_model_prod (
            neighbourhood, average_assessment, median_assessment, property_count,
            centroid_lat, centroid_lon, dataset_version, created_at
        ) VALUES ('Downtown', 999999.0, 888888.0, 123, 53.5, -113.5, 'v-test', '2026-01-01T00:00:00Z')
        """
    )
    conn.commit()
    conn.close()

    est = pe.PropertyEstimator(db_path)
    agg = est._neighbourhood_aggregates_by_name("Downtown")
    assert agg["average_assessment"] == 999999.0
    assert agg["median_assessment"] == 888888.0
    assert agg["property_count"] == 123


def test_estimate_uses_neighbourhood_value_model_adjustment(monkeypatch, tmp_path):
    db_path = tmp_path / "est.db"
    conn = sqlite3.connect(db_path)
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
            bedrooms REAL,
            bathrooms REAL,
            bedrooms_estimated REAL,
            bathrooms_estimated REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE census_prod (
            area_id TEXT, population INTEGER, households INTEGER, area_sq_km REAL,
            population_density REAL, limited_accuracy INTEGER
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
    conn.execute("INSERT INTO dataset_versions (dataset_type, version_id, promoted_at) VALUES ('a','v1','2026-01-01')")
    conn.execute(
        """
        INSERT INTO property_locations_prod (
            canonical_location_id, assessment_year, assessment_value, house_number, street_name,
            neighbourhood_id, neighbourhood, ward, zoning, lot_size, total_gross_area, year_built,
            tax_class, garage, assessment_class_1, assessment_class_2, assessment_class_3, lat, lon
        ) VALUES (
            'loc-1', 2026, 100000.0, '1', 'A',
            'n1', 'Downtown', 'w1', 'RL', 300.0, 200.0, 1990,
            'R', 'y', 'residential', NULL, NULL, 53.5, -113.5
        )
        """
    )
    conn.execute(
        "INSERT INTO property_attributes_prod (canonical_location_id, bedrooms_estimated, bathrooms_estimated) VALUES ('loc-1', 3, 2.0)"
    )
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
            neighbourhood, model_type, model_version,
            feature_schema_json, payload_json,
            train_count, test_count, r2, mae, dataset_version, created_at
        ) VALUES (
            'Downtown', 'ridge', 'test-ridge-v1',
            '{"categorical":["zoning","tax_class","garage","assessment_class_1"],"dummy_columns":["lot_size","total_gross_area","year_built","bedrooms_estimated","bathrooms_estimated"],"numeric":["lot_size","total_gross_area","year_built","bedrooms_estimated","bathrooms_estimated"]}',
            '{"coefficients":[0,1000,0,0,0],"intercept":0}',
            1000, 200, 0.5, 10000.0, 'v1', '2026-01-01T00:00:00Z'
        )
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(pe, "get_nearest_parks", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_playgrounds", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_schools", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_libraries", lambda *a, **k: [])
    monkeypatch.setattr(pe, "group_comparables_by_attributes", lambda *a, **k: {"matching": [], "non_matching": []})

    est = pe.PropertyEstimator(db_path)
    result = est.estimate(lat=53.5, lon=-113.5)
    adjustments = ((result.get("feature_breakdown") or {}).get("valuation_adjustments") or [])
    codes = [item["code"] for item in adjustments]
    assert "neighbourhood_value_model" in codes
