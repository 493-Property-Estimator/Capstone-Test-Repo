from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data_sourcing.database import connect, init_db
from src.data_sourcing.pipelines import (
    GEOSPATIAL_SIZE_LIMIT_BYTES,
    _apply_edmonton_road_enrichment,
    _build_geometry_payload,
    _canonical_location_id,
    _choose_common_value,
    _coalesce,
    _coalesce_prefer_new,
    _display_text,
    _extract_geometry_points,
    _is_placeholder_road_name,
    _load_json_object,
    _merge_json_lists,
    _merge_json_object,
    _merge_poi_rows,
    _merge_property_rows,
    _new_run_id,
    _normalize_road_name,
    _normalize_text,
    _nonnull,
    _poi_merge_key,
    _polyline_length_m,
    _property_location_key,
    _resolve_feature_name,
    _resolve_source_entity_id,
    _road_attributes_from_record,
    _road_name_candidates,
    _safe_float,
    _safe_int,
    _slug_text,
    _stable_id,
    run_assessment_ingest,
    run_deduplication,
    run_geospatial_ingest,
    run_poi_standardization,
    run_transit_ingest,
)
from src.data_sourcing.source_loader import SourcePayload


def _payload(records: list[dict], metadata: dict | None = None, size_bytes: int = 1) -> SourcePayload:
    return SourcePayload(metadata=metadata or {}, records=records, size_bytes=size_bytes, checksum="x")


@pytest.fixture()
def db_conn(tmp_path: Path):
    db_path = tmp_path / "pipelines.db"
    conn = connect(db_path)
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_pipeline_helper_functions_cover_branches():
    assert _new_run_id("x").startswith("x-")
    assert _safe_float("$1,234.5") == 1234.5
    assert _safe_float("") is None
    assert _safe_float("bad") is None
    assert _safe_int("10") == 10
    assert _safe_int("") is None
    assert _normalize_text("  a   b  ") == "a b"
    assert _normalize_text("  ") is None
    assert _slug_text("A B-1") == "ab1"
    assert _display_text("raw_value") == "Raw Value"
    assert _display_text("   ") is None
    assert _stable_id("p", "a", 1).startswith("p-")
    assert _nonnull("x")
    assert not _nonnull("")
    assert _coalesce(None, "n") == "n"
    assert _coalesce_prefer_new("old", "new") == "new"
    assert json.loads(_merge_json_lists('["a"]', ["a", "b"])) == ["a", "b"]
    assert _load_json_object("{") == {}
    assert _load_json_object("[]") == {}
    merged_obj = _merge_json_object('{"a":{"x":1}}', {"a": {"y": 2}, "b": 3})
    assert json.loads(merged_obj)["a"]["y"] == 2
    assert _property_location_key({"house_number": "1", "street_name": "Main"})[0] == "address"
    assert _property_location_key({"lat": 1.2, "lon": 3.4})[0] == "spatial"
    assert _property_location_key({"record_id": "r"}) == ("record", "r")
    assert _canonical_location_id({"record_id": "r"}).startswith("loc-")
    assert _resolve_feature_name({"name": "Road A"}, "f") == "Road A"
    assert "Park at" in _resolve_feature_name({"raw_category": "park", "address": "123 A"}, "f")
    assert _resolve_source_entity_id({"entity_id": "e1"}, "s1") == "e1"
    assert _resolve_source_entity_id({"name": "n"}, "s1").startswith("entity-")
    assert _poi_merge_key({"name": "A", "address": "B"}).startswith("poi-")
    assert _poi_merge_key({"name": "A", "lat": 1, "lon": 2}).startswith("poi-")
    assert _poi_merge_key({"lat": 1, "lon": 2}).startswith("poi-")
    assert _extract_geometry_points({"geometry_points": [[1, 2], ["x", 2], [3, 4]]}) == [(1.0, 2.0), (3.0, 4.0)]
    assert len(_extract_geometry_points({"start_lon": 1, "start_lat": 2, "end_lon": 3, "end_lat": 4})) == 2
    assert _extract_geometry_points({"lon": 1, "lat": 2}) == [(1.0, 2.0)]
    assert _extract_geometry_points({"x": 1}) == []
    assert _build_geometry_payload({}, "roads", [(1, 2), (3, 4)])["type"] == "MultiLineString"
    assert _build_geometry_payload({}, "boundaries", [(1, 2), (3, 4)])["type"] == "Polygon"
    assert _build_geometry_payload({}, "pois", [(1, 2)])["type"] == "Point"
    assert _polyline_length_m([(1, 2)]) == 0.0
    assert _polyline_length_m([(0, 0), (0, 1)]) > 0
    assert _normalize_road_name("Main Street") == "MAIN ST"
    assert _road_name_candidates({"road_name": "Main Street", "name": "Main Street"}) == ["MAIN ST"]
    assert _is_placeholder_road_name("123", "123")
    assert not _is_placeholder_road_name("Main")
    assert _choose_common_value(["A", "A", "B"]) == "A"
    attrs = _road_attributes_from_record({"street_nam": "Main", "functional": "collector"})
    assert attrs["official_road_name"] == "Main"
    assert attrs["functional_class"] == "collector"

    existing = {
        "assessment_year": 2024,
        "assessment_value": 100.0,
        "confidence": 0.5,
        "source_ids_json": '["s1"]',
        "record_ids_json": '["r1"]',
        "updated_at": "2024-01-01",
    }
    new_row = {
        "assessment_year": 2025,
        "assessment_value": 150.0,
        "confidence": 0.8,
        "link_method": "address",
        "source_ids_json": '["s2"]',
        "record_ids_json": '["r2"]',
        "updated_at": "2025-01-01",
    }
    merged = _merge_property_rows(existing, new_row)
    assert merged["assessment_value"] == 150.0
    assert json.loads(merged["source_ids_json"]) == ["s1", "s2"]

    poi_existing = {"source_ids_json": '["a"]', "source_entity_ids_json": '["x"]', "metadata_json": '{"sources":{"a":1}}'}
    poi_new = {"source_ids_json": '["b"]', "source_entity_ids_json": '["y"]', "metadata_json": '{"sources":{"b":2}}'}
    poi_merged = _merge_poi_rows(poi_existing, poi_new)
    assert "b" in json.loads(poi_merged["source_ids_json"])
    assert "sources" in json.loads(poi_merged["metadata_json"])


def test_apply_edmonton_road_enrichment_updates_existing_rows(db_conn):
    db_conn.execute(
        """
        INSERT INTO roads_prod (road_id, source_id, road_name, road_type, metadata_json)
        VALUES ('road-1', 'roads.src', 'Main Street', 'road', '{}')
        """
    )
    db_conn.execute(
        """
        INSERT INTO road_segments_prod (
            segment_id, road_id, source_id, segment_name, start_lon, start_lat, end_lon, end_lat,
            center_lon, center_lat, length_m, geometry_json, metadata_json
        ) VALUES (
            'seg-1', 'road-1', 'roads.src', 'seg-1',
            -113.5000, 53.5000, -113.4900, 53.5100,
            -113.4950, 53.5050, 1500.0, '[]', '{}'
        )
        """
    )
    db_conn.commit()

    payload = _payload(
        [
            {
                "official_road_name": "Main Street",
                "geometry_points": [[-113.5000, 53.5000], [-113.4900, 53.5100]],
                "municipal_segment_id": "m-1",
                "functional_class": "collector",
                "jurisdiction": "city",
            }
        ]
    )

    summary = _apply_edmonton_road_enrichment(db_conn, payload, "geospatial.roads_city")
    assert summary["matched_city_record_count"] == 1
    seg = db_conn.execute("SELECT official_road_name FROM road_segments_prod WHERE segment_id='seg-1'").fetchone()
    road = db_conn.execute("SELECT official_road_name FROM roads_prod WHERE road_id='road-1'").fetchone()
    assert seg["official_road_name"] == "Main Street"
    assert road["official_road_name"] == "Main Street"


def test_run_geospatial_ingest_success_and_error_branches(db_conn, monkeypatch):
    specs = {
        "geospatial.roads": {"target_dataset": "roads", "dataset": "roads", "provider": "City"},
        "geospatial.pois": {"target_dataset": "pois", "dataset": "pois", "provider": "City"},
    }
    payloads = {
        "geospatial.roads": _payload(
            [
                {
                    "entity_id": "r1",
                    "source_id": "roads.src",
                    "road_id": "road-1",
                    "road_name": "Main Street",
                    "raw_category": "road",
                    "geometry_points": [[-113.5, 53.5], [-113.49, 53.51]],
                }
            ],
            {"version": "v1", "publish_date": "2026-01-01"},
        ),
        "geospatial.pois": _payload(
            [
                {
                    "entity_id": "p1",
                    "source_id": "pois.src",
                    "name": "Library",
                    "raw_category": "library",
                    "address": "123 Main",
                    "lat": 53.5,
                    "lon": -113.5,
                },
                {
                    "entity_id": "p1",
                    "source_id": "pois.src",
                    "name": "Library",
                    "raw_category": "library",
                    "address": "123 Main",
                    "lat": 53.5,
                    "lon": -113.5,
                },
            ],
            {"version": "v2", "publish_date": "2026-01-02"},
        ),
    }
    monkeypatch.setattr("src.data_sourcing.pipelines.get_source_spec", lambda key: specs[key])
    monkeypatch.setattr("src.data_sourcing.pipelines.load_payload_for_source", lambda key, *_a, **_k: payloads[key])

    out = run_geospatial_ingest(db_conn, source_keys=["geospatial.roads", "geospatial.pois"])
    assert out["status"] == "succeeded"
    assert any(item["type"] == "roads" for item in out["datasets"])
    assert any(item["type"] == "pois" for item in out["datasets"])
    assert db_conn.execute("SELECT COUNT(*) FROM geospatial_prod WHERE dataset_type='roads'").fetchone()[0] == 1
    assert db_conn.execute("SELECT COUNT(*) FROM poi_prod").fetchone()[0] >= 1

    monkeypatch.setattr("src.data_sourcing.pipelines.get_source_spec", lambda _k: {"target_dataset": "invalid"})
    monkeypatch.setattr(
        "src.data_sourcing.pipelines.load_payload_for_source",
        lambda *_a, **_k: _payload([{"entity_id": "x"}], {}, GEOSPATIAL_SIZE_LIMIT_BYTES + 10),
    )
    out2 = run_geospatial_ingest(db_conn, source_keys=["geospatial.bad"])
    assert out2["status"] == "failed"
    assert out2["errors"]


def test_run_assessment_ingest_success_and_failure(db_conn, monkeypatch):
    tax_payload = _payload(
        [
            {
                "record_id": "r1",
                "source_id": "assess.tax",
                "assessment_value": 400000,
                "assessment_year": 2026,
                "house_number": "123",
                "street_name": "Main St",
                "lat": 53.5,
                "lon": -113.5,
                "ambiguous_hint": False,
            },
            {
                "record_id": "r2",
                "source_id": "assess.tax",
                "assessment_value": 420000,
                "assessment_year": 2026,
                "house_number": "123",
                "street_name": "Main St",
                "lat": 53.5,
                "lon": -113.5,
                "ambiguous_hint": True,
            },
        ],
        {"assessment_year": 2026, "publication_date": "2026-01-01"},
    )
    monkeypatch.setattr("src.data_sourcing.pipelines.load_payload_for_source", lambda *_a, **_k: tax_payload)
    out = run_assessment_ingest(db_conn, source_keys=["assessments.property_tax"])
    assert out["status"] == "failed"
    assert "ambiguous rate too high" in " ".join(out["errors"])

    clean_payload = _payload(
        [
            {
                "record_id": "r3",
                "source_id": "assess.tax",
                "assessment_value": 450000,
                "assessment_year": 2026,
                "house_number": "124",
                "street_name": "Main St",
                "lat": 53.5001,
                "lon": -113.5001,
            }
        ],
        {"assessment_year": 2026, "publication_date": "2026-01-01"},
    )
    monkeypatch.setattr("src.data_sourcing.pipelines.load_payload_for_source", lambda *_a, **_k: clean_payload)
    out2 = run_assessment_ingest(db_conn, source_keys=["assessments.property_tax"])
    assert out2["status"] == "succeeded"
    assert out2["promotion_status"] == "promoted"
    assert db_conn.execute("SELECT COUNT(*) FROM assessments_prod").fetchone()[0] >= 1


def test_run_transit_ingest_branches(db_conn, monkeypatch):
    out = run_transit_ingest(db_conn, source_keys=None)
    assert out["status"] == "failed"
    assert "no transit sources selected" in " ".join(out["errors"])

    monkeypatch.setattr("src.data_sourcing.pipelines.get_source_spec", lambda _k: {"target_dataset": "stops"})
    payload = _payload(
        [
            {"stop_id": "s1", "source_id": "transit.src", "stop_name": "A", "stop_lat": 53.5, "stop_lon": -113.5},
            {"entity_id": "e2", "source_id": "transit.src", "trip_headsign": "B", "geometry_points": [[-113.4, 53.4]]},
        ],
        {"version": "t1", "publish_date": "2026-02-01"},
    )
    monkeypatch.setattr("src.data_sourcing.pipelines.load_payload_for_source", lambda *_a, **_k: payload)
    out2 = run_transit_ingest(db_conn, source_keys=["transit.ets_stops"])
    assert out2["status"] == "succeeded"
    assert out2["promotion_status"] == "promoted"
    assert db_conn.execute("SELECT COUNT(*) FROM transit_prod").fetchone()[0] >= 1

    monkeypatch.setattr("src.data_sourcing.pipelines.get_source_spec", lambda _k: {"target_dataset": "bad"})
    out3 = run_transit_ingest(db_conn, source_keys=["transit.bad"])
    assert out3["status"] == "failed"


def test_run_poi_standardization_and_dedupe_branches(db_conn, monkeypatch):
    # Empty geospatial POIs path => fail
    mapping_payload = _payload([], {"mappings": {"library": {"canonical_category": "Library", "rule_id": "r1"}}})
    monkeypatch.setattr("src.data_sourcing.pipelines.load_payload_for_source", lambda *_a, **_k: mapping_payload)
    out_empty = run_poi_standardization(db_conn)
    assert out_empty["status"] == "failed"

    # Seed POIs for success path
    db_conn.execute(
        """
        INSERT INTO geospatial_prod (dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat, geometry_json)
        VALUES
        ('pois', 'poi1', 'src1', 'City Library', 'library', 'Point', -113.5000, 53.5000, '{}'),
        ('pois', 'poi2', 'src2', 'City Library', 'library', 'Point', -113.5001, 53.5001, '{}')
        """
    )
    db_conn.commit()

    out = run_poi_standardization(db_conn, taxonomy_version="v1", mapping_version="v1")
    assert out["status"] == "succeeded"
    assert out["promotion_status"] == "promoted"
    assert db_conn.execute("SELECT COUNT(*) FROM poi_standardized_prod").fetchone()[0] >= 2

    dedupe_out = run_deduplication(db_conn)
    assert dedupe_out["status"] == "succeeded"
    assert dedupe_out["publication_status"] == "published"
    assert db_conn.execute("SELECT COUNT(*) FROM canonical_entities_prod").fetchone()[0] >= 1

    # Force suspicious merge branch via threshold adjustment + distant low-similarity names.
    db_conn.execute("DELETE FROM canonical_entities_prod")
    db_conn.execute("DELETE FROM canonical_links_prod")
    db_conn.execute("DELETE FROM poi_standardized_prod")
    db_conn.execute("DELETE FROM geospatial_prod WHERE dataset_type='pois'")
    db_conn.execute(
        """
        INSERT INTO geospatial_prod (dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat, geometry_json)
        VALUES
        ('pois', 'x1', 'src1', 'A', 'library', 'Point', -113.5000, 53.5000, '{}'),
        ('pois', 'x2', 'src2', 'ZZZZ', 'library', 'Point', -113.5012, 53.5012, '{}')
        """
    )
    db_conn.execute(
        """
        INSERT INTO poi_standardized_prod (poi_id, source_id, canonical_category, raw_category, mapping_rule_id, mapping_rationale, taxonomy_version, mapping_version, unmapped)
        VALUES
        ('x1', 'src1', 'Library', 'library', 'r1', 'm', 'v1', 'v1', 0),
        ('x2', 'src2', 'Library', 'library', 'r1', 'm', 'v1', 'v1', 0)
        """
    )
    db_conn.commit()

    monkeypatch.setattr("src.data_sourcing.pipelines.DEDUPE_AUTO_MERGE_THRESHOLD", 0.3)
    bad = run_deduplication(db_conn)
    assert bad["status"] == "failed"
    assert "suspicious merges" in " ".join(bad["errors"])
