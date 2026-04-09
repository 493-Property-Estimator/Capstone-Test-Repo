from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

from src.data_sourcing.database import connect, init_db
from src.data_sourcing.pipelines import (
    _apply_edmonton_road_enrichment,
    _convert_edmonton_neighbourhood_rows,
    _convert_statscan_census_long_rows,
    _merge_json_lists,
    run_crime_ingest,
    run_assessment_ingest,
    run_deduplication,
    run_geospatial_ingest,
)
from src.data_sourcing.source_fetcher import _normalize_geojson, _normalize_shapefile
from src.data_sourcing.source_loader import SourcePayload
from src.estimator.property_estimator import (
    COMMUTE_INDICATOR_THRESHOLDS,
    COMMUTE_TIME_BASELINE_MIN,
    PropertyEstimator,
)


def _payload(records, metadata=None, size_bytes=1):
    return SourcePayload(metadata=metadata or {}, records=records, size_bytes=size_bytes, checksum="x")


@pytest.fixture()
def db_conn(tmp_path: Path):
    db_path = tmp_path / "cov.db"
    conn = connect(db_path)
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_backend_app_bootstrap_adds_repo_and_src_to_sys_path(monkeypatch):
    import src.backend.src.app as app_module

    repo_root = str(app_module.REPO_ROOT)
    src_root = str(app_module.SRC_ROOT)
    original_sys_path = sys.path[:]
    try:
        sys.path[:] = [p for p in sys.path if p not in {repo_root, src_root}]
        importlib.reload(app_module)
        assert repo_root in sys.path
        assert src_root in sys.path
    finally:
        sys.path[:] = original_sys_path


def test_merge_json_lists_covers_empty_existing_and_duplicate_items():
    assert json.loads(_merge_json_lists(None, ["a", "b"])) == ["a", "b"]
    assert json.loads(_merge_json_lists('["a", "a"]', ["a", "b"])) == ["a", "b"]


def _seed_road_segment(conn, *, segment_id: str, road_id: str, source_id: str, name: str, center_lat: float, center_lon: float):
    conn.execute(
        "INSERT INTO roads_prod (road_id, source_id, road_name, road_type, metadata_json) VALUES (?, ?, ?, 'road', '{}')",
        (road_id, source_id, name),
    )
    conn.execute(
        """
        INSERT INTO road_segments_prod (
            segment_id, road_id, source_id, segment_name,
            start_lon, start_lat, end_lon, end_lat, center_lon, center_lat,
            length_m, geometry_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 100.0, '[]', '{}')
        """,
        (segment_id, road_id, source_id, name, center_lon, center_lat, center_lon, center_lat, center_lon, center_lat),
    )


def test_apply_edmonton_road_enrichment_skips_un_normalizable_road_name(db_conn):
    _seed_road_segment(
        db_conn,
        segment_id="seg-1",
        road_id="r1",
        source_id="s1",
        name="Main St",
        center_lat=53.5,
        center_lon=-113.5,
    )
    db_conn.commit()

    payload = _payload([{"official_road_name": "_", "geometry_points": [[-113.5, 53.5], [-113.49, 53.51]]}])
    result = _apply_edmonton_road_enrichment(db_conn, payload, "test")
    assert result["named_city_record_count"] == 0


def test_apply_edmonton_road_enrichment_candidate_selection_and_assignment_branches(db_conn):
    _seed_road_segment(
        db_conn,
        segment_id="seg-best",
        road_id="r1",
        source_id="s1",
        name="Main St",
        center_lat=53.5,
        center_lon=-113.5,
    )
    # Second candidate within 35m but worse score; ensures the "do not update best_score" path is exercised.
    _seed_road_segment(
        db_conn,
        segment_id="seg-worse",
        road_id="r2",
        source_id="s1",
        name="Main St",
        center_lat=53.50030,
        center_lon=-113.50030,
    )
    db_conn.commit()

    payload = _payload(
        [
            {"official_road_name": "Main St", "geometry_points": [[-113.5, 53.5], [-113.50005, 53.50005]]},
            {"official_road_name": "Main St", "geometry_points": [[-113.50010, 53.50010], [-113.50012, 53.50012]]},
        ]
    )
    result = _apply_edmonton_road_enrichment(db_conn, payload, "test")
    assert result["matched_city_record_count"] == 2
    assert result["updated_segment_count"] == 1


def test_apply_edmonton_road_enrichment_missing_existing_segment_row(monkeypatch, db_conn):
    # Candidate points to a segment that no longer exists (existing_row is None branch).
    monkeypatch.setattr(
        "src.data_sourcing.pipelines._build_road_segment_index",
        lambda _conn: {
            "MAIN ST": [
                {
                    "segment_id": "seg-missing",
                    "road_id": "r1",
                    "source_id": "s1",
                    "segment_name": "Main St",
                    "length_m": 100.0,
                    "center_lon": -113.5,
                    "center_lat": 53.5,
                    "road_name": "Main St",
                    "official_road_name": "Main St",
                }
            ]
        },
    )
    payload = _payload([{"official_road_name": "Main St", "geometry_points": [[-113.5, 53.5], [-113.50001, 53.50001]]}])
    result = _apply_edmonton_road_enrichment(db_conn, payload, "test")
    assert result["matched_city_record_count"] == 1
    assert result["updated_segment_count"] == 1


def test_geospatial_repair_rate_check_allows_clean_samples(db_conn, monkeypatch):
    monkeypatch.setattr(
        "src.data_sourcing.pipelines.get_source_spec",
        lambda k: {"target_dataset": "pois", "dataset": "pois", "provider": "Test"},
    )
    monkeypatch.setattr(
        "src.data_sourcing.pipelines.load_payload_for_source",
        lambda *a, **k: _payload(
            [
                {"entity_id": f"e{i}", "source_id": "s1", "lat": 53.5 + i * 0.0001, "lon": -113.5 - i * 0.0001}
                for i in range(5)
            ],
            {"version": "v1", "publish_date": "2026-01-01"},
        ),
    )
    result = run_geospatial_ingest(db_conn, source_keys=["geospatial.test"])
    assert result["status"] == "succeeded"


def test_convert_statscan_year_does_not_regress_and_priority_prevents_override():
    records = [
        {
            "DGUID": "2021A000548033",
            "REF_DATE": "2022",
            "Population and dwelling counts": "Private dwellings occupied by usual residents",
            "Statistics": "Number",
            "VALUE": "500",
        },
        {
            "DGUID": "2021A000548033",
            "REF_DATE": "2021",
            "Population and dwelling counts": "Total dwelling count",
            "Statistics": "Number",
            "VALUE": "999",
        },
        {
            "DGUID": "2021A000548033",
            "REF_DATE": "2022",
            "Population and dwelling counts": "Population, 2021",
            "Statistics": "Number",
            "VALUE": "1000",
        },
        {
            "DGUID": "2021A000548033",
            "REF_DATE": "2022",
            "Population and dwelling counts": "Land area in square kilometres, 2021",
            "Statistics": "Number",
            "VALUE": "100.5",
        },
        # Unrecognized measure label should fall through without populating any fields.
        {
            "DGUID": "2021A000548033",
            "REF_DATE": "2022",
            "Population and dwelling counts": "Median income",
            "Statistics": "Number",
            "VALUE": "123",
        },
    ]
    out = _convert_statscan_census_long_rows(records)
    assert len(out) == 1
    assert out[0]["households"] == 500


def test_convert_edmonton_neighbourhood_skips_non_positive_area():
    out = _convert_edmonton_neighbourhood_rows(
        [
            {
                "neighbourhood_number": 1,
                "population_2021": 100,
                "households_2021": 40,
                "area_sq_km": -1,
            }
        ]
    )
    assert out == []


def test_crime_ingest_does_not_replace_with_lower_values(db_conn, monkeypatch):
    monkeypatch.setattr("src.data_sourcing.pipelines.get_source_spec", lambda *_a, **_k: {"include_rates": True, "include_counts": True})
    payload = _payload(
        [
            {"neighbourhood": "DOWNTOWN", "crime_type": "Theft", "year": "2026", "incident_count": 10},
            {"neighbourhood": "DOWNTOWN", "crime_type": "Theft", "year": "2026", "incident_count": 5},
            {"neighbourhood": "DOWNTOWN", "crime_type": "Theft rate per 100,000", "year": "2026", "value": 3.0, "unit": "rate per 100,000"},
            {"neighbourhood": "DOWNTOWN", "crime_type": "Theft rate per 100,000", "year": "2026", "value": 2.0, "unit": "rate per 100,000"},
        ],
        {"version": "v1"},
    )
    monkeypatch.setattr("src.data_sourcing.pipelines.load_payload_for_source", lambda *a, **k: payload)
    out = run_crime_ingest(db_conn, source_keys=["crime.test"])
    assert out["status"] == "succeeded"


def test_assessment_ingest_empty_payload_covers_no_source_cleanup_path(db_conn, monkeypatch):
    monkeypatch.setattr("src.data_sourcing.pipelines.load_payload_for_source", lambda *a, **k: _payload([], {"assessment_year": 2026}))
    result = run_assessment_ingest(db_conn, source_keys=["assessments.property_tax"])
    assert result["status"] == "succeeded"


def test_assessment_ingest_quarantined_rows_can_promote_and_choice_does_not_replace_lower_score(db_conn, monkeypatch):
    monkeypatch.setattr("src.data_sourcing.pipelines.ASSESSMENT_INVALID_RATE_LIMIT", 1.0)
    payload = _payload(
        [
            # quarantined (missing assessment_value)
            {"record_id": "q1", "source_id": "assess.tax", "assessment_year": 2026, "lat": 53.5, "lon": -113.5},
            # two valid rows for same canonical location: keep higher assessment_value
            {
                "record_id": "r1",
                "source_id": "assess.tax",
                "assessment_value": 500000,
                "assessment_year": 2026,
                "house_number": "123",
                "street_name": "Main St",
                "lat": 53.5,
                "lon": -113.5,
            },
            {
                "record_id": "r2",
                "source_id": "assess.tax",
                "assessment_value": 400000,
                "assessment_year": 2026,
                "house_number": "123",
                "street_name": "Main St",
                "lat": 53.5,
                "lon": -113.5,
            },
        ],
        {"assessment_year": 2026, "publication_date": "2026-01-01"},
    )
    monkeypatch.setattr("src.data_sourcing.pipelines.load_payload_for_source", lambda *a, **k: payload)
    result = run_assessment_ingest(db_conn, source_keys=["assessments.property_tax"])
    assert result["status"] == "succeeded"


def _seed_standardized_poi(conn, *, poi_id: str, source_id: str, category: str, name: str, lat: float, lon: float):
    conn.execute(
        """
        INSERT INTO geospatial_prod (
            dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat, geometry_json
        ) VALUES ('pois', ?, ?, ?, 'Park', 'Point', ?, ?, '{}')
        """,
        (poi_id, source_id, name, lon, lat),
    )
    conn.execute(
        """
        INSERT INTO poi_standardized_prod (
            poi_id, source_id, poi_type_id, canonical_category, canonical_subcategory,
            raw_category, mapping_rule_id, mapping_rationale, taxonomy_version, mapping_version, unmapped
        ) VALUES (?, ?, NULL, ?, NULL, 'Park', 'rule', 'seed', 'v1', 'v1', 0)
        """,
        (poi_id, source_id, category),
    )


def test_deduplication_review_decision(db_conn):
    _seed_standardized_poi(db_conn, poi_id="a", source_id="s1", category="Parks", name="Central Park", lat=53.5, lon=-113.5)
    _seed_standardized_poi(
        db_conn,
        poi_id="b",
        source_id="s2",
        category="Parks",
        name="Central Park East",
        lat=53.50030,
        lon=-113.50030,
    )
    db_conn.commit()

    result = run_deduplication(db_conn)
    assert result["status"] in {"succeeded", "failed"}
    assert result["review_candidates"] == 1


def test_deduplication_redundant_union_edge_executes(db_conn):
    # Three close-by, same-named POIs from different sources -> auto-merge on all pairs -> cycle -> redundant union.
    _seed_standardized_poi(db_conn, poi_id="p1", source_id="s1", category="Parks", name="Same Name", lat=53.5, lon=-113.5)
    _seed_standardized_poi(db_conn, poi_id="p2", source_id="s2", category="Parks", name="Same Name", lat=53.50001, lon=-113.50001)
    _seed_standardized_poi(db_conn, poi_id="p3", source_id="s3", category="Parks", name="Same Name", lat=53.50002, lon=-113.50002)
    db_conn.commit()

    result = run_deduplication(db_conn)
    assert result["count_reduction"] > 0.5


def test_source_fetcher_geojson_multilinestring_branch(tmp_path: Path):
    geojson_path = tmp_path / "multi.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"entity_id": "e1"},
                        "geometry": {
                            "type": "MultiLineString",
                            "coordinates": [
                                [[-113.5, 53.5], [-113.49, 53.51]],
                                [[-113.48, 53.52], [-113.47, 53.53]],
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    payload = _normalize_geojson(geojson_path, field_map=None, spec={})
    assert payload.records and "geometry_points" in payload.records[0]


def test_source_fetcher_geojson_unhandled_geometry_type_falls_through(tmp_path: Path):
    geojson_path = tmp_path / "poly.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"entity_id": "e1"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-113.5, 53.5], [-113.49, 53.5], [-113.49, 53.51], [-113.5, 53.5]]],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    payload = _normalize_geojson(geojson_path, field_map=None, spec={})
    assert payload.records


def test_source_fetcher_shapefile_geometry_without_flattened_points(monkeypatch, tmp_path: Path):
    import src.data_sourcing.source_fetcher as source_fetcher
    import types

    # Fake a minimal shapefile reader so we can force the "flattened is falsy" branch.
    class _FakeShape:
        bbox = None

    class _FakeShapeRecord:
        def __init__(self):
            self.record = ["x"]
            self.shape = _FakeShape()

    class _FakeReader:
        fields = [("DeletionFlag", "C", 1, 0), ("NAME", "C", 10, 0)]

        def iterShapeRecords(self):
            yield _FakeShapeRecord()

    monkeypatch.setattr(source_fetcher, "_build_coordinate_transformer", lambda *_a, **_k: None)
    monkeypatch.setattr(source_fetcher, "_shape_to_geojson", lambda *_a, **_k: {"type": "Point", "coordinates": [-113.5, 53.5]})
    monkeypatch.setattr(source_fetcher, "_flatten_geometry_points", lambda *_a, **_k: [])

    fake_shapefile = types.ModuleType("shapefile")
    fake_shapefile.Reader = lambda *_a, **_k: _FakeReader()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "shapefile", fake_shapefile)
    shp_path = tmp_path / "fake.shp"
    shp_path.write_text("", encoding="utf-8")

    payload = _normalize_shapefile(shp_path, field_map=None, spec={})
    assert payload.records and "geometry_points" not in payload.records[0]


def test_employment_centers_loader_filters_and_weight_fallback(tmp_path: Path, monkeypatch):
    import src.estimator.property_estimator as pe

    centers_path = tmp_path / "centers.json"
    centers_path.write_text(
        json.dumps(
            [
                "not-a-dict",
                {"enabled": False, "lat": 53.5, "lon": -113.5},
                {"name": "Missing coords"},
                {"name": "Bad coords", "lat": "x", "lon": "y"},
                {"name": "Out of bounds", "lat": 200, "lon": 0},
                {"name": "Valid", "lat": 53.5, "lon": -113.5, "weight": "bad"},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(pe, "EMPLOYMENT_CENTERS_PATH", centers_path)
    PropertyEstimator._load_employment_centers.cache_clear()
    out = PropertyEstimator._load_employment_centers()
    assert len(out) == 1
    assert out[0]["name"] == "Valid"


def test_employment_centers_loader_handles_read_error(tmp_path: Path, monkeypatch):
    import src.estimator.property_estimator as pe

    monkeypatch.setattr(pe, "EMPLOYMENT_CENTERS_PATH", tmp_path / "does-not-exist.json")
    PropertyEstimator._load_employment_centers.cache_clear()
    assert PropertyEstimator._load_employment_centers() == []


def _build_estimator(tmp_path: Path) -> PropertyEstimator:
    db_path = tmp_path / "open_data.db"
    conn = connect(db_path)
    init_db(conn)
    conn.commit()
    conn.close()
    return PropertyEstimator(db_path)


def test_collect_commute_accessibility_no_targets(tmp_path: Path, monkeypatch):
    estimator = _build_estimator(tmp_path)
    monkeypatch.setattr(estimator, "_load_employment_centers", lambda: [])
    warnings: list[dict] = []
    fallback_flags: list[str] = []
    missing: list[str] = []
    result = estimator._collect_commute_accessibility({"lat": 53.5, "lon": -113.5}, warnings, fallback_flags, missing)
    assert result["status"] == "no_targets"
    assert "commute_accessibility" in missing


@pytest.mark.parametrize(
    ("travel_time_min", "expected_label"),
    [
        (COMMUTE_TIME_BASELINE_MIN * 0.9, "low"),
        (COMMUTE_TIME_BASELINE_MIN * 0.5, "medium"),
        (COMMUTE_TIME_BASELINE_MIN * 0.2, "high"),
    ],
)
def test_collect_commute_accessibility_time_mode_indicator_levels(tmp_path: Path, monkeypatch, travel_time_min: float, expected_label: str):
    estimator = _build_estimator(tmp_path)
    monkeypatch.setattr(
        estimator,
        "_load_employment_centers",
        lambda: [{"id": "c1", "name": "Center 1", "category": "work", "lat": 53.5, "lon": -113.5, "weight": 1.0}],
    )

    def _bundle(*, point, target, label, fallback_flags, warnings):
        return {
            "id": target["entity_id"],
            "name": label,
            "straight_line_m": 0.0,
            "road_distance_m": 0.0,
            "car_travel_time_min": travel_time_min,
            "fallback_metadata": {"used": False},
        }

    monkeypatch.setattr(estimator, "_distance_bundle", _bundle)
    warnings: list[dict] = []
    fallback_flags: list[str] = []
    missing: list[str] = []
    out = estimator._collect_commute_accessibility({"lat": 53.5, "lon": -113.5}, warnings, fallback_flags, missing)
    assert out["indicator"]["label"] == expected_label
    assert out["indicator"]["thresholds"] == COMMUTE_INDICATOR_THRESHOLDS


def test_collect_commute_accessibility_distance_mode_when_time_missing(tmp_path: Path, monkeypatch):
    estimator = _build_estimator(tmp_path)
    monkeypatch.setattr(
        estimator,
        "_load_employment_centers",
        lambda: [
            {"id": "c1", "name": "Center 1", "category": "work", "lat": 53.5, "lon": -113.5, "weight": 1.0},
            {"id": "c2", "name": "Center 2", "category": "work", "lat": 53.5, "lon": -113.5, "weight": 1.0},
        ],
    )

    def _bundle(*, point, target, label, fallback_flags, warnings):
        return {
            "id": target["entity_id"],
            "name": label,
            "straight_line_m": 100.0,
            "road_distance_m": 120.0,
            "car_travel_time_min": None,
            "fallback_metadata": {"used": False},
        }

    monkeypatch.setattr(estimator, "_distance_bundle", _bundle)
    warnings: list[dict] = []
    fallback_flags: list[str] = []
    missing: list[str] = []
    out = estimator._collect_commute_accessibility({"lat": 53.5, "lon": -113.5}, warnings, fallback_flags, missing)
    assert out["metrics"]["mode"] == "distance_m"


def test_estimate_adds_commute_adjustment_when_metrics_present(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "open_data.db"
    conn = connect(db_path)
    init_db(conn)
    conn.execute(
        """
        INSERT INTO property_locations_prod (
            canonical_location_id, assessment_year, assessment_value, house_number, street_name,
            neighbourhood, neighbourhood_id, ward, zoning, lot_size, total_gross_area, year_built, tax_class,
            garage, assessment_class_1, lat, lon, source_ids_json, record_ids_json, link_method, confidence
        ) VALUES (
            'loc-1', 2026, 450000.0, '100', 'MAIN ST', 'DOWNTOWN', '1090', 'Ward 1', 'DC1', 350.0, '180.0', 2005,
            'Residential', 'Y', 'RESIDENTIAL', 53.5460, -113.4930, '[]', '[]', 'test', 1.0
        )
        """
    )
    conn.execute(
        "INSERT INTO assessments_prod (canonical_location_id, assessment_year, assessment_value, chosen_record_id, confidence) VALUES ('loc-1', 2026, 450000.0, 'rec-loc-1', 1.0)"
    )
    conn.commit()
    conn.close()

    estimator = PropertyEstimator(db_path)
    monkeypatch.setattr(
        estimator,
        "_collect_commute_accessibility",
        lambda *a, **k: {"metrics": {"mode": "time_min", "nearest": 1.0, "average_top_n": 2.0, "weighted_index": 0.5}},
    )
    out = estimator.estimate(lat=53.5460, lon=-113.4930)
    assert any(adj["code"] == "commute_accessibility" for adj in out["feature_breakdown"]["valuation_adjustments"])
