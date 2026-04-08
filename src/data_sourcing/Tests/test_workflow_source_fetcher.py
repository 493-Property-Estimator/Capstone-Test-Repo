from __future__ import annotations

import csv
import io
import json
import sqlite3
import sys
import types
import zipfile
from pathlib import Path

import pytest

from data_sourcing import source_fetcher as sf
from data_sourcing import workflow


def _workflow_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE workflow_runs (
            run_id TEXT PRIMARY KEY,
            trigger_type TEXT,
            correlation_id TEXT,
            status TEXT,
            started_at TEXT,
            completed_at TEXT,
            warnings_json TEXT,
            errors_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE workflow_steps (
            step_id TEXT,
            run_id TEXT,
            dataset_type TEXT,
            status TEXT,
            retry_count INTEGER,
            started_at TEXT,
            completed_at TEXT,
            warnings_json TEXT,
            errors_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE workflow_summaries (
            run_id TEXT,
            promoted_json TEXT,
            skipped_json TEXT,
            failed_json TEXT,
            reasons_json TEXT
        )
        """
    )
    return conn


def _fixed_now() -> str:
    return "2026-01-01T00:00:00Z"


def test_workflow_new_run_id_shape() -> None:
    run_id = workflow._new_run_id("refresh")
    assert run_id.startswith("refresh-")
    assert len(run_id.split("-")) >= 3


def test_workflow_scheduled_requires_secret(monkeypatch) -> None:
    conn = _workflow_conn()
    alerts: list[tuple[str, str, str]] = []
    monkeypatch.delenv("OPEN_DATA_REFRESH_SECRET", raising=False)
    monkeypatch.setattr(workflow, "utc_now", _fixed_now)
    monkeypatch.setattr(workflow, "add_alert", lambda c, run_id, level, msg: alerts.append((run_id, level, msg)))

    out = workflow.run_refresh_workflow(conn, trigger="scheduled")
    assert out["status"] == "failed"
    assert "OPEN_DATA_REFRESH_SECRET" in out["errors"][0]
    assert alerts and alerts[0][1] == "error"
    stored = conn.execute("SELECT status FROM workflow_runs").fetchone()[0]
    assert stored == "failed"


def test_workflow_partial_success_with_failures_and_skips(monkeypatch) -> None:
    conn = _workflow_conn()
    sleeps: list[float] = []
    records: list[str] = []
    alerts: list[str] = []
    monkeypatch.setattr(workflow, "utc_now", _fixed_now)
    monkeypatch.setattr(workflow.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(workflow, "record_dataset_version", lambda *_a, **kwargs: records.append(kwargs["dataset_type"]))
    monkeypatch.setattr(workflow, "add_alert", lambda *_a, **_k: alerts.append("alert"))
    monkeypatch.setattr(workflow, "run_geospatial_ingest", lambda *_a, **_k: {"status": "failed", "errors": ["boom"]})
    monkeypatch.setattr(workflow, "run_transit_ingest", lambda *_a, **_k: {"status": "succeeded", "run_id": "t1", "warnings": []})
    monkeypatch.setattr(workflow, "run_census_ingest", lambda *_a, **_k: {"status": "succeeded", "run_id": "c1", "warnings": []})
    monkeypatch.setattr(workflow, "run_assessment_ingest", lambda *_a, **_k: {"status": "succeeded", "run_id": "a1", "warnings": []})
    monkeypatch.setattr(workflow, "run_poi_standardization", lambda *_a, **_k: {"status": "succeeded", "run_id": "p1", "warnings": []})
    monkeypatch.setattr(workflow, "run_deduplication", lambda *_a, **_k: {"status": "succeeded", "run_id": "d1", "warnings": []})

    out = workflow.run_refresh_workflow(conn, trigger="on_demand")
    assert out["status"] == "partial_success"
    assert "geospatial" in out["summary"]["failed"]
    assert "census" in out["summary"]["skipped"]
    assert "assessments" in out["summary"]["skipped"]
    assert "poi_standardization" in out["summary"]["skipped"]
    assert "deduplication" in out["summary"]["skipped"]
    assert "refresh:transit" in records
    assert sleeps
    assert alerts
    assert conn.execute("SELECT COUNT(*) FROM workflow_steps").fetchone()[0] == 6


def test_workflow_retry_then_success(monkeypatch) -> None:
    conn = _workflow_conn()
    attempts = {"geo": 0}
    records: list[str] = []
    sleeps: list[float] = []
    monkeypatch.setattr(workflow, "utc_now", _fixed_now)
    monkeypatch.setattr(workflow.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(workflow, "record_dataset_version", lambda *_a, **kwargs: records.append(kwargs["dataset_type"]))
    monkeypatch.setattr(workflow, "add_alert", lambda *_a, **_k: None)

    def geo(*_a, **_k):
        attempts["geo"] += 1
        if attempts["geo"] == 1:
            return {"status": "failed", "errors": ["first fail"]}
        return {"status": "succeeded", "run_id": "g1", "warnings": []}

    success = {"status": "succeeded", "run_id": "ok", "warnings": []}
    monkeypatch.setattr(workflow, "run_geospatial_ingest", geo)
    monkeypatch.setattr(workflow, "run_transit_ingest", lambda *_a, **_k: success)
    monkeypatch.setattr(workflow, "run_census_ingest", lambda *_a, **_k: success)
    monkeypatch.setattr(workflow, "run_assessment_ingest", lambda *_a, **_k: success)
    monkeypatch.setattr(workflow, "run_poi_standardization", lambda *_a, **_k: success)
    monkeypatch.setattr(workflow, "run_deduplication", lambda *_a, **_k: success)

    out = workflow.run_refresh_workflow(conn, trigger="on_demand")
    assert out["status"] == "succeeded"
    assert any("geospatial succeeded after retry" in item for item in out["warnings"])
    assert attempts["geo"] == 2
    assert len(records) == 6
    assert sleeps


def test_workflow_failed_when_no_promoted(monkeypatch) -> None:
    conn = _workflow_conn()
    monkeypatch.setattr(workflow, "utc_now", _fixed_now)
    monkeypatch.setattr(workflow.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(workflow, "record_dataset_version", lambda *_a, **_k: None)
    monkeypatch.setattr(workflow, "add_alert", lambda *_a, **_k: None)
    monkeypatch.setattr(workflow, "run_geospatial_ingest", lambda *_a, **_k: {"status": "failed", "errors": ["g"]})
    monkeypatch.setattr(workflow, "run_transit_ingest", lambda *_a, **_k: {"status": "failed", "errors": ["t"]})
    monkeypatch.setattr(workflow, "run_census_ingest", lambda *_a, **_k: {"status": "succeeded", "run_id": "c", "warnings": []})
    monkeypatch.setattr(workflow, "run_assessment_ingest", lambda *_a, **_k: {"status": "succeeded", "run_id": "a", "warnings": []})
    monkeypatch.setattr(workflow, "run_poi_standardization", lambda *_a, **_k: {"status": "succeeded", "run_id": "p", "warnings": []})
    monkeypatch.setattr(workflow, "run_deduplication", lambda *_a, **_k: {"status": "succeeded", "run_id": "d", "warnings": []})

    out = workflow.run_refresh_workflow(conn, trigger="on_demand")
    assert out["status"] == "failed"
    assert "geospatial" in out["summary"]["failed"]
    assert "transit" in out["summary"]["failed"]
    assert not out["summary"]["promoted"]


def test_source_fetcher_basic_helpers(tmp_path: Path, monkeypatch) -> None:
    assert sf._bbox_intersects((0, 0, 1, 1), (0.5, 0.5, 2, 2))
    assert not sf._bbox_intersects((0, 0, 1, 1), (2, 2, 3, 3))
    assert sf._passes_attribute_filters({"a": 1}, {"a": "1"})
    assert not sf._passes_attribute_filters({"a": 2}, {"a": "1"})
    assert sf._passes_point_bbox_filter({"lon": 0, "lat": 0}, (-1, -1, 1, 1))
    assert not sf._passes_point_bbox_filter({"a": 1}, (-1, -1, 1, 1))
    assert sf._safe_cache_name("key/1", "seed", ".json").endswith(".json")
    assert sf._normalize_field_name("A B_C-1") == "abc1"

    repo_dir = tmp_path / "repo"
    sources_dir = tmp_path / "sources"
    repo_dir.mkdir()
    sources_dir.mkdir()
    repo_file = repo_dir / "a.json"
    source_file = sources_dir / "b.json"
    repo_file.write_text("{}", encoding="utf-8")
    source_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sf, "REPO_ROOT", repo_dir)
    monkeypatch.setattr(sf, "SOURCES_DIR", sources_dir)
    assert sf._resolve_local_path(str(repo_file)) == repo_file
    assert sf._resolve_local_path("a.json") == repo_file
    assert sf._resolve_local_path("b.json") == source_file
    with pytest.raises(FileNotFoundError):
        sf._resolve_local_path("missing.json")


def test_source_fetcher_remote_fetch_and_field_map(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sf, "SOURCES_DIR", tmp_path)

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self):
            return b'{"k":1}'

    monkeypatch.setattr(sf, "urlopen", lambda *_a, **_k: _Resp())
    fetched = sf._fetch_remote_file("https://example.com/data", "demo", forced_ext=".json")
    assert fetched.exists()
    assert fetched.suffix == ".json"

    record = {"Street Name": "Main", "lat": "53.5"}
    assert sf._lookup_mapped_value(record, "Street Name") == "Main"
    assert sf._lookup_mapped_value(record, "street_name") == "Main"
    assert sf._lookup_mapped_value(record, "street") == "Main"
    assert sf._lookup_mapped_value(record, "none") is None
    mapped = sf._apply_field_map(record, {"street": "street_name", "fixed": "=x"})
    assert mapped["street"] == "Main"
    assert mapped["fixed"] == "x"


def test_source_fetcher_wkt_and_geometry_helpers(monkeypatch) -> None:
    poly = sf._parse_wkt_geometry("POLYGON ((0 0, 1 0, 1 1, 0 0))")
    line = sf._parse_wkt_geometry("LINESTRING (0 0, 1 1)")
    mline = sf._parse_wkt_geometry("MULTILINESTRING ((0 0, 1 1), (2 2, 3 3))")
    mpoly = sf._parse_wkt_geometry("MULTIPOLYGON (((0 0, 1 0, 1 1, 0 0)))")
    assert poly and poly["type"] == "Polygon"
    assert line and line["type"] == "LineString"
    assert mline and mline["type"] == "MultiLineString"
    assert mpoly and mpoly["type"] == "MultiPolygon"
    assert sf._parse_wkt_geometry("") is None
    assert sf._parse_wkt_geometry("POINT (1 2)") is None

    assert sf._flatten_geometry_points({"type": "Point", "coordinates": [1, 2]}) == [[1, 2]]
    assert len(sf._flatten_geometry_points({"type": "LineString", "coordinates": [[1, 2], [3, 4]]})) == 2
    assert len(sf._flatten_geometry_points(poly)) >= 1
    assert len(sf._flatten_geometry_points(mline)) >= 2
    assert sf._flatten_geometry_points(None) == []

    shape = types.SimpleNamespace(points=[(0, 0), (1, 1)], parts=[0], shapeTypeName="POINT")
    assert sf._shape_to_geojson(shape)["type"] == "Point"
    shape2 = types.SimpleNamespace(points=[(0, 0), (1, 1)], parts=[0], shapeTypeName="LINE")
    assert sf._shape_to_geojson(shape2)["type"] in {"LineString", "MultiLineString"}
    shape3 = types.SimpleNamespace(points=[(0, 0), (1, 0), (1, 1), (0, 0)], parts=[0], shapeTypeName="POLYGON")
    assert sf._shape_to_geojson(shape3)["type"] in {"Polygon", "MultiPolygon"}

    assert sf._infer_local_ingestion_technique(Path("a.csv"), "x") == "local_csv"
    assert sf._infer_local_ingestion_technique(Path("a.ivt"), "x") == "local_ivt"
    assert sf._infer_local_ingestion_technique(Path("a.unknown"), "orig") == "orig"

    calls = {"n": 0}

    def _limit(value):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OverflowError
        return value

    monkeypatch.setattr(sf.csv, "field_size_limit", _limit)
    sf._increase_csv_field_limit()


def test_source_fetcher_coordinate_transform_and_transform_geometry(tmp_path: Path, monkeypatch) -> None:
    shp = tmp_path / "x.shp"
    shp.write_bytes(b"fake")
    assert sf._build_coordinate_transformer(shp) is None

    prj = shp.with_suffix(".prj")
    prj.write_text("", encoding="utf-8")
    assert sf._build_coordinate_transformer(shp) is None

    prj.write_text("PROJCS[\"Fake\"]", encoding="utf-8")

    orig_import = __import__

    def _mock_import(name, *args, **kwargs):
        if name == "pyproj":
            raise ImportError("missing")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _mock_import)
    with pytest.raises(RuntimeError):
        sf._build_coordinate_transformer(shp)

    class T:
        def transform(self, x, y):
            return (x + 1, y + 1)

    geom = {"type": "LineString", "coordinates": [[0, 0], [1, 1, 9]]}
    transformed = sf._transform_geometry(geom, T())
    assert transformed["coordinates"][0] == [1, 1]
    assert sf._transform_geometry(None, T()) is None


def test_source_fetcher_normalize_csv_geojson_arcgis(tmp_path: Path) -> None:
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text(
        "lon,lat,kind,wkt\n-113.5,53.5,keep,\"LINESTRING (0 0, 1 1)\"\n-120,40,drop,\"LINESTRING (0 0, 1 1)\"\n",
        encoding="utf-8",
    )
    spec = {"spatial_filter": {"bbox": [-114, 53, -113, 54]}, "attribute_filters": {"kind": "keep"}, "geometry_wkt_field": "wkt"}
    csv_payload = sf._normalize_csv(csv_path, {"kind2": "kind"}, spec)
    assert csv_payload.metadata["row_count"] == 1
    assert csv_payload.metadata["dropped_by_filters"] == 1
    assert csv_payload.records[0]["kind2"] == "keep"

    geojson_path = tmp_path / "rows.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "features": [
                    {"type": "Feature", "properties": {"k": "ok"}, "geometry": {"type": "Point", "coordinates": [-113.5, 53.5]}},
                    {"type": "Feature", "properties": {"k": "drop"}, "geometry": {"type": "LineString", "coordinates": [[-120, 40], [-121, 41]]}},
                    {"type": "Feature", "properties": {"k": "ok"}, "geometry": {"type": "MultiLineString", "coordinates": [[[-113.4, 53.6], [-113.3, 53.7]]]}},
                ]
            }
        ),
        encoding="utf-8",
    )
    geo_spec = {"spatial_filter": {"bbox": [-114, 53, -113, 54]}, "attribute_filters": {"k": "ok"}}
    geo_payload = sf._normalize_geojson(geojson_path, {"kind": "k"}, geo_spec)
    assert geo_payload.metadata["feature_count"] == 3
    assert geo_payload.metadata["row_count"] == 1
    assert geo_payload.records[0]["kind"] == "ok"

    arc_path = tmp_path / "arc.json"
    arc_path.write_text(
        json.dumps(
            {
                "displayFieldName": "arc",
                "currentVersion": 1,
                "features": [
                    {"attributes": {"cat": "ok"}, "geometry": {"x": -113.5, "y": 53.5}},
                    {"attributes": {"cat": "drop"}, "geometry": {"x": -120.0, "y": 40.0}},
                ],
            }
        ),
        encoding="utf-8",
    )
    arc_spec = {"spatial_filter": {"bbox": [-114, 53, -113, 54]}, "attribute_filters": {"cat": "ok"}}
    arc_payload = sf._normalize_arcgis(arc_path, {"kind": "cat"}, arc_spec)
    assert arc_payload.metadata["ingested_from"] == "arcgis_rest_json"
    assert len(arc_payload.records) == 1
    assert arc_payload.records[0]["kind"] == "ok"


def test_source_fetcher_normalize_shapefile_and_resolve_dispatch(tmp_path: Path, monkeypatch) -> None:
    shp_file = tmp_path / "sample.shp"
    shp_file.write_bytes(b"fake")
    zip_file = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("layer.shp", "x")

    class _Shape:
        def __init__(self):
            self.points = [(-113.5, 53.5), (-113.4, 53.6)]
            self.parts = [0]
            self.shapeTypeName = "LINE"
            self.bbox = [-113.6, 53.4, -113.3, 53.7]

    class _ShapeRecord:
        def __init__(self):
            self.shape = _Shape()
            self.record = ["ok"]

    class _Reader:
        fields = [("DeletionFlag", "C", 1, 0), ("kind", "C", 10, 0)]

        def __init__(self, *_a, **kwargs):
            self._encoding = kwargs.get("encoding")

        def iterShapeRecords(self):
            if self._encoding == "utf-8":
                raise UnicodeDecodeError("utf-8", b"x", 0, 1, "bad")
            return [_ShapeRecord()]

    fake_shapefile = types.SimpleNamespace(Reader=_Reader)
    monkeypatch.setitem(sys.modules, "shapefile", fake_shapefile)
    monkeypatch.setattr(sf, "_build_coordinate_transformer", lambda *_a, **_k: None)
    monkeypatch.setattr(sf, "SOURCES_DIR", tmp_path)

    payload = sf._normalize_shapefile(
        zip_file,
        {"category": "kind"},
        {"attribute_filters": {"kind": "ok"}, "spatial_filter": {"bbox": [-114, 53, -113, 54]}},
    )
    assert payload.metadata["ingested_from"] == "shapefile"
    assert payload.records[0]["category"] == "ok"

    with zipfile.ZipFile(tmp_path / "empty.zip", "w") as zf:
        zf.writestr("x.txt", "n")
    with pytest.raises(FileNotFoundError):
        sf._normalize_shapefile(tmp_path / "empty.zip", None, {})

    registry = {"ingestion_technique": "local_json", "local_path": "a.json"}
    monkeypatch.setattr(sf, "get_source_spec", lambda *_a, **_k: registry)
    local = tmp_path / "a.json"
    local.write_text(json.dumps({"metadata": {}, "records": []}), encoding="utf-8")
    monkeypatch.setattr(sf, "_resolve_local_path", lambda *_a, **_k: local)
    assert sf.resolve_source_location("k", {"k": "https://x"}) == ("remote", "https://x")
    assert sf.resolve_source_location("k", {"k": str(local)})[0] == "local"
    assert sf.resolve_source_location("k")[0] == "local"

    registry["ingestion_technique"] = "remote_json"
    registry["remote_url"] = "https://remote"
    assert sf.resolve_source_location("k")[0] == "remote"
    registry["remote_url"] = None
    with pytest.raises(ValueError):
        sf.resolve_source_location("k")
    registry["ingestion_technique"] = "unknown"
    with pytest.raises(ValueError):
        sf.resolve_source_location("k")

    monkeypatch.setattr(sf, "get_source_spec", lambda *_a, **_k: {"ingestion_technique": "local_json", "field_map": None})
    monkeypatch.setattr(sf, "resolve_source_location", lambda *_a, **_k: ("local", str(local)))
    monkeypatch.setattr(sf, "_normalize_json", lambda *_a, **_k: "json")
    monkeypatch.setattr(sf, "_normalize_csv", lambda *_a, **_k: "csv")
    monkeypatch.setattr(sf, "_normalize_geojson", lambda *_a, **_k: "geo")
    monkeypatch.setattr(sf, "_normalize_shapefile", lambda *_a, **_k: "shp")
    assert sf.load_payload_for_source("k") == "json"
    monkeypatch.setattr(sf, "get_source_spec", lambda *_a, **_k: {"ingestion_technique": "remote_csv", "field_map": None})
    monkeypatch.setattr(sf, "resolve_source_location", lambda *_a, **_k: ("remote", "https://x"))
    monkeypatch.setattr(sf, "_fetch_remote_file", lambda *_a, **_k: local)
    assert sf.load_payload_for_source("k") == "csv"
    monkeypatch.setattr(sf, "get_source_spec", lambda *_a, **_k: {"ingestion_technique": "remote_geojson", "field_map": None})
    assert sf.load_payload_for_source("k") == "geo"
    monkeypatch.setattr(sf, "get_source_spec", lambda *_a, **_k: {"ingestion_technique": "remote_shapefile", "field_map": None})
    assert sf.load_payload_for_source("k") == "shp"
    monkeypatch.setattr(sf, "get_source_spec", lambda *_a, **_k: {"ingestion_technique": "local_ivt", "field_map": None})
    monkeypatch.setattr(sf, "resolve_source_location", lambda *_a, **_k: ("remote", "https://x"))
    monkeypatch.setattr(sf, "_fetch_remote_file", lambda *_a, **_k: local)
    with pytest.raises(RuntimeError):
        sf.load_payload_for_source("k")
    monkeypatch.setattr(sf, "get_source_spec", lambda *_a, **_k: {"ingestion_technique": "arcgis_rest_json", "field_map": None})
    monkeypatch.setattr(sf, "_normalize_arcgis", lambda *_a, **_k: "arc")
    assert sf.load_payload_for_source("k") == "arc"
    monkeypatch.setattr(sf, "get_source_spec", lambda *_a, **_k: {"ingestion_technique": "nope", "field_map": None})
    with pytest.raises(ValueError):
        sf.load_payload_for_source("k")
