from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from estimator import property_estimator as pe
from estimator import proximity as prox


def _mk_estimator(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    db = tmp_path / "est.db"
    conn = sqlite3.connect(db)
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
        INSERT INTO property_locations_prod VALUES
        ('loc-1',2026,410000,'123','MAIN ST','1090','Downtown','Ward 1','DC1',300,170,2005,'Residential','Y','R',NULL,NULL,53.5461,-113.4938),
        ('loc-2',2026,450000,'200','RIVER RD','2000','Oliver','Ward 2','RF3',350,200,2010,'Residential','N','R',NULL,NULL,53.5470,-113.4910)
        """
    )
    conn.execute("INSERT INTO assessments_prod VALUES ('loc-1',2026,415000,'rec-1')")
    conn.execute("INSERT INTO property_attributes_prod VALUES ('loc-1',3,2,NULL,NULL)")
    conn.execute("INSERT INTO census_prod VALUES ('N1090',25000,10000,5.0,5000.0,0)")
    conn.commit()
    conn.close()

    class Svc:
        @staticmethod
        def haversine_meters(a1, o1, a2, o2):
            return abs(a1 - a2) * 100000 + abs(o1 - o2) * 100000

        class OsrmService:
            def __init__(self):
                self._configured = False

            def is_configured(self):
                return self._configured

            def route(self, *args, **kwargs):
                return {"duration_s": 100.0, "distance_m": 900.0}

        class SQLiteCrimeProvider:
            def __init__(self, _db):
                pass

            def is_available(self):
                return False

            def summary_by_neighbourhood(self, _n):
                return None

        class UnavailableCrimeProvider:
            def is_available(self):
                return False

            def summary_by_neighbourhood(self, _n):
                return None

    svc = Svc.OsrmService()
    assert svc.route() == {"duration_s": 100.0, "distance_m": 900.0}
    crime = Svc.SQLiteCrimeProvider(None)
    assert crime.is_available() is False
    assert crime.summary_by_neighbourhood("x") is None
    unavailable = Svc.UnavailableCrimeProvider()
    assert unavailable.is_available() is False
    assert unavailable.summary_by_neighbourhood("x") is None

    est = pe.PropertyEstimator.__new__(pe.PropertyEstimator)
    est._db_path = db
    est._services_module = Svc
    est._road_graph = None
    est._transit = None
    est._osrm = Svc.OsrmService()
    est._crime_provider = Svc.UnavailableCrimeProvider()
    return est


def _mk_prox_db(tmp_path: Path) -> Path:
    db = tmp_path / "prox.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE property_locations_prod (
            canonical_location_id TEXT PRIMARY KEY, suite TEXT, house_number TEXT, street_name TEXT,
            neighbourhood TEXT, ward TEXT, assessment_value REAL, lat REAL, lon REAL, point_location TEXT,
            zoning TEXT, lot_size REAL, total_gross_area REAL, year_built INTEGER, garage TEXT, tax_class TEXT,
            assessment_class_1 TEXT, assessment_class_2 TEXT, assessment_class_3 TEXT
        )
        """
    )
    conn.execute(
        "CREATE TABLE property_attributes_prod (canonical_location_id TEXT PRIMARY KEY, bedrooms REAL, bathrooms REAL, bedrooms_estimated REAL, bathrooms_estimated REAL)"
    )
    conn.execute(
        "CREATE TABLE geospatial_prod (dataset_type TEXT, entity_id TEXT, source_id TEXT, name TEXT, raw_category TEXT, canonical_geom_type TEXT, lat REAL, lon REAL, geometry_json TEXT)"
    )
    conn.execute(
        "CREATE TABLE poi_prod (canonical_poi_id TEXT PRIMARY KEY, source_dataset TEXT, name TEXT, raw_category TEXT, raw_subcategory TEXT, lat REAL, lon REAL)"
    )
    conn.execute(
        "CREATE TABLE road_segments_prod (geometry_json TEXT, start_lon REAL, start_lat REAL, end_lon REAL, end_lat REAL, length_m REAL)"
    )
    conn.execute(
        "INSERT INTO property_locations_prod VALUES ('loc-1',NULL,'123','MAIN ST','Downtown','W1',410000,53.5461,-113.4938,NULL,'DC1',300,170,2005,'Y','Residential','R',NULL,NULL)"
    )
    conn.execute("INSERT INTO property_attributes_prod VALUES ('loc-1',3,2,NULL,NULL)")
    conn.execute(
        "INSERT INTO geospatial_prod VALUES ('pois','s1','geospatial.school_locations','School','school','point',53.5462,-113.4937,NULL)"
    )
    conn.execute(
        "INSERT INTO geospatial_prod VALUES ('pois','p1','geospatial.parks','Park','park','point',53.5463,-113.4936,NULL)"
    )
    conn.execute(
        "INSERT INTO poi_prod VALUES ('l1','osm','Lib','Business','library',53.54615,-113.49365)"
    )
    conn.execute(
        "INSERT INTO road_segments_prod VALUES (?, -113.494,53.546, -113.493,53.546, 100.0)",
        (json.dumps([[-113.494, 53.546], [-113.493, 53.546]]),),
    )
    conn.commit()
    conn.close()
    return db


def test_proximity_validation_and_modes() -> None:
    assert prox._validate_point((-113.4, 53.5)) == (-113.4, 53.5)
    with pytest.raises(ValueError):
        prox._validate_point((1,))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        prox._validate_point((200.0, 0.0))
    with pytest.raises(ValueError):
        prox._validate_limit(0)
    assert prox._validate_limit(2) == 2
    assert prox._normalize_distance_mode("straight-line") == "manhattan"
    assert prox._normalize_distance_mode("road_network") == "road"
    with pytest.raises(ValueError):
        prox._normalize_distance_mode("bad")


def test_proximity_geometry_and_road_helpers() -> None:
    assert prox._candidate_limit(1) >= 1
    assert prox._parse_geometry_points("not-json") == []
    assert prox._parse_geometry_points(json.dumps([[1, 2], ["x"]])) == [(1.0, 2.0)]
    assert prox._normalize_node((1.12345678, 2.98765432)) == (1.123457, 2.987654)
    _ = prox._road_grid_cell((-113.4, 53.5))
    assert prox._geodesic_distance_m((0.0, 0.0), (0.0, 0.0)) == 0.0
    assert prox._manhattan_distance_m((0.0, 0.0), (0.0, 0.0)) == 0.0
    ax = prox._segment_attachments((0.0, 0.0), (0.0, 0.0), (0.0, 0.0))
    assert ax[1] == 0.0
    bx = prox._segment_attachments((2.0, 0.0), (0.0, 0.0), (1.0, 0.0))
    assert bx[1] >= 0.0
    _ = prox._project_local_xy((0.0, 0.0), (0.0, 0.0))


def test_proximity_road_graph_and_ranking(tmp_path: Path) -> None:
    db = _mk_prox_db(tmp_path)
    prox._table_exists.cache_clear()
    graph = prox._load_road_graph(Path(db))
    best = prox._road_distances_from_origin((-113.494, 53.546), graph)
    d = prox._road_distance_to_target((-113.4935, 53.546), graph, best)
    assert d >= 0.0
    ranked = prox._rank_rows(
        [{"entity_id": "x", "lon": -113.4937, "lat": 53.5462}],
        center=(-113.4938, 53.5461),
        limit=1,
        mode="manhattan",
        db_path=db,
    )
    assert ranked and ranked[0]["distance_mode"] == "manhattan"


def test_proximity_queries_and_groups(tmp_path: Path) -> None:
    db = _mk_prox_db(tmp_path)
    prox._table_exists.cache_clear()
    props = prox.get_top_closest_properties((-113.4938, 53.5461), db_path=db)
    assert props
    same = prox.get_properties_on_same_street((-113.4938, 53.5461), db_path=db)
    assert same
    schools = prox.get_nearest_schools((-113.4938, 53.5461), db_path=db)
    assert schools
    libs = prox.get_nearest_libraries((-113.4938, 53.5461), db_path=db)
    assert libs
    ctx = prox.get_neighbourhood_context((-113.4938, 53.5461), db_path=db)
    assert ctx["primary_neighbourhood"] == "Downtown"
    down = prox.get_downtown_accessibility((-113.4938, 53.5461))
    assert down["distance_mode"] == "straight_line"
    grouped = prox.group_comparables_by_attributes(
        (-113.4938, 53.5461),
        {"year_built": 2005, "garage": "Y"},
        db_path=db,
    )
    assert grouped["non_matching"] or grouped["matching"]


def test_proximity_error_branches(tmp_path: Path) -> None:
    db = _mk_prox_db(tmp_path)
    prox._table_exists.cache_clear()
    with pytest.raises(RuntimeError):
        prox._require_table(db, "missing")
    with pytest.raises(RuntimeError):
        prox._query_rows(db, "SELECT nope FROM missing", [])
    assert prox._matches_comparable_attributes({}, {}) is False
    assert prox._normalize_comparable_attributes({"garage": " y ", "year_built": 2000})["garage"] == "Y"


def test_property_estimator_normalization_helpers(tmp_path: Path) -> None:
    est = _mk_estimator(tmp_path)
    assert est._normalize_point(53.5, -113.4) == {"lat": 53.5, "lon": -113.4}
    with pytest.raises(ValueError):
        est._normalize_point(100.0, 0.0)
    attrs = est._normalize_attributes({"year_built": "2000", "garage": " y ", "x": None})
    assert attrs["year_built"] == 2000.0 and attrs["garage"] == "y"
    assert est._property_address({"house_number": "1", "street_name": "A"}) == "1 A"
    assert est._property_address({}) == "Address unavailable"
    assert pe.PropertyEstimator._round_money(-1) == 0.0
    assert pe.PropertyEstimator._round_signed_money(-1.234) == -1.23


def test_property_estimator_core_methods(tmp_path: Path, monkeypatch) -> None:
    est = _mk_estimator(tmp_path)
    nearest = est._find_nearest_property(53.5461, -113.4938)
    assert nearest is not None
    warnings = []
    flags = []
    base = est._resolve_baseline(nearest, nearest, warnings, flags)
    assert base["matched_property"] is True
    base2 = est._resolve_baseline(nearest, None, warnings, flags)
    assert base2["matched_property"] is False
    with pytest.raises(ValueError):
        est._resolve_baseline({**nearest, "assessment_value": None}, None, [], [])

    monkeypatch.setattr(pe, "get_nearest_parks", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_playgrounds", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_schools", lambda *a, **k: [])
    monkeypatch.setattr(pe, "get_nearest_libraries", lambda *a, **k: [])
    amenities = est._collect_amenities({"lat": 53.5461, "lon": -113.4938}, warnings, flags, [])
    assert all(v == [] for v in amenities.values())

    commute = est._collect_commute_accessibility({"lat": 53.5461, "lon": -113.4938}, warnings, flags, [])
    assert commute["status"] in {"ok", "no_targets"}
    if commute["targets"]:
        assert any(item["name"] == "Downtown Edmonton" for item in commute["targets"])


def test_property_estimator_value_range_confidence(tmp_path: Path) -> None:
    est = _mk_estimator(tmp_path)
    warnings = []
    flags = []
    value = est._calculate_value(
        baseline={"assessment_value": 400000.0},
        amenities={"parks": [], "playgrounds": [], "schools": [], "libraries": []},
        commute_accessibility={"metrics": {"weighted_index": 0.6, "mode": "distance_m", "nearest": 900.0, "average_top_n": 1100.0}},
        neighbourhood_context={
            "primary_average_assessment": 410000.0,
            "census_indicators": {},
            "census_indicators_available": False,
            "crime_available": False,
        },
        comparables={"matching": [], "non_matching": []},
        warnings=warnings,
        fallback_flags=flags,
    )
    assert value["final_estimate"] > 0
    rng = est._calculate_range(
        final_estimate=value["final_estimate"],
        baseline_value=400000.0,
        comparables={"matching": [], "non_matching": []},
        completeness_score=20.0,
        warnings=warnings,
    )
    assert rng["low_estimate"] <= rng["high_estimate"]
    comp = est._calculate_completeness(
        amenities={"parks": [], "playgrounds": [], "schools": [], "libraries": []},
        commute_accessibility={"metrics": None},
        neighbourhood_context={"primary_average_assessment": None, "crime_available": False, "census_indicators_available": False},
        comparables={"matching": [], "non_matching": []},
    )
    conf = est._calculate_confidence(
        matched_property=None,
        baseline={"matched_property": False},
        comparables={"matching": [], "non_matching": []},
        missing_factors=["x"],
        fallback_flags=["y"],
        amenities={"parks": [], "playgrounds": [], "schools": [], "libraries": []},
        commute_accessibility={"metrics": None},
        neighbourhood_context={"primary_average_assessment": None, "crime_available": False, "census_indicators_available": False},
    )
    assert conf["confidence_score"] >= 5.0 and comp >= 0.0


def test_property_estimator_neighbourhood_and_census(tmp_path: Path) -> None:
    est = _mk_estimator(tmp_path)
    agg = est._neighbourhood_aggregates_by_name("Downtown")
    assert agg["average_assessment"] is not None
    other = est._closest_other_neighbourhoods("Downtown", 3)
    assert isinstance(other, list)
    assert est._table_row_count("property_locations_prod") > 0
    assert est._neighbourhood_numeric_id("Downtown") == 1090
    ci = est._census_indicators_for_neighbourhood("Downtown")
    assert ci is not None and ci["population"] == 25000
    cb = est._citywide_census_baselines()
    assert cb is not None
    cp = est._comparable_payload({"house_number": "1", "street_name": "A", "distance_m": 1.2})
    assert cp["address"] == "1 A"
    pp = est._property_payload({"house_number": "1", "street_name": "A", "lat": 1.0, "lon": 2.0})
    assert pp["lat"] == 1.0 and pp["lon"] == 2.0


def test_property_estimator_estimate_orchestration(tmp_path: Path, monkeypatch) -> None:
    est = _mk_estimator(tmp_path)
    monkeypatch.setattr(est, "_find_nearest_property", lambda *_a, **_k: {"canonical_location_id": "x", "distance_m": 10.0, "assessment_value": 100000.0})
    monkeypatch.setattr(est, "_resolve_baseline", lambda *_a, **_k: {"assessment_value": 100000.0, "matched_property": True, "canonical_location_id": "x"})
    monkeypatch.setattr(est, "_collect_amenities", lambda *_a, **_k: {"parks": [], "playgrounds": [], "schools": [], "libraries": []})
    monkeypatch.setattr(
        est,
        "_collect_commute_accessibility",
        lambda *_a, **_k: {"metrics": {"weighted_index": 0.5, "mode": "distance_m", "nearest": 100.0, "average_top_n": 100.0}},
    )
    monkeypatch.setattr(est, "_collect_neighbourhood_context", lambda *_a, **_k: {"primary_average_assessment": None, "crime_available": False, "census_indicators_available": False})
    monkeypatch.setattr(est, "_collect_comparables", lambda *_a, **_k: {"matching": [], "non_matching": []})
    monkeypatch.setattr(est, "_calculate_value", lambda **_k: {"final_estimate": 100000.0, "adjustments": [], "completeness_score": 50.0, "top_positive_factors": [], "top_negative_factors": []})
    monkeypatch.setattr(est, "_calculate_range", lambda **_k: {"low_estimate": 90000.0, "high_estimate": 110000.0})
    monkeypatch.setattr(est, "_calculate_confidence", lambda **_k: {"confidence_score": 70.0, "confidence_label": "medium"})
    monkeypatch.setattr(est, "_property_payload", lambda _x: {"canonical_location_id": "x"})
    result = est.estimate(lat=53.5, lon=-113.4, property_attributes={"garage": "Y"})
    assert result["final_estimate"] == 100000.0


def test_property_estimator_neighbourhood_context_and_comparables_branches(tmp_path: Path, monkeypatch) -> None:
    est = _mk_estimator(tmp_path)
    warnings = []
    missing = []
    monkeypatch.setattr(pe, "get_neighbourhood_context", lambda *_a, **_k: {"primary_neighbourhood": None, "resolution_method": "x"})
    out = est._collect_neighbourhood_context({"lat": 53.5, "lon": -113.4}, None, warnings, missing)
    assert out["primary_neighbourhood"] is None and "neighbourhood_context" in missing

    warnings.clear()
    missing.clear()
    monkeypatch.setattr(pe, "get_neighbourhood_context", lambda *_a, **_k: {"primary_neighbourhood": "Downtown", "resolution_method": "x"})
    monkeypatch.setattr(est, "_neighbourhood_aggregates_by_name", lambda _n: {"average_assessment": 400000.0, "property_count": 1})
    monkeypatch.setattr(est, "_closest_other_neighbourhoods", lambda _n, limit: [{"neighbourhood": "Other"}][:limit])
    monkeypatch.setattr(est, "_table_row_count", lambda _t: 1)
    monkeypatch.setattr(est, "_census_indicators_for_neighbourhood", lambda _n: None)
    out2 = est._collect_neighbourhood_context({"lat": 53.5, "lon": -113.4}, {"neighbourhood": "Downtown"}, warnings, missing)
    assert out2["primary_neighbourhood"] == "Downtown"

    monkeypatch.setattr(pe, "group_comparables_by_attributes", lambda *_a, **_k: {"matching": [], "non_matching": []})
    comp = est._collect_comparables({"lat": 53.5, "lon": -113.4}, {"garage": "Y"}, warnings, missing)
    assert comp["matching"] == []


def test_property_estimator_distance_bundle_branches(tmp_path: Path) -> None:
    est = _mk_estimator(tmp_path)
    warnings = []
    flags = []
    class RG:
        def route_distance(self, *_a):
            return {"road_distance_m": 12.0, "straight_line_m": 10.0, "routing_mode": "road"}
    est._road_graph = RG()
    bundle = est._distance_bundle(
        point={"lat": 53.5, "lon": -113.4},
        target={"lat": 53.6, "lon": -113.5, "entity_id": "e", "raw_category": "x"},
        label="T",
        fallback_flags=flags,
        warnings=warnings,
    )
    assert bundle["distance_method"] in {"road", "osrm", "straight_line_fallback"}


def test_property_estimator_road_graph_router_fallback_branches(tmp_path: Path, monkeypatch) -> None:
    router = pe._RoadGraphRouter(tmp_path / "router.db")

    monkeypatch.setattr(
        pe.proximity_module,
        "_load_road_graph",
        lambda _p: {"adjacency": {(-113.4, 53.5): []}, "segments": [], "segment_grid": {}, "polylines": []},
    )
    monkeypatch.setattr(pe.proximity_module, "_road_distances_from_origin", lambda *_a, **_k: {(-113.4, 53.5): 0.0})
    monkeypatch.setattr(
        pe.proximity_module,
        "_road_distance_to_target",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("route failed")),
    )
    fallback = router.route_distance(53.5, -113.4, 53.6, -113.5)
    assert fallback["routing_mode"] == "straight_line_fallback"

    router2 = pe._RoadGraphRouter(tmp_path / "router2.db")
    monkeypatch.setattr(
        pe.proximity_module,
        "_load_road_graph",
        lambda _p: (_ for _ in ()).throw(RuntimeError("graph failed")),
    )
    fallback_no_graph = router2.route_distance(53.5, -113.4, 53.6, -113.5)
    assert fallback_no_graph["routing_mode"] == "straight_line_fallback"


def test_proximity_additional_branches(tmp_path: Path, monkeypatch) -> None:
    db = _mk_prox_db(tmp_path)
    prox._table_exists.cache_clear()
    monkeypatch.setattr(prox, "_get_nearest_geospatial_rows", lambda *_a, **_k: [{"ok": 1}])
    assert prox.get_nearest_police_stations((-113.4, 53.5), db_path=db) == [{"ok": 1}]
    assert prox.get_nearest_playgrounds((-113.4, 53.5), db_path=db) == [{"ok": 1}]
    assert prox.get_nearest_parks((-113.4, 53.5), db_path=db) == [{"ok": 1}]

    monkeypatch.setattr(prox, "_infer_street_name", lambda *_a, **_k: "")
    assert prox.get_properties_on_same_street((-113.4, 53.5), street_name="", db_path=db) == []
    assert prox._infer_street_name((-113.4, 53.5), db) in {"", "MAIN ST"}

    monkeypatch.setattr(prox, "_load_road_graph", lambda _p: {"adjacency": {}, "segments": [], "segment_grid": {}, "polylines": []})
    with pytest.raises(prox.RoadNetworkError):
        prox._rank_rows([{"lon": -113.4, "lat": 53.5}], (-113.4, 53.5), 1, "road", db_path=db)

    assert prox._rank_rows([], (-113.4, 53.5), 1, "manhattan", db_path=db) == []


def test_proximity_missing_and_fallback_paths(tmp_path: Path, monkeypatch) -> None:
    db = _mk_prox_db(tmp_path)
    prox._table_exists.cache_clear()
    monkeypatch.setattr(prox, "_fetch_neighbourhood_aggregates", lambda _db: [])
    ctx = prox.get_neighbourhood_context((-113.4, 53.5), db_path=db)
    assert ctx["resolution_method"] == "unavailable"

    monkeypatch.setattr(prox, "get_top_closest_properties", lambda **_k: [])
    assert prox._infer_street_name((-113.4, 53.5), db) == ""

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("DELETE FROM geospatial_prod")
    conn.execute(
        "INSERT INTO geospatial_prod VALUES ('pois','f1','other','Fallback','school','point',53.5,-113.4,NULL)"
    )
    conn.commit()
    conn.close()
    rows = prox._fetch_geospatial_rows(db, {"geospatial.school_locations"}, {"school"}, 1, (-113.4, 53.5))
    assert rows and rows[0]["entity_id"] == "f1"

    with pytest.raises(ValueError):
        prox._validate_point((0.0, 100.0))
    with pytest.raises(ValueError):
        prox._validate_limit(None)  # type: ignore[arg-type]


def test_proximity_road_error_helpers(tmp_path: Path) -> None:
    db = _mk_prox_db(tmp_path)
    prox._table_exists.cache_clear()

    empty_graph = {"adjacency": {}, "segments": [], "segment_grid": {}, "polylines": []}
    with pytest.raises(prox.RoadNetworkError):
        prox._road_distances_from_origin((-113.4, 53.5), empty_graph)

    graph = {"adjacency": {(-113.4, 53.5): []}, "segments": [((-113.4, 53.5), (-113.39, 53.5))], "segment_grid": {}, "polylines": []}
    with pytest.raises(prox.RoadNetworkError):
        prox._road_distance_to_target((-113.2, 53.2), graph, {})
    with pytest.raises(prox.RoadNetworkError):
        prox._snap_point_to_network((-113.2, 53.2), {"segments": [], "segment_grid": {}, "adjacency": {}, "polylines": []})

    db2 = tmp_path / "empty_roads.db"
    conn = sqlite3.connect(db2)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE road_segments_prod (geometry_json TEXT, start_lon REAL, start_lat REAL, end_lon REAL, end_lat REAL, length_m REAL)"
    )
    conn.commit()
    conn.close()
    prox._table_exists.cache_clear()
    prox._load_road_graph.cache_clear()
    with pytest.raises(prox.RoadNetworkError):
        prox._load_road_graph(db2)


def test_property_estimator_init_and_error_paths(tmp_path: Path, monkeypatch) -> None:
    class FakeSvc:
        class OsrmService:
            pass

        class SQLiteCrimeProvider:
            def __init__(self, _db):
                pass

            def is_available(self):
                return True

        class UnavailableCrimeProvider:
            pass

        @staticmethod
        def haversine_meters(*_a):
            return 0.0

    monkeypatch.setattr(pe.PropertyEstimator, "_load_testingstage_services", staticmethod(lambda: FakeSvc))
    est = pe.PropertyEstimator(tmp_path / "x.db")
    assert est._crime_provider.__class__.__name__ == "SQLiteCrimeProvider"
    assert pe.PropertyEstimator._load_testingstage_services()
    assert FakeSvc.haversine_meters(0) == 0.0

    est2 = _mk_estimator(tmp_path / "second")
    monkeypatch.setattr(est2, "_find_nearest_property", lambda *_a, **_k: None)
    with pytest.raises(ValueError):
        est2.estimate(lat=53.5, lon=-113.4)


def test_property_estimator_remaining_branches(tmp_path: Path, monkeypatch) -> None:
    est = _mk_estimator(tmp_path)
    warnings = []
    flags = []

    class O:
        def __init__(self):
            self._configured = True

        def is_configured(self):
            return True

        def route(self, *_a, **_k):
            raise RuntimeError("x")

    class T:
        def has_data(self):
            return True

        def plan_journey(self, *_a, **_k):
            raise RuntimeError("x")

    est._osrm = O()
    est._transit = T()
    bundle = est._distance_bundle(
        point={"lat": 53.5, "lon": -113.4},
        target={"lat": 53.6, "lon": -113.5, "entity_id": "e", "raw_category": "x"},
        label="T",
        fallback_flags=flags,
        warnings=warnings,
    )
    assert bundle["car_travel_time_s"] is None

    monkeypatch.setattr(pe, "group_comparables_by_attributes", lambda *_a, **_k: {"matching": [], "non_matching": []})
    comp = est._collect_comparables({"lat": 53.5, "lon": -113.4}, {}, warnings, [])
    assert comp["matching"] == []

    monkeypatch.setattr(est, "_citywide_census_baselines", lambda: {"avg_population_density": 1000.0, "avg_household_size": 2.5})
    val = est._calculate_value(
        baseline={"assessment_value": 400000.0},
        amenities={"parks": [{"road_distance_m": 100.0, "straight_line_m": 90.0}], "playgrounds": [], "schools": [], "libraries": []},
        commute_accessibility={"metrics": {"weighted_index": 0.55, "mode": "distance_m", "nearest": 100.0, "average_top_n": 120.0}},
        neighbourhood_context={
            "primary_average_assessment": 380000.0,
            "census_indicators": {"population_density": 1200.0, "household_size": 2.8, "limited_accuracy": True, "area_id": "N1090"},
            "census_indicators_available": True,
            "crime_available": False,
        },
        comparables={"matching": [{"assessment_value": 600000.0}], "non_matching": [{"assessment_value": 100000.0}]},
        warnings=warnings,
        fallback_flags=flags,
    )
    assert "final_estimate" in val

    with pytest.raises(ValueError):
        est._normalize_point(53.5, 200.0)


def test_property_estimator_branch_closures(tmp_path: Path, monkeypatch) -> None:
    assert hasattr(pe.PropertyEstimator._load_testingstage_services(), "OsrmService")
    est = _mk_estimator(tmp_path)
    warnings = []
    missing = []
    flags = []

    # _collect_amenities non-empty branch
    monkeypatch.setattr(pe, "get_nearest_parks", lambda *_a, **_k: [{"lat": 53.5, "lon": -113.4, "name": "P"}])
    monkeypatch.setattr(pe, "get_nearest_playgrounds", lambda *_a, **_k: [{"lat": 53.5, "lon": -113.4, "name": "G"}])
    monkeypatch.setattr(pe, "get_nearest_schools", lambda *_a, **_k: [{"lat": 53.5, "lon": -113.4, "name": "S"}])
    monkeypatch.setattr(pe, "get_nearest_libraries", lambda *_a, **_k: [{"lat": 53.5, "lon": -113.4, "name": "L"}])
    monkeypatch.setattr(est, "_distance_bundle", lambda **_k: {"road_distance_m": 10.0, "straight_line_m": 10.0, "transit_distance_m": 1.0, "name": "x"})
    am = est._collect_amenities({"lat": 53.5, "lon": -113.4}, warnings, flags, missing)
    assert am["parks"] and am["libraries"]

    # _collect_neighbourhood_context branches
    class CrimeAvail:
        def is_available(self):
            return True

        def summary_by_neighbourhood(self, _n):
            return {"ok": True}

    est._crime_provider = CrimeAvail()
    monkeypatch.setattr(pe, "get_neighbourhood_context", lambda *_a, **_k: {"primary_neighbourhood": "Downtown", "resolution_method": "x"})
    monkeypatch.setattr(est, "_neighbourhood_aggregates_by_name", lambda _n: {"average_assessment": 400000.0, "property_count": 1})
    monkeypatch.setattr(est, "_closest_other_neighbourhoods", lambda _n, limit: [{"neighbourhood": "Other"}][:limit])
    monkeypatch.setattr(est, "_table_row_count", lambda _t: 0)
    out = est._collect_neighbourhood_context({"lat": 53.5, "lon": -113.4}, None, warnings, missing)
    assert out["census_available"] is False
    monkeypatch.setattr(est, "_table_row_count", lambda _t: 1)
    monkeypatch.setattr(est, "_census_indicators_for_neighbourhood", lambda _n: None)
    out2 = est._collect_neighbourhood_context({"lat": 53.5, "lon": -113.4}, None, warnings, missing)
    assert out2["census_available"] is True

    # _collect_comparables empty branch
    monkeypatch.setattr(pe, "group_comparables_by_attributes", lambda *_a, **_k: {"matching": [], "non_matching": []})
    comp = est._collect_comparables({"lat": 53.5, "lon": -113.4}, {}, warnings, missing)
    assert comp["non_matching"] == []

    # osrm and transit success paths
    class OS:
        def is_configured(self):
            return True

        def route(self, *_a):
            return {"duration_s": 60.0, "distance_m": 500.0}

    class TR:
        def has_data(self):
            return True

        def plan_journey(self, *_a):
            return {"summary": {"total_distance_m": 300.0}}

    est2 = _mk_estimator(tmp_path / "osrm")
    est2._osrm = OS()
    est2._transit = TR()
    b = est2._distance_bundle(
        point={"lat": 53.5, "lon": -113.4},
        target={"lat": 53.6, "lon": -113.5, "entity_id": "e", "raw_category": "x"},
        label="T",
        fallback_flags=flags,
        warnings=warnings,
    )
    assert b["car_travel_time_s"] == 60.0 and b["transit_distance_m"] == 300.0

    # range swap branch
    swapped = est._calculate_range(
        final_estimate=-1.0,
        baseline_value=400000.0,
        comparables={"matching": [], "non_matching": []},
        completeness_score=10.0,
        warnings=warnings,
    )
    assert swapped["low_estimate"] >= swapped["high_estimate"]

    # confidence labels
    c1 = est._calculate_confidence(
        matched_property={"x": 1},
        baseline={"matched_property": True},
        comparables={"matching": [{"x": 1}], "non_matching": []},
        missing_factors=[],
        fallback_flags=[],
        amenities={"parks": [1], "playgrounds": [1], "schools": [1], "libraries": [1]},
        commute_accessibility={"metrics": {"weighted_index": 0.5}},
        neighbourhood_context={"primary_average_assessment": 1, "crime_available": True, "census_indicators_available": True},
    )
    assert c1["confidence_label"] == "high"

    # row-none branches on unpatched instance
    est3 = _mk_estimator(tmp_path / "raw")
    assert est3._neighbourhood_aggregates_by_name("Unknown")["property_count"] == 0
    assert est3._closest_other_neighbourhoods("Unknown", 2) == []
    assert est3._table_row_count("missing_table") == 0
    assert est3._census_indicators_for_neighbourhood("Unknown") is None
    assert est3._neighbourhood_numeric_id("Unknown") is None

    # invalid neighbourhood_id and missing census
    conn = sqlite3.connect(est._db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("UPDATE property_locations_prod SET neighbourhood_id='not-a-number' WHERE canonical_location_id='loc-1'")
    conn.execute("DELETE FROM census_prod")
    conn.commit()
    conn.close()
    assert est._neighbourhood_numeric_id("Downtown") is None
    assert est._citywide_census_baselines() is None
    assert pe.PropertyEstimator._dedupe_warnings([{"code": "c", "severity": "s", "message": "m"}, {"code": "c", "severity": "s", "message": "m"}]) == [{"code": "c", "severity": "s", "message": "m"}]
    assert pe.PropertyEstimator._round_signed_money(None) is None


def test_proximity_branch_closures(tmp_path: Path, monkeypatch) -> None:
    db = _mk_prox_db(tmp_path)
    prox._table_exists.cache_clear()

    # group comparables non-matching path
    grouped = prox.group_comparables_by_attributes((-113.4938, 53.5461), {"garage": "N"}, db_path=db)
    assert grouped["non_matching"]

    # fetch with limit None
    assert prox._fetch_properties(db, None, (-113.4, 53.5))
    assert prox._fetch_library_rows(db, 1, (-113.4, 53.5))
    assert prox._fetch_library_rows(db, None, (-113.4, 53.5))
    assert prox._fetch_geospatial_rows(
        db,
        {"geospatial.school_locations"},
        {"school"},
        None,
        (-113.4, 53.5),
    )
    conn3 = sqlite3.connect(db)
    conn3.row_factory = sqlite3.Row
    conn3.execute("DELETE FROM geospatial_prod WHERE source_id='s1'")
    conn3.commit()
    conn3.close()
    assert prox._fetch_geospatial_rows(
        db,
        {"geospatial.school_locations"},
        {"school"},
        None,
        (-113.4, 53.5),
    )

    # normalize/match branches
    norm = prox._normalize_comparable_attributes({"garage": "", "zoning": " dc1 ", "bathrooms": "2"})
    assert norm["zoning"] == "DC1"
    assert "year_built" not in prox._normalize_comparable_attributes({"year_built": None})
    assert prox._matches_comparable_attributes({"year_built": None}, {"year_built": 2000}) is False
    assert prox._matches_comparable_attributes({"year_built": 2010}, {"year_built": 2000}) is False
    assert prox._matches_comparable_attributes({"bedrooms": ""}, {"bedrooms": 2}) is False
    assert prox._matches_comparable_attributes({"bedrooms": 4.5}, {"bedrooms": 2}) is False
    assert prox._matches_comparable_attributes({"bathrooms": ""}, {"bathrooms": 2}) is False
    assert prox._matches_comparable_attributes({"bathrooms": 3.0}, {"bathrooms": 2}) is False
    assert prox._matches_comparable_attributes({"lot_size": ""}, {"lot_size": 10}) is False
    assert prox._matches_comparable_attributes({"lot_size": 30.0}, {"lot_size": 10.0}) is False
    assert prox._matches_comparable_attributes({"zoning": "a"}, {"zoning": "B"}) is False
    assert prox._rank_rows([], (-113.4, 53.5), 1, "manhattan", db_path=db) == []
    assert prox._matches_comparable_attributes(
        {"bedrooms": 2.0, "bathrooms": 2.0, "lot_size": 10.0},
        {"bedrooms": 2.0, "bathrooms": 2.0, "lot_size": 10.0},
    ) is True

    # road-mode success in _rank_rows
    original_load_road_graph = prox._load_road_graph
    monkeypatch.setattr(prox, "_load_road_graph", lambda _p: {"adjacency": {(-113.4, 53.5): []}, "segments": [((-113.4, 53.5), (-113.39, 53.5))], "segment_grid": {(0, 0): [0]}, "polylines": []})
    original_road_distances = prox._road_distances_from_origin
    monkeypatch.setattr(prox, "_road_distances_from_origin", lambda *_a, **_k: {(-113.4, 53.5): 0.0})
    monkeypatch.setattr(prox, "_road_distance_to_target", lambda *_a, **_k: 12.0)
    rr = prox._rank_rows([{"lon": -113.39, "lat": 53.5, "entity_id": "e"}], (-113.4, 53.5), 1, "road", db_path=db)
    assert rr[0]["distance_m"] == 12.0

    # road-mode with skipped rows -> raise
    monkeypatch.setattr(prox, "_road_distance_to_target", lambda *_a, **_k: (_ for _ in ()).throw(prox.RoadNetworkError("x")))
    with pytest.raises(prox.RoadNetworkError):
        prox._rank_rows([{"lon": -113.39, "lat": 53.5, "entity_id": "e"}], (-113.4, 53.5), 1, "road", db_path=db)

    # _load_road_graph fallback when geometry parse is short
    db2 = tmp_path / "short_geom.db"
    conn = sqlite3.connect(db2)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE road_segments_prod (geometry_json TEXT, start_lon REAL, start_lat REAL, end_lon REAL, end_lat REAL, length_m REAL)")
    conn.execute("INSERT INTO road_segments_prod VALUES (?, -113.4,53.5,-113.39,53.5,100.0)", (json.dumps([[-113.4, 53.5]]),))
    conn.commit()
    conn.close()
    prox._table_exists.cache_clear()
    prox._load_road_graph = original_load_road_graph
    prox._load_road_graph.cache_clear()
    prox._road_distances_from_origin = original_road_distances
    g2 = prox._load_road_graph(db2)
    assert g2["segments"]

    # dijkstra stale-queue branch
    monkeypatch.setattr(prox, "_snap_point_to_network", lambda *_a, **_k: [((0.0, 0.0), 0.0)])
    graph = {
        "adjacency": {
            (0.0, 0.0): [((1.0, 0.0), 10.0), ((2.0, 0.0), 1.0)],
            (2.0, 0.0): [((1.0, 0.0), 1.0)],
            (1.0, 0.0): [],
        },
        "segments": [],
        "segment_grid": {},
        "polylines": [],
    }
    best = prox._road_distances_from_origin((0.0, 0.0), graph)
    assert best[(1.0, 0.0)] == 2.0

    # snap-point both update and non-update branches + candidate duplicate-seen branch
    monkeypatch.setattr(prox, "_segment_attachments", lambda point, start, end: ([(start, 1.0)], 1.0) if start[0] == 0 else ([(start, 2.0)], 2.0))
    snaps = prox._snap_point_to_network((0.0, 0.0), {"segments": [((0.0, 0.0), (1.0, 0.0)), ((2.0, 0.0), (3.0, 0.0))], "segment_grid": {(0, 0): [0, 0, 1]}, "adjacency": {}, "polylines": []})
    assert snaps
    candidates = prox._candidate_segments_for_point(
        (0.0, 0.0),
        [((0.0, 0.0), (1.0, 0.0)), ((2.0, 0.0), (3.0, 0.0))],
        {(0, 0): [0, 0, 1]},
    )
    assert len(candidates) == 2


def test_proximity_fetch_geospatial_fallback_no_limit_branch(tmp_path: Path, monkeypatch) -> None:
    db = _mk_prox_db(tmp_path)
    prox._table_exists.cache_clear()
    captured: dict[str, list[object] | str] = {}

    def fake_query_rows(_db_path, sql, params):
        captured["sql"] = sql
        captured["params"] = list(params)
        if "source_id IN" in sql:
            return []
        return [{"entity_id": "f1"}]

    monkeypatch.setattr(prox, "_query_rows", fake_query_rows)
    out = prox._fetch_geospatial_rows(
        db,
        {"geospatial.school_locations"},
        {"school"},
        None,
        (-113.4, 53.5),
    )
    assert out == [{"entity_id": "f1"}]
    assert "LIMIT ?" not in str(captured["sql"])


def test_proximity_snap_prefers_first_when_second_is_worse(monkeypatch) -> None:
    monkeypatch.setattr(
        prox,
        "_candidate_segments_for_point",
        lambda *_a, **_k: [((0.0, 0.0), (1.0, 0.0)), ((2.0, 0.0), (3.0, 0.0))],
    )
    monkeypatch.setattr(
        prox,
        "_segment_attachments",
        lambda _point, start, _end: ([(start, 1.0)], 1.0)
        if start == (0.0, 0.0)
        else ([(start, 2.0)], 2.0),
    )
    out = prox._snap_point_to_network(
        (0.0, 0.0),
        {"segments": [], "segment_grid": {}, "adjacency": {}, "polylines": []},
    )
    assert out == [((0.0, 0.0), 1.0)]


def test_property_estimator_remaining_coverage_branches(tmp_path: Path, monkeypatch) -> None:
    est = _mk_estimator(tmp_path / "cov")
    warnings: list[dict[str, object]] = []
    missing: list[str] = []
    flags: list[str] = []

    # estimate() unmatched branch (line 118 -> 128) and matched_payload=None.
    monkeypatch.setattr(
        est,
        "_find_nearest_property",
        lambda *_a, **_k: {
            "canonical_location_id": "x",
            "distance_m": 1000.0,
            "assessment_value": 100000.0,
            "assessment_year": 2026,
            "house_number": "1",
            "street_name": "A",
            "neighbourhood": "Downtown",
            "chosen_record_id": None,
        },
    )
    monkeypatch.setattr(est, "_resolve_baseline", lambda *_a, **_k: {"assessment_value": 100000.0, "matched_property": False, "canonical_location_id": "x"})
    monkeypatch.setattr(est, "_collect_amenities", lambda *_a, **_k: {"parks": [], "playgrounds": [], "schools": [], "libraries": []})
    monkeypatch.setattr(
        est,
        "_collect_commute_accessibility",
        lambda *_a, **_k: {"metrics": {"weighted_index": 0.5, "mode": "distance_m", "nearest": 500.0, "average_top_n": 500.0}},
    )
    monkeypatch.setattr(est, "_collect_neighbourhood_context", lambda *_a, **_k: {"primary_average_assessment": None, "crime_available": False, "census_indicators_available": False})
    monkeypatch.setattr(est, "_collect_comparables", lambda *_a, **_k: {"matching": [], "non_matching": [{"assessment_value": 90000.0}]})
    monkeypatch.setattr(est, "_calculate_value", lambda **_k: {"final_estimate": 100000.0, "adjustments": [], "completeness_score": 55.0, "top_positive_factors": [], "top_negative_factors": []})
    monkeypatch.setattr(est, "_calculate_range", lambda **_k: {"low_estimate": 90000.0, "high_estimate": 110000.0})
    monkeypatch.setattr(est, "_calculate_confidence", lambda **_k: {"confidence_score": 60.0, "confidence_label": "medium"})
    result = est.estimate(lat=53.5, lon=-113.4)
    assert result["matched_property"] is None

    # _find_nearest_property row=None branch.
    est_empty = _mk_estimator(tmp_path / "empty")
    conn = sqlite3.connect(est_empty._db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("DELETE FROM property_locations_prod")
    conn.commit()
    conn.close()
    assert est_empty._find_nearest_property(53.5, -113.4) is None

    # _collect_commute_accessibility branch with a single employment center.
    monkeypatch.setattr(
        est_empty,
        "_load_employment_centers",
        lambda: [
            {
                "id": "downtown-edmonton",
                "name": "Downtown Edmonton",
                "lat": 53.5,
                "lon": -113.4,
                "weight": 1.0,
                "category": "business_district",
            }
        ],
    )
    monkeypatch.setattr(
        est_empty,
        "_distance_bundle",
        lambda **_k: {
            "name": "Downtown Edmonton",
            "road_distance_m": 12.0,
            "straight_line_m": 12.0,
            "transit_distance_m": 20.0,
            "car_travel_time_min": None,
            "fallback_metadata": {"used": False},
        },
    )
    commute = est_empty._collect_commute_accessibility({"lat": 53.5, "lon": -113.4}, warnings, flags, missing)
    assert commute["target_count"] == 1 and "commute_accessibility" not in missing

    # _collect_comparables branch where lists are non-empty (line 472 -> 482).
    monkeypatch.setattr(
        pe,
        "group_comparables_by_attributes",
        lambda *_a, **_k: {
            "matching": [{"house_number": "1", "street_name": "A", "assessment_value": 100000.0, "distance_m": 10.0}],
            "non_matching": [{"house_number": "2", "street_name": "B", "assessment_value": 90000.0, "distance_m": 15.0}],
        },
    )
    comp = est_empty._collect_comparables({"lat": 53.5, "lon": -113.4}, {"garage": "Y"}, warnings, missing)
    assert comp["matching"] and comp["non_matching"]

    # _calculate_value: no neighbourhood average and census inner gate false.
    monkeypatch.setattr(est_empty, "_citywide_census_baselines", lambda: {"avg_population_density": 1000.0, "avg_household_size": 2.0})
    val = est_empty._calculate_value(
        baseline={"assessment_value": 100000.0},
        amenities={
            "parks": [{"road_distance_m": 0.0, "straight_line_m": 0.0}],
            "playgrounds": [{"road_distance_m": 0.0, "straight_line_m": 0.0}],
            "schools": [{"road_distance_m": 0.0, "straight_line_m": 0.0}],
            "libraries": [{"road_distance_m": 0.0, "straight_line_m": 0.0}],
        },
        commute_accessibility={"metrics": {"weighted_index": 0.4, "mode": "distance_m", "nearest": 0.0, "average_top_n": 0.0}},
        neighbourhood_context={
            "primary_average_assessment": None,
            "census_indicators": {
                "population_density": 0.0,
                "household_size": 3.0,
                "limited_accuracy": False,
                "area_id": "N1090",
            },
            "census_indicators_available": True,
            "crime_available": False,
        },
        comparables={
            "matching": [{"assessment_value": 1_000_000.0}],
            "non_matching": [{"assessment_value": 1_000_000.0}],
        },
        warnings=warnings,
        fallback_flags=flags,
    )
    assert val["final_estimate"] > 0

    # guardrail branch true (force large adjustment values).
    monkeypatch.setattr(
        est_empty,
        "_adjustment",
        lambda code, label, value, metadata: {
            "code": code,
            "label": label,
            "value": 1_000_000.0,
            "metadata": metadata,
        },
    )
    val_guard = est_empty._calculate_value(
        baseline={"assessment_value": 100000.0},
        amenities={
            "parks": [{"road_distance_m": 1_000_000.0, "straight_line_m": 1_000_000.0}],
            "playgrounds": [{"road_distance_m": 1_000_000.0, "straight_line_m": 1_000_000.0}],
            "schools": [{"road_distance_m": 1_000_000.0, "straight_line_m": 1_000_000.0}],
            "libraries": [{"road_distance_m": 1_000_000.0, "straight_line_m": 1_000_000.0}],
        },
        commute_accessibility={"metrics": {"weighted_index": 0.0, "mode": "distance_m", "nearest": 1_000_000.0, "average_top_n": 1_000_000.0}},
        neighbourhood_context={
            "primary_average_assessment": 0.0,
            "census_indicators": {
                "population_density": 1.0,
                "household_size": 0.1,
                "limited_accuracy": False,
                "area_id": "N1090",
            },
            "census_indicators_available": True,
            "crime_available": False,
        },
        comparables={
            "matching": [{"assessment_value": 0.0}],
            "non_matching": [{"assessment_value": 0.0}],
        },
        warnings=warnings,
        fallback_flags=flags,
    )
    assert val_guard["final_estimate"] == 135000.0
    assert "valuation_guardrail" in flags

    # _calculate_range branch with comparable_values present (lines 770-772, 783 -> 792 false path).
    warnings_before = len(warnings)
    rng = est_empty._calculate_range(
        final_estimate=100000.0,
        baseline_value=100000.0,
        comparables={"matching": [{"assessment_value": 90000.0}], "non_matching": [{"assessment_value": 110000.0}]},
        completeness_score=95.0,
        warnings=warnings,
    )
    assert rng["high_estimate"] >= rng["low_estimate"]
    assert len(warnings) == warnings_before

    # _calculate_confidence branches: non-matching + medium, and low label.
    c_medium = est_empty._calculate_confidence(
        matched_property=None,
        baseline={"matched_property": False},
        comparables={"matching": [], "non_matching": [{"assessment_value": 1.0}]},
        missing_factors=[],
        fallback_flags=[],
        amenities={"parks": [1], "playgrounds": [1], "schools": [1], "libraries": []},
        commute_accessibility={"metrics": {"weighted_index": 0.5}},
        neighbourhood_context={"primary_average_assessment": 1.0, "crime_available": False, "census_indicators_available": False},
    )
    assert c_medium["confidence_label"] == "medium"
    c_low = est_empty._calculate_confidence(
        matched_property=None,
        baseline={"matched_property": False},
        comparables={"matching": [], "non_matching": []},
        missing_factors=["a", "b", "c", "d"],
        fallback_flags=[],
        amenities={"parks": [1], "playgrounds": [1], "schools": [1], "libraries": []},
        commute_accessibility={"metrics": {"weighted_index": 0.2}},
        neighbourhood_context={"primary_average_assessment": 1.0, "crime_available": True, "census_indicators_available": True},
    )
    assert c_low["confidence_label"] == "low"

    # _census_indicators_for_neighbourhood row=None branch (line 968).
    est5 = _mk_estimator(tmp_path / "census-none")
    conn = sqlite3.connect(est5._db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("DELETE FROM census_prod")
    conn.commit()
    conn.close()
    assert est5._census_indicators_for_neighbourhood("Downtown") is None

    # _citywide_census_baselines row=None branch via stubbed _connect (line 1018).
    class _DummyCursor:
        def fetchone(self):
            return None

    class _DummyConn:
        def execute(self, *_a, **_k):
            return _DummyCursor()

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    est4 = _mk_estimator(tmp_path / "citywide-none")
    monkeypatch.setattr(est4, "_connect", lambda: _DummyConn())
    assert est4._citywide_census_baselines() is None
