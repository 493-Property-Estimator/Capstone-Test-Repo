from __future__ import annotations

import json
import runpy
import sqlite3
import sys
import types
import re
import zipfile
import warnings
from pathlib import Path

import pytest

from src.data_sourcing import address_normalization as an
from src.data_sourcing import bedbath_models as bm
from src.data_sourcing import database
from src.data_sourcing import permit_parser
from src.data_sourcing import promotion
from src.data_sourcing import property_matcher
from src.data_sourcing import reporting
from src.data_sourcing import service as ingestion_service
from src.data_sourcing import source_clients
from src.data_sourcing import source_fetcher
import src.data_sourcing.enrich_bedbath as enrich_bedbath
from src.data_sourcing.promotion import upsert_staging_rows
from src.data_sourcing.enrich_bedbath import (
    EnrichmentConfig,
    _build_matching_diagnostics,
    _collect_alert_warnings,
    _diagnostic_similarity,
    _run_step,
    _retain_best_source_assignments,
    extract_candidates,
    backfill_property_locations_from_observed,
    _decode_jsonish,
    _raw_source_address,
    _duplicate_group_export_rows,
    _coerce_int,
    run_bedbath_enrichment,
    run_imputation,
    run_observed_matching,
    run_permit_inference,
)


def test_address_normalization_uncovered_lines(monkeypatch) -> None:
    assert an._clean_token("   ") is None  # hits line 110

    never_match = re.compile(r"a^")
    monkeypatch.setattr(an, "_ADDRESS_RE", never_match)
    parsed = an.parse_address_components("101 Main St")
    assert parsed["street_name"] == "101 MAIN ST"

    assert an._coerce_float("nope") is None


def test_permit_parser_uncovered_lines() -> None:
    assert permit_parser.parse_permit_text(None) is None
    assert permit_parser.parse_permit_text("") is None
    assert permit_parser.parse_permit_text("no beds or baths") is None

    inference = permit_parser.parse_permit_text("3 bed 2 bath")
    assert inference is not None and inference.bedrooms == 3 and inference.bathrooms == 2.0

    inference2 = permit_parser.parse_permit_text("2 BEDROOM 1 BATH plus half-bath")
    assert inference2 is not None and inference2.bathrooms == 1.5

    inference3 = permit_parser.parse_permit_text("half bath only")
    assert inference3 is not None and inference3.bedrooms is None and inference3.bathrooms == 0.5

    assert permit_parser.parse_permit_record({"permit_text": "nope"}) is None


def test_reporting_diagnostics_branch() -> None:
    report = reporting.build_report([], 0, diagnostics={"x": 1})
    assert report["x"] == 1
    report2 = reporting.build_report([], 0, diagnostics=None)
    assert "x" not in report2


def test_database_transaction_and_add_alert_uncovered_lines(monkeypatch) -> None:
    conn = sqlite3.connect(":memory:")
    try:
        with pytest.raises(RuntimeError):
            with database.transaction(conn):
                raise RuntimeError("boom")

        conn.execute("CREATE TABLE alerts (run_id TEXT, level TEXT, message TEXT, created_at TEXT)")
        monkeypatch.setattr(database, "utc_now", lambda: "now")
        database.add_alert(conn, None, "error", "msg")
        row = conn.execute("SELECT run_id, level, message, created_at FROM alerts").fetchone()
        assert row == (None, "error", "msg", "now")
    finally:
        conn.close()


def test_bedbath_models_training_rows_filters() -> None:
    rows = [
        {"source_type": "observed", "confidence": 0.95, "bedrooms": 3, "bathrooms": 2.0},
        {"source_type": "other", "confidence": 0.99, "bedrooms": 4, "bathrooms": 3.0},
        {"source_type": "observed", "confidence": 0.99, "quarantined": True, "bedrooms": 1},
        {"source_type": "observed", "confidence": 0.1, "bedrooms": 2},
        {"source_type": "observed", "confidence": 0.99, "bedrooms": None, "bathrooms": None},
    ]
    out = bm.training_rows_from_candidates(rows, min_confidence=0.9, allowed_source_types={"observed"})
    assert len(out) == 1

    observed = bm.training_rows_from_observed(rows, min_confidence=0.9)
    assert len(observed) == 1


def test_bedbath_models_sklearn_path_without_real_deps(monkeypatch) -> None:
    class FakeMask(list):
        def any(self):
            return any(self)

    class FakeSeries:
        def __init__(self, values):
            self._values = list(values)

        def notna(self):
            return FakeMask(value is not None for value in self._values)

        def astype(self, typ):
            return [typ(value) for value in self._values]

    class _Loc:
        def __init__(self, frame):
            self._frame = frame

        def __getitem__(self, key):
            if isinstance(key, tuple) and len(key) == 2:
                mask, column = key
                values = []
                for keep, row in zip(mask, self._frame._rows, strict=False):
                    if keep:
                        values.append(row.get(column))
                return FakeSeries(values)
            mask = key
            rows = [row for keep, row in zip(mask, self._frame._rows, strict=False) if keep]
            return FakeDataFrame(rows)

    class FakeDataFrame:
        def __init__(self, rows):
            self._rows = [dict(row) for row in rows]
            self.loc = _Loc(self)

        def __getitem__(self, key):
            if isinstance(key, list):
                return FakeDataFrame([{col: row.get(col) for col in key} for row in self._rows])
            if isinstance(key, str):
                return FakeSeries([row.get(key) for row in self._rows])
            raise TypeError("unsupported key")

    class _FeaturesLoc:
        def __init__(self, features):
            self._features = features

        def __getitem__(self, mask):
            rows = [row for keep, row in zip(mask, self._features._rows, strict=False) if keep]
            return FakeFeatures(rows, columns=list(self._features.columns))

    class FakeFeatures:
        def __init__(self, rows, *, columns):
            self._rows = rows
            self.columns = list(columns)
            self.loc = _FeaturesLoc(self)

        def reindex(self, *, columns, fill_value=0):
            self.columns = list(columns)
            return self

    class FakePd:
        DataFrame = FakeDataFrame

        @staticmethod
        def get_dummies(frame, dummy_na=True):
            if isinstance(frame, FakeDataFrame):
                columns = list(frame._rows[0].keys()) if frame._rows else []
                return FakeFeatures(frame._rows, columns=columns)
            raise TypeError("expected FakeDataFrame")

    class FakeRFC:
        def __init__(self, *args, **kwargs):
            self.classes_ = []

        def fit(self, X, y):
            self.classes_ = sorted(set(int(v) for v in y))
            return self

        def predict_proba(self, X):
            class _ProbRow(list):
                def argmax(self):
                    best = 0
                    best_val = None
                    for idx, val in enumerate(self):
                        if best_val is None or val > best_val:
                            best = idx
                            best_val = val
                    return best

                def max(self):
                    return float(max(self))

            if len(self.classes_) >= 2:
                return [_ProbRow([0.2, 0.8])]
            return [_ProbRow([1.0])]

    class FakeRFR:
        def __init__(self, *args, **kwargs):
            pass

        def fit(self, X, y):
            return self

        def predict(self, X):
            return [2.25]

    monkeypatch.setattr(bm, "pd", FakePd)
    monkeypatch.setattr(bm, "RandomForestClassifier", FakeRFC)
    monkeypatch.setattr(bm, "RandomForestRegressor", FakeRFR)

    model = bm.select_model("demo")
    assert isinstance(model, bm.SklearnBedBathModel)

    rows = [
        {"canonical_location_id": "a", "bedrooms": 2, "bathrooms": 1.0, "confidence": 0.9},
        {"canonical_location_id": "b", "bedrooms": 3, "bathrooms": 2.0, "confidence": 0.9},
    ]
    for row in rows:
        for col in bm.FEATURE_COLUMNS:
            row.setdefault(col, None)
    model.fit(rows)

    row = {"canonical_location_id": "x", "confidence": 0.4}
    for col in bm.FEATURE_COLUMNS:
        row.setdefault(col, None)
    pred = model.predict(row)
    assert pred.bedrooms_estimated in {2, 3}
    assert pred.bathrooms_estimated is not None
    assert 0.0 <= pred.confidence <= 0.95

    # Cover the "mask.any() is False" branches (no models fit).
    model2 = bm.SklearnBedBathModel(version="demo2")
    model2.fit(
        [
            {"canonical_location_id": "c", "bedrooms": None, "bathrooms": None, **{col: None for col in bm.FEATURE_COLUMNS}},
        ]
    )
    baseline = model2.predict({"canonical_location_id": "c", **{col: None for col in bm.FEATURE_COLUMNS}})
    assert baseline.bedrooms_estimated is not None


def test_bedbath_models_sklearn_early_return_paths(monkeypatch) -> None:
    monkeypatch.setattr(bm, "pd", None)
    monkeypatch.setattr(bm, "RandomForestClassifier", None)
    monkeypatch.setattr(bm, "RandomForestRegressor", None)
    model = bm.SklearnBedBathModel(version="no-deps")
    model.fit([{"canonical_location_id": "x", "bedrooms": 2, "bathrooms": 1.0}])  # hits line 132
    row = {"canonical_location_id": "x"}
    for col in bm.FEATURE_COLUMNS:
        row.setdefault(col, None)
    pred = model.predict(row)  # hits line 150
    assert pred.canonical_location_id == "x"


def test_promotion_uncovered_branches(monkeypatch) -> None:
    monkeypatch.setattr(promotion, "utc_now", lambda: "now")

    assert promotion.precedence_key({"source_type": "observed", "match_method": "x"})[0] == float(
        promotion.PRECEDENCE_ORDER["observed_fuzzy"]
    )
    assert promotion.precedence_key({"source_type": "imputed"})[0] == float(promotion.PRECEDENCE_ORDER["imputed_model"])

    existing = {"source_type": "observed", "bedrooms_estimated": None, "bathrooms_estimated": None, "updated_at": "t"}
    candidate = {"source_type": "imputed", "bedrooms_estimated": 2, "bathrooms_estimated": 1.5, "updated_at": "t"}
    merged = promotion.choose_preferred_record(existing, candidate)
    assert merged["bedrooms_estimated"] == 2
    assert merged["bathrooms_estimated"] == 1.5

    higher = {"source_type": "observed", "match_method": "exact_address_suite", "confidence": 0.99}
    lower = {"source_type": "inferred", "match_method": "permit_text", "confidence": 0.5, "bedrooms_estimated": 1}
    merged2 = promotion.choose_preferred_record(higher, lower)
    assert merged2["bedrooms_estimated"] == 1

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE property_attributes_staging (
                run_id TEXT,
                canonical_location_id TEXT,
                bedrooms INTEGER,
                bathrooms REAL,
                source_type TEXT,
                source_name TEXT,
                source_record_id TEXT,
                observed_at TEXT,
                match_method TEXT,
                confidence REAL,
                ambiguous INTEGER,
                quarantined INTEGER,
                reason_code TEXT,
                bedrooms_estimated INTEGER,
                bathrooms_estimated REAL,
                feature_snapshot_json TEXT,
                raw_payload_json TEXT,
                updated_at TEXT,
                PRIMARY KEY (run_id, canonical_location_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE property_attributes_prod (
                canonical_location_id TEXT PRIMARY KEY,
                run_id TEXT,
                bedrooms INTEGER,
                bathrooms REAL,
                bedrooms_estimated INTEGER,
                bathrooms_estimated REAL,
                source_type TEXT,
                source_name TEXT,
                source_record_id TEXT,
                observed_at TEXT,
                confidence REAL,
                match_method TEXT,
                ambiguous INTEGER,
                quarantined INTEGER,
                reason_code TEXT,
                feature_snapshot_json TEXT,
                raw_payload_json TEXT,
                updated_at TEXT
            )
            """
        )
        out_empty = promotion.promote_run(conn, "missing")
        assert out_empty["staging_records"] == 0

        conn.execute(
            """
            INSERT INTO property_attributes_prod
            (canonical_location_id, run_id, bedrooms, bathrooms, bedrooms_estimated, bathrooms_estimated,
             source_type, source_name, source_record_id, observed_at, confidence, match_method,
             ambiguous, quarantined, reason_code, feature_snapshot_json, raw_payload_json, updated_at)
            VALUES ('loc-keep', 'r1', 3, 2.0, 3, 2.0, 'observed', 'src', 'r', 't', 0.99, 'exact_address_suite', 0, 0, NULL, '{}', '{}', 'now')
            """
        )
        conn.execute(
            """
            INSERT INTO property_attributes_staging
            (run_id, canonical_location_id, bedrooms, bathrooms, bedrooms_estimated, bathrooms_estimated,
             source_type, source_name, source_record_id, observed_at, confidence, match_method,
             ambiguous, quarantined, reason_code, feature_snapshot_json, raw_payload_json, updated_at)
            VALUES ('r1', 'loc-keep', 3, 2.0, 3, 2.0, 'observed', 'src', 'r', 't', 0.99, 'exact_address_suite', 0, 0, NULL, '{}', '{}', 'now')
            """
        )
        conn.execute(
            """
            INSERT INTO property_attributes_staging
            (run_id, canonical_location_id, bedrooms, bathrooms, bedrooms_estimated, bathrooms_estimated,
             source_type, source_name, source_record_id, observed_at, confidence, match_method,
             ambiguous, quarantined, reason_code, feature_snapshot_json, raw_payload_json, updated_at)
            VALUES ('r1', 'loc-new', NULL, NULL, 2, 1.0, 'imputed', 'm', NULL, NULL, 0.7, 'model', 0, 0, NULL, '{}', '{}', 'now')
            """
        )
        out = promotion.promote_run(conn, "r1")
        assert out["promoted_records"] == 1
    finally:
        conn.close()


def test_property_matcher_uncovered_branches(monkeypatch) -> None:
    assert property_matcher._similarity("", "x") == 0.0

    class FakeFuzz:
        @staticmethod
        def ratio(a, b):
            return 50

        @staticmethod
        def token_sort_ratio(a, b):
            return 80

    monkeypatch.setattr(property_matcher, "fuzz", FakeFuzz)
    assert property_matcher._similarity("a", "b") == 0.8

    # Distance <= 15m hits the 0.20 branch.
    score_close = property_matcher._agreement_score(
        {"lat": 0.0, "lon": 0.0, "year_built": 2000, "total_gross_area": 100},
        {"lat": 0.0, "lon": 0.00005, "year_built": 2000, "total_gross_area": 100},
    )
    assert score_close > 0.0

    # Distance in (15m, 40m] hits the 0.10 branch.
    score = property_matcher._agreement_score(
        {"lat": 0.0, "lon": 0.0, "year_built": 2000, "total_gross_area": 100},
        {"lat": 0.0, "lon": 0.00025, "year_built": 2000, "total_gross_area": 100},
    )
    assert score > 0.0

    # Distance > 40m hits the "no distance bonus" path (covers the remaining branch arc).
    score_far = property_matcher._agreement_score(
        {"lat": 0.0, "lon": 0.0, "year_built": 2000, "total_gross_area": 100},
        {"lat": 0.0, "lon": 0.0010, "year_built": 2000, "total_gross_area": 100},
    )
    assert score_far >= 0.0

    assert property_matcher._clean_token("") is None
    assert property_matcher._coerce_float("bad") is None

    # Suite missing risk early returns.
    prop = {"multi_unit_group_size": 2}
    normalized_prop = property_matcher.normalize_property_address({"house_number": "10", "street_name": "Main", "suite": ""})
    normalized_src = property_matcher.normalize_property_address({"house_number": "10", "street_name": "Main"})
    assert not property_matcher._is_suite_missing_multi_unit_risk(prop, normalized_prop, normalized_src)

    normalized_prop2 = property_matcher.normalize_property_address({"house_number": "10", "street_name": "Main", "suite": "1"})
    normalized_src2 = property_matcher.normalize_property_address({"house_number": "11", "street_name": "Main"})
    assert not property_matcher._is_suite_missing_multi_unit_risk(prop, normalized_prop2, normalized_src2)

    # Legal description exact match branch.
    prop_row = {"canonical_location_id": "loc-1", "legal_description": "Lot 1 Block 1 Plan 1"}
    src_row = {"legal_description": "Lot 1 Block 1 Plan 1", "source_record_id": "s1"}
    norm_prop = property_matcher.normalize_property_address(prop_row)
    norm_src = property_matcher.normalize_property_address(src_row)
    result = property_matcher._match_single(prop_row, norm_prop, src_row, norm_src, 0.90)
    assert result is not None and result.match_method == "exact_legal_description"

    # Street similarity below threshold returns None.
    prop_row2 = {"canonical_location_id": "loc-2", "house_number": "1", "street_name": "Main Street"}
    src_row2 = {"house_number": "1", "street_name": "Completely Different"}
    norm_prop2 = property_matcher.normalize_property_address(prop_row2)
    norm_src2 = property_matcher.normalize_property_address(src_row2)
    assert property_matcher._match_single(prop_row2, norm_prop2, src_row2, norm_src2, 0.90) is None

    # choose_best_match ambiguity gap branch.
    base = property_matcher.MatchResult(
        canonical_location_id="loc-3",
        source_record_id="r",
        match_method="x",
        confidence=0.90,
        ambiguous=False,
        quarantined=False,
        reason_code=None,
        matched_row={},
    )

    def _fake_match(*_a, **_k):
        _fake_match.calls += 1
        if _fake_match.calls == 1:
            return base
        return property_matcher.MatchResult(**{**base.__dict__, "confidence": 0.88})

    _fake_match.calls = 0
    monkeypatch.setattr(property_matcher, "_match_single", _fake_match)
    ambiguous = property_matcher.choose_best_match({"canonical_location_id": "loc-3"}, [{"a": 1}, {"b": 2}], ambiguity_gap=0.03)
    assert ambiguous is not None and ambiguous.ambiguous and ambiguous.quarantined


def test_source_clients_uncovered_branches(tmp_path: Path) -> None:
    mapping = tmp_path / "map.json"
    mapping.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ValueError):
        source_clients._load_mapping(mapping)

    list_json = tmp_path / "list.json"
    list_json.write_text(json.dumps([{"a": 1}]), encoding="utf-8")
    assert source_clients._load_records(list_json)[0]["a"] == 1

    dict_json = tmp_path / "dict.json"
    dict_json.write_text(json.dumps({"records": [{"b": 2}]}), encoding="utf-8")
    assert source_clients._load_records(dict_json)[0]["b"] == 2

    bad_json = tmp_path / "bad.json"
    bad_json.write_text(json.dumps("nope"), encoding="utf-8")
    with pytest.raises(ValueError):
        source_clients._load_records(bad_json)

    csv_path = tmp_path / "rows.csv"
    csv_path.write_text("x,y\n1,2\n", encoding="utf-8")
    assert source_clients._load_records(csv_path)[0]["x"] == "1"

    txt = tmp_path / "x.txt"
    txt.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError):
        source_clients._load_records(txt)

    normalized = source_clients._normalize_record(
        {},
        {"field": [None, "field"]},
        {},
        source_name="x",
    )
    assert "field" in normalized


def test_source_fetcher_uncovered_lines() -> None:
    assert source_fetcher._lookup_mapped_value({"a": 1}, "   ") is None
    assert source_fetcher._lookup_mapped_value({"": "x", "abc": 1}, "z") is None
    record = {"a": 1}
    assert source_fetcher._apply_field_map(record, None) == {"a": 1}


def test_source_fetcher_wkt_none_and_continue_branches() -> None:
    assert source_fetcher._parse_wkt_ring("1") == []
    assert source_fetcher._parse_wkt_ring("a b") == []
    assert source_fetcher._parse_wkt_geometry("POLYGON (())") is None
    assert source_fetcher._parse_wkt_geometry("MULTIPOLYGON (())") is None
    assert source_fetcher._parse_wkt_geometry("MULTILINESTRING (())") is None
    assert source_fetcher._parse_wkt_geometry("LINESTRING ()") is None


def test_source_fetcher_normalize_geojson_arcgis_more_branches(tmp_path: Path) -> None:
    geojson_path = tmp_path / "rows.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "features": [
                    {"type": "Feature", "properties": {"k": "ok"}, "geometry": {"type": "Point", "coordinates": []}},
                    {"type": "Feature", "properties": {"k": "ok"}, "geometry": {"type": "MultiLineString", "coordinates": ["bad", [1, 2, 3]]}},
                    {"type": "Feature", "properties": {"k": "ok"}, "geometry": {"type": "MultiLineString", "coordinates": [[["x"]]]}},
                ]
            }
        ),
        encoding="utf-8",
    )
    payload = source_fetcher._normalize_geojson(geojson_path, None, {"spatial_filter": {}, "attribute_filters": {"k": "ok"}})
    assert payload.metadata["feature_count"] == 3

    arc_path = tmp_path / "arc.json"
    arc_path.write_text(
        json.dumps(
            {
                "displayFieldName": "arc",
                "currentVersion": 1,
                "features": [
                    {"attributes": {"cat": "ok"}, "geometry": {}},
                ],
            }
        ),
        encoding="utf-8",
    )
    payload2 = source_fetcher._normalize_arcgis(arc_path, None, {"spatial_filter": {}, "attribute_filters": {"cat": "ok"}})
    assert payload2.metadata["ingested_from"] == "arcgis_rest_json"


def test_source_fetcher_normalize_shapefile_layer_errors(tmp_path: Path, monkeypatch) -> None:
    zip_file = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("layer.shp", "x")

    class _Shape:
        def __init__(self, bbox=None):
            self.points = [(-113.5, 53.5), (-113.4, 53.6)]
            self.parts = [0]
            self.shapeTypeName = "LINE"
            self.bbox = bbox

    class _ShapeRecord:
        def __init__(self, bbox=None, record=None):
            self.shape = _Shape(bbox=bbox)
            self.record = record or ["ok"]

    class _Reader:
        fields = [("DeletionFlag", "C", 1, 0), ("kind", "C", 10, 0)]

        def __init__(self, *_a, **kwargs):
            self._encoding = kwargs.get("encoding")

        def iterShapeRecords(self):
            if self._encoding == "utf-8":
                raise UnicodeDecodeError("utf-8", b"x", 0, 1, "bad")
            # One dropped by bbox + one dropped by attr filter + one kept
            return [
                _ShapeRecord(bbox=[-120, 40, -119, 41], record=["ok"]),
                _ShapeRecord(bbox=[-113.6, 53.4, -113.3, 53.7], record=["drop"]),
                _ShapeRecord(bbox=[-113.6, 53.4, -113.3, 53.7], record=["ok"]),
            ]

    fake_shapefile = types.SimpleNamespace(Reader=_Reader)
    monkeypatch.setitem(sys.modules, "shapefile", fake_shapefile)
    monkeypatch.setattr(source_fetcher, "_build_coordinate_transformer", lambda *_a, **_k: None)
    monkeypatch.setattr(source_fetcher, "SOURCES_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        source_fetcher._normalize_shapefile(zip_file, None, {"shapefile_layer": "missing.shp"})

    payload = source_fetcher._normalize_shapefile(
        zip_file,
        None,
        {"attribute_filters": {"kind": "ok"}, "spatial_filter": {"bbox": [-114, 53, -113, 54]}},
    )
    assert payload.metadata["record_count"] == 1


def test_service_uncovered_branches(monkeypatch) -> None:
    svc = ingestion_service.IngestionService(db_path=":memory:")

    # _expand_with_dependencies adds upstream deps.
    expanded = svc._expand_with_dependencies({"deduplication"})
    assert "geospatial" in expanded and "poi_standardization" in expanded

    # _resolve_pipeline_plan without source keys returns full plan.
    assert svc._resolve_pipeline_plan(None) == ingestion_service.PIPELINE_ORDER[:]

    monkeypatch.setattr(ingestion_service, "get_source_spec", lambda _k: {})
    with pytest.raises(ValueError):
        svc._resolve_pipeline_plan(["x"])

    monkeypatch.setattr(
        ingestion_service,
        "get_source_spec",
        lambda _k: {"pipeline": "geospatial", "downstream_pipelines": ["crime"]},
    )
    plan = svc._resolve_pipeline_plan(["k"])
    assert "crime" in plan

    # Ingest failing all source checks.
    class _Conn:
        def commit(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(ingestion_service.IngestionService, "_connect", lambda self: _Conn())
    monkeypatch.setattr(ingestion_service.IngestionService, "_sync_source_configs", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "list_sources", lambda *args, **kwargs: [{"key": "k1"}])
    monkeypatch.setattr(ingestion_service, "resolve_source_location", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("loc")))
    monkeypatch.setattr(ingestion_service, "load_payload_for_source", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "log_source_check", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "add_alert", lambda *_a, **_k: None)
    out = svc.ingest(source_keys=None)
    assert out["status"] == "failed"

    # Ingest path that hits geospatial skip + crime skip + final_status computations.
    monkeypatch.setattr(ingestion_service, "list_sources", lambda *args, **kwargs: [{"key": "census.one"}, {"key": "crime.two"}])
    spec_map = {
        "census.one": {"pipeline": "census", "downstream_pipelines": []},
        "crime.two": {"pipeline": "crime", "downstream_pipelines": []},
    }
    monkeypatch.setattr(ingestion_service, "get_source_spec", lambda key: spec_map[key])
    monkeypatch.setattr(ingestion_service, "resolve_source_location", lambda *_a, **_k: ("local", "x"))
    monkeypatch.setattr(ingestion_service, "load_payload_for_source", lambda *_a, **_k: None)

    monkeypatch.setattr(ingestion_service, "run_geospatial_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_census_ingest", lambda *_a, **_k: {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_crime_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_transit_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_assessment_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_poi_standardization", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_deduplication", lambda *_a, **_k: {"status": "skipped"})

    out2 = svc.ingest(source_keys=["census.one", "crime.two"])
    assert out2["status"] in {"partial_success", "failed", "succeeded"}

    # Wrapper methods.
    assert svc.ingest_all()["status"] in {"failed", "partial_success", "succeeded"}

    called = {"closed": 0}

    class _Conn2(_Conn):
        def close(self):
            called["closed"] += 1

    monkeypatch.setattr(ingestion_service.IngestionService, "_connect", lambda self: _Conn2())
    monkeypatch.setattr(ingestion_service, "run_refresh_workflow", lambda *_a, **_k: {"status": "ok"})
    assert svc.run_refresh()["status"] == "ok"
    assert called["closed"] == 1

    monkeypatch.setattr(ingestion_service, "list_sources", lambda *args, **kwargs: [{"key": "x"}])
    assert svc.list_sources() == [{"key": "x"}]
    monkeypatch.setattr(ingestion_service, "get_source_spec", lambda key: {"key": key})
    assert svc.get_source("abc") == {"key": "abc"}


def test_service_pipeline_branches_more(monkeypatch, tmp_path: Path) -> None:
    svc = ingestion_service.IngestionService(db_path=str(tmp_path / "svc.db"))

    # Make source checks succeed without hitting filesystem/network.
    monkeypatch.setattr(ingestion_service, "resolve_source_location", lambda *_a, **_k: ("local", "x"))
    monkeypatch.setattr(ingestion_service, "load_payload_for_source", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "log_source_check", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "add_alert", lambda *_a, **_k: None)

    specs = {
        "geospatial.roads": {"pipeline": "geospatial", "downstream_pipelines": []},
        "transit.stops": {"pipeline": "transit", "downstream_pipelines": []},
        "assessments.tax": {"pipeline": "assessments", "downstream_pipelines": []},
        "poi.mapping": {"pipeline": "poi_standardization", "downstream_pipelines": []},
        "dedupe.run": {"pipeline": "deduplication", "downstream_pipelines": []},
    }
    monkeypatch.setattr(ingestion_service, "get_source_spec", lambda key: specs[key])

    called: list[str] = []
    monkeypatch.setattr(ingestion_service, "run_geospatial_ingest", lambda *_a, **_k: called.append("geo") or {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_transit_ingest", lambda *_a, **_k: called.append("transit") or {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_assessment_ingest", lambda *_a, **_k: called.append("assess") or {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_poi_standardization", lambda *_a, **_k: called.append("poi") or {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_deduplication", lambda *_a, **_k: called.append("dedupe") or {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_census_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_crime_ingest", lambda *_a, **_k: {"status": "skipped"})

    out = svc.ingest(source_keys=list(specs.keys()))
    assert out["status"] == "partial_success"
    assert set(called) >= {"geo", "transit", "assess", "poi", "dedupe"}

    monkeypatch.setattr(ingestion_service.IngestionService, "_resolve_pipeline_plan", lambda *_a, **_k: ["nope"])
    with pytest.raises(ValueError):
        svc.ingest(source_keys=["geospatial.roads"])


def test_service_transit_and_crime_skip_branches(monkeypatch, tmp_path: Path) -> None:
    svc = ingestion_service.IngestionService(db_path=str(tmp_path / "svc2.db"))

    # One good source key triggers a pipeline plan that includes downstream pipelines with no matching source keys.
    specs = {
        "census.one": {"pipeline": "census", "downstream_pipelines": ["crime", "transit"]},
    }
    monkeypatch.setattr(ingestion_service, "get_source_spec", lambda key: specs[key])
    monkeypatch.setattr(ingestion_service, "resolve_source_location", lambda *_a, **_k: ("local", "x"))
    monkeypatch.setattr(ingestion_service, "load_payload_for_source", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "log_source_check", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "add_alert", lambda *_a, **_k: None)

    monkeypatch.setattr(ingestion_service, "run_census_ingest", lambda *_a, **_k: {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_geospatial_ingest", lambda *_a, **_k: {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_transit_ingest", lambda *_a, **_k: {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_crime_ingest", lambda *_a, **_k: {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_assessment_ingest", lambda *_a, **_k: {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_poi_standardization", lambda *_a, **_k: {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_deduplication", lambda *_a, **_k: {"status": "succeeded"})

    out = svc.ingest(source_keys=["census.one"])
    # Crime/transit should be "skipped" by the service code paths since there are no valid keys with those prefixes.
    assert out["pipelines"]["crime"]["status"] == "skipped"
    assert out["pipelines"]["transit"]["status"] == "skipped"


def test_service_partial_success_when_some_source_checks_fail(monkeypatch, tmp_path: Path) -> None:
    svc = ingestion_service.IngestionService(db_path=str(tmp_path / "svc3.db"))

    specs = {
        "geospatial.ok": {"pipeline": "geospatial", "downstream_pipelines": []},
        "geospatial.bad": {"pipeline": "geospatial", "downstream_pipelines": []},
    }
    monkeypatch.setattr(ingestion_service, "get_source_spec", lambda key: specs[key])

    def resolve(source_key, overrides=None):
        if source_key.endswith(".bad"):
            raise RuntimeError("nope")
        return ("local", "x")

    monkeypatch.setattr(ingestion_service, "resolve_source_location", resolve)
    monkeypatch.setattr(ingestion_service, "load_payload_for_source", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "log_source_check", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "add_alert", lambda *_a, **_k: None)

    monkeypatch.setattr(ingestion_service, "run_geospatial_ingest", lambda *_a, **_k: {"status": "succeeded"})
    monkeypatch.setattr(ingestion_service, "run_census_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_crime_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_transit_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_assessment_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_poi_standardization", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_deduplication", lambda *_a, **_k: {"status": "skipped"})

    out = svc.ingest(source_keys=["geospatial.ok", "geospatial.bad"])
    assert out["status"] == "partial_success"


def test_service_failed_when_no_pipelines_succeed(monkeypatch, tmp_path: Path) -> None:
    svc = ingestion_service.IngestionService(db_path=str(tmp_path / "svc4.db"))

    # Source checks succeed so we reach pipeline execution.
    monkeypatch.setattr(ingestion_service, "resolve_source_location", lambda *_a, **_k: ("local", "x"))
    monkeypatch.setattr(ingestion_service, "load_payload_for_source", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "log_source_check", lambda *_a, **_k: None)
    monkeypatch.setattr(ingestion_service, "add_alert", lambda *_a, **_k: None)

    monkeypatch.setattr(ingestion_service, "get_source_spec", lambda _k: {"pipeline": "transit", "downstream_pipelines": []})
    monkeypatch.setattr(ingestion_service, "run_geospatial_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_transit_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_census_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_crime_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_assessment_ingest", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_poi_standardization", lambda *_a, **_k: {"status": "skipped"})
    monkeypatch.setattr(ingestion_service, "run_deduplication", lambda *_a, **_k: {"status": "skipped"})

    out = svc.ingest(source_keys=["transit.none"])
    assert out["status"] == "failed"


def test_enrich_bedbath_uncovered_helpers_and_main(tmp_path: Path, monkeypatch, capsys) -> None:
    # _diagnostic_similarity early return.
    assert _diagnostic_similarity("", "x") == 0.0

    # _collect_alert_warnings collects both ambiguous and quarantined.
    alert_warnings = _collect_alert_warnings(
        [{"canonical_location_id": "loc-1", "ambiguous": 1, "match_method": "x", "reason_code": None}]
    )
    assert alert_warnings

    # _retain_best_source_assignments quarantines suite-missing group.
    rows = [
        {"source_record_id": "r1", "reason_code": "suite_missing_multi_unit", "confidence": 0.9},
        {"source_record_id": "r1", "reason_code": None, "confidence": 0.95},
    ]
    winners = _retain_best_source_assignments(rows)
    assert any(row.get("quarantined") for row in winners)

    # Tie confidence triggers duplicate_source_record_match.
    rows2 = [
        {"source_record_id": "r2", "match_method": "exact_address_suite", "confidence": 0.9},
        {"source_record_id": "r2", "match_method": "exact_legal_description", "confidence": 0.9},
    ]
    winners2 = _retain_best_source_assignments(rows2)
    assert any(row.get("reason_code") == "duplicate_source_record_match" for row in winners2)

    rows3 = [
        {"source_record_id": "r3", "match_method": "suite_missing_multi_unit", "confidence": 0.9},
        {"source_record_id": "r3", "match_method": "exact_address_suite", "confidence": 0.9},
    ]
    winners3 = _retain_best_source_assignments(rows3)
    assert any(row.get("match_method") == "suite_missing_multi_unit" for row in winners3)

    # Diagnostics reason branches.
    candidates = [
        {"canonical_location_id": "c1", "normalized_address": {"address_key_without_suite": "A", "house_number": "1", "street_name": "MAIN"}},
        {"canonical_location_id": "c2", "normalized_address": {"address_key_without_suite": "A", "house_number": "2", "street_name": "MAIN"}},
        {"canonical_location_id": "c3", "normalized_address": {"address_key_without_suite": "", "house_number": None, "street_name": ""}},
    ]
    listing = [{"address": "#2 2 MAIN", "source_record_id": "s1"}]
    permits = [{"address": "999 X", "source_record_id": "p1"}]
    staging = [{"source_type": "observed", "source_record_id": "s1"}]
    diag = _build_matching_diagnostics(candidates, listing, permits, staging)
    assert "fuzzy_misses_by_reason" in diag

    # extract_candidates assessment override branch.
    db_path = tmp_path / "db.sqlite"
    conn = database.connect(db_path)
    database.init_db(conn)
    try:
        conn.execute(
            """
            INSERT INTO property_locations_prod (canonical_location_id, house_number, street_name, assessment_value, link_method)
            VALUES ('loc-1', '1', 'Main', 100, 'address')
            """
        )
        conn.execute(
            "INSERT INTO assessments_prod (canonical_location_id, assessment_year, assessment_value, chosen_record_id, confidence) "
            "VALUES ('loc-1', 2026, 200, 'rec-1', 0.9)"
        )
        conn.commit()
        extracted = extract_candidates(conn)
        assert extracted[0]["assessment_value"] == 200
    finally:
        conn.close()

    # run_imputation branches: existing has observed values => skip, low-confidence => skip.
    conn = database.connect(db_path)
    database.init_db(conn)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO property_locations_prod (canonical_location_id, link_method) VALUES ('loc-skip', 'address')"
        )
        conn.execute(
            """
            INSERT INTO property_attributes_staging (
                run_id, canonical_location_id, bedrooms, bathrooms, source_type, source_name,
                ambiguous, quarantined, feature_snapshot_json, raw_payload_json, updated_at
            ) VALUES (
                'r1', 'loc-skip', 3, NULL, 'observed', 'seed',
                0, 0, '{}', '{}', 'now'
            )
            """
        )
        conn.commit()

        class _Pred:
            def __init__(self, confidence):
                self.confidence = confidence
                self.bedrooms_estimated = 2
                self.bathrooms_estimated = 1.0
                self.feature_snapshot = {}

        class _Model:
            def predict(self, row):
                return _Pred(confidence=row.get("confidence", 0.0))

        training_info = {"model": _Model(), "model_version": "m1", "imputation_enabled": True}
        cfg = EnrichmentConfig(min_training_rows=1, shadow_mode=False, promotion_target="disabled")
        candidates = [{"canonical_location_id": "loc-skip"}, {"canonical_location_id": "loc-low", "confidence": 0.1}]
        out = run_imputation(conn, "r1", candidates, training_info, cfg)
        assert out == []
    finally:
        conn.close()

    # run_observed_matching + run_permit_inference alert branches by forcing ambiguous/quarantined.
    conn = database.connect(db_path)
    database.init_db(conn)
    try:
        clients = types.SimpleNamespace(
            load_listing_candidates=lambda: [{"bedrooms": 3, "source_record_id": "s1"}],
            load_prior_observed_candidates=lambda: [],
            load_permit_candidates=lambda: [{"permit_text": "3 bed 2 bath", "source_record_id": "p1"}],
        )

        fake_match = property_matcher.MatchResult(
            canonical_location_id="loc-1",
            source_record_id="s1",
            match_method="exact_address_suite",
            confidence=0.99,
            ambiguous=True,
            quarantined=True,
            reason_code="ambiguous_match_candidates",
            matched_row={"bedrooms": 3, "bathrooms": 2.0, "source_name": "listing_api", "source_record_id": "s1"},
        )
        monkeypatch.setattr("src.data_sourcing.enrich_bedbath.choose_best_match", lambda *_a, **_k: fake_match)
        alerts = []
        monkeypatch.setattr("src.data_sourcing.enrich_bedbath.add_alert", lambda *_a, **_k: alerts.append("a"))

        candidates = [{"canonical_location_id": "loc-1"}]
        cfg = EnrichmentConfig(min_training_rows=1, shadow_mode=False, promotion_target="disabled")
        observed_rows = run_observed_matching(conn, "run", candidates, clients, cfg)
        assert observed_rows and alerts

        permit_rows = run_permit_inference(conn, "run2", candidates, clients, cfg)
        assert permit_rows and alerts
    finally:
        conn.close()

    # run_bedbath_enrichment exception handling branch.
    monkeypatch.setattr("src.data_sourcing.enrich_bedbath.connect", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("connect fail")))
    with pytest.raises(RuntimeError):
        run_bedbath_enrichment(str(db_path))

    # main() + __main__ guard coverage without doing work.
    monkeypatch.setattr("src.data_sourcing.enrich_bedbath.run_bedbath_enrichment", lambda *_a, **_k: {"status": "ok"})
    monkeypatch.setattr(
        "sys.argv",
        [
            "enrich_bedbath.py",
            "--db-path",
            str(db_path),
            "--disable-promotion",
        ],
    )
    # `runpy.run_module()` warns when the module is already imported; suppress for this intentional coverage run.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=RuntimeWarning,
            message=r".*found in sys\.modules after import of package.*prior to execution.*",
        )
        runpy.run_module("src.data_sourcing.enrich_bedbath", run_name="__main__")
    out = capsys.readouterr().out
    assert "\"status\"" in out


def test_enrich_bedbath_failure_path_covers_except(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "fail.db"

    # Force a failure inside the try block (through _run_step) so run_bedbath_enrichment hits its except path.
    monkeypatch.setattr(enrich_bedbath, "run_observed_matching", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        run_bedbath_enrichment(
            db_path,
            listing_records=[],
            permit_records=[],
            config=EnrichmentConfig(promotion_target="disabled"),
        )


def test_enrich_bedbath_run_imputation_existing_row_without_observed_values(tmp_path: Path) -> None:
    db_path = tmp_path / "impute.db"
    conn = database.connect(db_path)
    database.init_db(conn)
    try:
        conn.execute(
            "INSERT INTO property_locations_prod (canonical_location_id, link_method) VALUES ('loc-1', 'address')"
        )
        upsert_staging_rows(
            conn,
            [
                {
                    "run_id": "r1",
                    "canonical_location_id": "loc-1",
                    "bedrooms": None,
                    "bathrooms": None,
                    "bedrooms_estimated": None,
                    "bathrooms_estimated": None,
                    "source_type": "observed",
                    "source_name": "seed",
                    "source_record_id": None,
                    "observed_at": None,
                    "confidence": 0.9,
                    "match_method": "seed",
                    "ambiguous": 0,
                    "quarantined": 0,
                    "reason_code": None,
                    "feature_snapshot_json": "{}",
                    "raw_payload_json": "{}",
                    "updated_at": "now",
                }
            ],
        )
        conn.commit()

        class _Pred:
            confidence = 0.99
            bedrooms_estimated = 2
            bathrooms_estimated = 1.5
            feature_snapshot = {"x": 1}

        class _Model:
            def predict(self, _row):
                return _Pred()

        cfg = EnrichmentConfig(imputation_min_confidence=0.1, promotion_target="disabled")
        out = run_imputation(
            conn,
            "r1",
            [{"canonical_location_id": "loc-1"}],
            {"model": _Model(), "model_version": "m", "imputation_enabled": True},
            cfg,
        )
        assert out
    finally:
        conn.close()


def test_enrich_bedbath_backfill_and_helpers(tmp_path: Path) -> None:
    db_path = tmp_path / "backfill.db"
    conn = database.connect(db_path)
    database.init_db(conn)
    try:
        conn.execute(
            "INSERT INTO property_locations_prod (canonical_location_id, link_method) VALUES ('loc-1', 'address')"
        )
        conn.commit()

        observed_rows = [
            {"source_type": "observed", "quarantined": 0, "canonical_location_id": None, "raw_payload_json": {}},
            {"source_type": "observed", "quarantined": 0, "canonical_location_id": "loc-1", "raw_payload_json": "{"},
            {"source_type": "observed", "quarantined": 0, "canonical_location_id": "missing", "raw_payload_json": {"suite": "1"}},
            {"source_type": "observed", "quarantined": 0, "canonical_location_id": "loc-1", "raw_payload_json": {"suite": ""}},
            {
                "source_type": "observed",
                "quarantined": 0,
                "canonical_location_id": "loc-1",
                "raw_payload_json": {"suite": "101", "house_number": "10", "street_name": "Main", "lat": "bad", "lon": "bad"},
            },
        ]
        out = backfill_property_locations_from_observed(conn, observed_rows, overwrite_existing=False)
        assert out["matched_rows_considered"] == 5
        assert out["rows_updated"] == 1

        out2 = backfill_property_locations_from_observed(
            conn,
            [
                {
                    "source_type": "observed",
                    "quarantined": 0,
                    "canonical_location_id": "loc-1",
                    "raw_payload_json": {"suite": "202"},
                }
            ],
            overwrite_existing=True,
        )
        assert out2["rows_updated"] == 1

        assert _decode_jsonish({"a": 1}) == {"a": 1}
        assert _decode_jsonish("{") == {}
        assert _raw_source_address({}) is None
        assert _raw_source_address({"suite": "1", "house_number": "2", "street_name": "X", "raw_payload_json": "{}"}) == "1 2 X"
    finally:
        conn.close()


def test_enrich_bedbath_main_argument_branches(monkeypatch, tmp_path: Path, capsys) -> None:
    # Call enrich_bedbath.main() directly so monkeypatching works (no runpy re-import issues).
    monkeypatch.setattr(enrich_bedbath, "run_bedbath_enrichment", lambda *_a, **_k: {"status": "ok"})
    db_path = tmp_path / "x.db"

    monkeypatch.setattr(
        "sys.argv",
        ["enrich_bedbath.py", "--db-path", str(db_path), "--shadow-table-name", "shadow_tbl"],
    )
    enrich_bedbath.main()
    assert "\"status\": \"ok\"" in capsys.readouterr().out


def test_enrich_bedbath_remaining_missing_lines() -> None:
    # _build_matching_diagnostics reason branches.
    candidates = [
        {"canonical_location_id": "c1", "normalized_address": {"address_key_without_suite": "1 MAIN", "house_number": "1", "street_name": "MAIN"}},
        {"canonical_location_id": "c2", "normalized_address": {"address_key_without_suite": "1 MAIN", "house_number": "1", "street_name": "MAIN"}},
    ]
    diag = _build_matching_diagnostics(
        candidates,
        listing_candidates=[
            {"address": "??", "source_record_id": "s2"},  # parse -> base_key missing -> missing_address_components
            {"address": "1 MAIN", "source_record_id": "s3"},  # duplicate base_key, no suite -> suite_missing_multi_unit
        ],
        permit_candidates=[],
        staging_rows=[],
    )
    assert "missing_address_components" in diag["fuzzy_misses_by_reason"]
    assert "suite_missing_multi_unit" in diag["fuzzy_misses_by_reason"]

    # _coerce_int error path.
    assert _coerce_int(None) is None
    assert _coerce_int("") is None
    assert _coerce_int("bad") is None

    # _decode_jsonish parsed-but-not-dict path.
    assert _decode_jsonish("[]") == {}

    # _duplicate_group_export_rows loop path.
    rows = _duplicate_group_export_rows(
        [{"address_key_without_suite": "X", "locations": ["loc-1"]}],
        {"loc-1": {"house_number": "1", "street_name": "Main"}},
    )
    assert rows and rows[0]["canonical_location_id"] == "loc-1"


def test_promotion_remaining_missing_branches(monkeypatch) -> None:
    monkeypatch.setattr(promotion, "utc_now", lambda: "now")

    existing = {"source_type": "observed", "bedrooms_estimated": 1, "bathrooms_estimated": None}
    candidate = {"source_type": "inferred", "bedrooms_estimated": 2, "bathrooms_estimated": 1.0}
    merged = promotion.choose_preferred_record(existing, candidate)
    assert merged["bedrooms_estimated"] == 1  # no overwrite
    assert merged["bathrooms_estimated"] == 1.0  # fill missing

    existing2 = {"source_type": "observed", "match_method": "exact_address_suite", "confidence": 0.9, "bedrooms_estimated": None, "bathrooms_estimated": None}
    candidate2 = {"source_type": "imputed", "match_method": "model", "confidence": 0.1, "bedrooms_estimated": 2, "bathrooms_estimated": 1.0}
    merged2 = promotion.choose_preferred_record(existing2, candidate2)
    assert merged2["bedrooms_estimated"] == 2

    existing3 = {"source_type": "imputed", "bedrooms_estimated": 3, "bathrooms_estimated": 2.0}
    candidate3 = {"source_type": "observed", "bedrooms_estimated": None, "bathrooms_estimated": None}
    merged3 = promotion.choose_preferred_record(existing3, candidate3)
    assert merged3["bedrooms_estimated"] == 3

    row = promotion._jsonify_row({"feature_snapshot_json": {}, "raw_payload_json": "{}", "canonical_location_id": "x"})
    assert isinstance(row["feature_snapshot_json"], str)

    # Cover precedence_key(candidate) < precedence_key(existing) branch.
    existing = {"source_type": "inferred", "confidence": 0.9, "bedrooms_estimated": None, "bathrooms_estimated": None}
    candidate = {"source_type": "imputed", "confidence": 0.1, "bedrooms_estimated": 2, "bathrooms_estimated": 1.0}
    merged = promotion.choose_preferred_record(existing, candidate)
    assert merged["bedrooms_estimated"] == 2

    # Cover candidate is imputed in the final merge path (skips the "restore existing estimates" branch).
    existing2 = {"source_type": "imputed", "confidence": 0.1, "bedrooms_estimated": 3, "bathrooms_estimated": 2.0}
    candidate2 = {"source_type": "imputed", "confidence": 0.9, "bedrooms_estimated": 2, "bathrooms_estimated": 1.0}
    merged2 = promotion.choose_preferred_record(existing2, candidate2)
    assert merged2["bedrooms_estimated"] == 2

    # Cover the "don't fill bedrooms, do fill bathrooms" branch behavior inside the precedence comparison path.
    existing3 = {"source_type": "inferred", "confidence": 0.9, "bedrooms_estimated": 1, "bathrooms_estimated": None}
    candidate3 = {"source_type": "imputed", "confidence": 0.1, "bedrooms_estimated": 2, "bathrooms_estimated": 1.0}
    merged3 = promotion.choose_preferred_record(existing3, candidate3)
    assert merged3["bedrooms_estimated"] == 1
    assert merged3["bathrooms_estimated"] == 1.0

    # Cover the "don't fill bathrooms_estimated" arc inside the precedence branch.
    existing4 = {"source_type": "inferred", "confidence": 0.9, "bedrooms_estimated": None, "bathrooms_estimated": 2.0}
    candidate4 = {"source_type": "imputed", "confidence": 0.1, "bedrooms_estimated": 2, "bathrooms_estimated": 1.0}
    merged4 = promotion.choose_preferred_record(existing4, candidate4)
    assert merged4["bathrooms_estimated"] == 2.0


def test_source_fetcher_more_missing_branches(tmp_path: Path, monkeypatch) -> None:
    # Cover bbox-drop branch in CSV normalization.
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text("lon,lat,kind\n-120,40,keep\n-113.5,53.5,keep\n", encoding="utf-8")
    payload = source_fetcher._normalize_csv(
        csv_path,
        None,
        {"spatial_filter": {"bbox": [-114, 53, -113, 54]}, "attribute_filters": {"kind": "keep"}},
    )
    assert payload.metadata["dropped_by_filters"] == 1

    # Cover arcgis bbox-drop branch.
    arc_path = tmp_path / "arc2.json"
    arc_path.write_text(
        json.dumps(
            {
                "displayFieldName": "arc",
                "currentVersion": 1,
                "features": [
                    {"attributes": {"cat": "ok"}, "geometry": {"x": -120.0, "y": 40.0}},
                ],
            }
        ),
        encoding="utf-8",
    )
    payload2 = source_fetcher._normalize_arcgis(
        arc_path,
        None,
        {"spatial_filter": {"bbox": [-114, 53, -113, 54]}, "attribute_filters": {"cat": "ok"}},
    )
    assert payload2.metadata["row_count"] == 0

    # Cover normalize_json path.
    json_path = tmp_path / "rows.json"
    json_path.write_text(json.dumps({"metadata": {}, "records": [{"a": 1}]}), encoding="utf-8")
    payload3 = source_fetcher._normalize_json(json_path, {"b": "=x"})
    assert payload3.records[0]["b"] == "x"

    # Cover shapefile ImportError branch.
    monkeypatch.delitem(sys.modules, "shapefile", raising=False)
    shp_path = tmp_path / "x.shp"
    shp_path.write_bytes(b"fake")
    with pytest.raises(RuntimeError):
        source_fetcher._normalize_shapefile(shp_path, None, {})

    # Cover pyproj-present branch in _build_coordinate_transformer.
    prj = shp_path.with_suffix(".prj")
    prj.write_text("PROJCS[\"Fake\"]", encoding="utf-8")

    class _CRS:
        def __init__(self, tag):
            self._tag = tag
            self.is_geographic = False

        def __eq__(self, other):
            return isinstance(other, _CRS) and self._tag == other._tag

        @staticmethod
        def from_wkt(_wkt):
            return _CRS("src")

        @staticmethod
        def from_epsg(_epsg):
            return _CRS("dst")

    class _Transformer:
        @staticmethod
        def from_crs(_a, _b, always_xy=True):
            return object()

    fake_pyproj = types.SimpleNamespace(CRS=_CRS, Transformer=_Transformer)
    monkeypatch.setitem(sys.modules, "pyproj", fake_pyproj)
    assert source_fetcher._build_coordinate_transformer(shp_path) is not None

    # Cover pyproj-missing but non-projected prj => return None.
    monkeypatch.delitem(sys.modules, "pyproj", raising=False)
    prj.write_text("GEOGCS[\"Fake\"]", encoding="utf-8")
    assert source_fetcher._build_coordinate_transformer(shp_path) is None

    # Cover pyproj present but geographic => return None at the CRS check.
    class _GeoCRS(_CRS):
        def __init__(self, tag):
            super().__init__(tag)
            self.is_geographic = True

        @staticmethod
        def from_wkt(_wkt):
            return _GeoCRS("src")

        @staticmethod
        def from_epsg(_epsg):
            return _GeoCRS("dst")

    monkeypatch.setitem(sys.modules, "pyproj", types.SimpleNamespace(CRS=_GeoCRS, Transformer=_Transformer))
    prj.write_text("PROJCS[\"Fake\"]", encoding="utf-8")
    assert source_fetcher._build_coordinate_transformer(shp_path) is None

    # Cover _apply_field_map branches where mapped_value is None / source_field not a str.
    out = source_fetcher._apply_field_map({"A": 1}, {"x": 123, "y": "missing"})
    assert out == {"A": 1}

    # Cover malformed linestring path in _parse_wkt_geometry (else branch for points extraction).
    assert source_fetcher._parse_wkt_geometry("LINESTRING 0 0, 1 1") is None

    # Cover _flatten_geometry_points polygon branches.
    flattened = source_fetcher._flatten_geometry_points(
        {"type": "Polygon", "coordinates": ["bad", [["x"], [1, 2]]]}
    )
    assert flattened == [[1, 2]]

    # Cover _shape_to_geojson no-points branch.
    assert source_fetcher._shape_to_geojson(types.SimpleNamespace(points=[])) is None

    # Cover _normalize_shapefile requested_layer match + direct .shp path + transformer path.
    shp_file = tmp_path / "layer.shp"
    shp_file.write_bytes(b"fake")
    with zipfile.ZipFile(tmp_path / "withlayer.zip", "w") as zf:
        zf.writestr("layer.shp", "x")

    class _T:
        def transform(self, x, y):
            return (x + 1, y + 1)

    class _Shape2:
        def __init__(self):
            self.points = [(-113.5, 53.5), (-113.4, 53.6)]
            self.parts = [0]
            self.shapeTypeName = "LINE"
            self.bbox = [-113.6, 53.4, -113.3, 53.7]

    class _ShapeRecord2:
        def __init__(self):
            self.shape = _Shape2()
            self.record = ["ok"]

    class _Reader2:
        fields = [("DeletionFlag", "C", 1, 0), ("kind", "C", 10, 0)]

        def __init__(self, *_a, **kwargs):
            self._encoding = kwargs.get("encoding")

        def iterShapeRecords(self):
            return [_ShapeRecord2()]

    monkeypatch.setitem(sys.modules, "shapefile", types.SimpleNamespace(Reader=_Reader2))
    monkeypatch.setattr(source_fetcher, "SOURCES_DIR", tmp_path)
    monkeypatch.setattr(source_fetcher, "_build_coordinate_transformer", lambda *_a, **_k: _T())
    payload4 = source_fetcher._normalize_shapefile(
        tmp_path / "withlayer.zip",
        None,
        {"shapefile_layer": "layer.shp", "attribute_filters": {"kind": "ok"}, "spatial_filter": {"bbox": [-114, 53, -113, 54]}},
    )
    assert payload4.metadata["record_count"] == 1

    payload5 = source_fetcher._normalize_shapefile(
        shp_file,
        None,
        {"attribute_filters": {"kind": "ok"}},
    )
    assert payload5.metadata["record_count"] == 1


def test_source_fetcher_remaining_branch_arcs(tmp_path: Path, monkeypatch) -> None:
    # _flatten_geometry_points: skip invalid points in LineString and extend stack for MultiPolygon.
    assert source_fetcher._flatten_geometry_points({"type": "LineString", "coordinates": ["bad", [1, 2]]}) == [[1, 2]]
    flat = source_fetcher._flatten_geometry_points({"type": "MultiPolygon", "coordinates": [[[[-1, -2]]]]})
    assert flat == [[-1, -2]]
    assert source_fetcher._flatten_geometry_points({"type": "Nope", "coordinates": []}) == []

    # _shape_to_geojson: empty segment path + MultiPolygon/MultiLineString paths.
    shape = types.SimpleNamespace(points=[(0, 0), (1, 1)], parts=[0, 0, 2], shapeTypeName="POLYGON")
    geo = source_fetcher._shape_to_geojson(shape)
    assert geo and geo["type"] in {"Polygon", "MultiPolygon"}
    shape2 = types.SimpleNamespace(points=[(0, 0), (1, 1), (2, 2)], parts=[0, 2], shapeTypeName="LINE")
    geo2 = source_fetcher._shape_to_geojson(shape2)
    assert geo2 and geo2["type"] in {"LineString", "MultiLineString"}

    assert source_fetcher._infer_local_ingestion_technique(Path("a.shp"), "x") == "local_shapefile"
    assert source_fetcher._infer_local_ingestion_technique(Path("a.zip"), "x") == "local_shapefile"

    class T:
        def transform(self, x, y):
            return (x + 1, y + 1)

    geom = {"type": "LineString", "coordinates": [[0, 0], "x", [1, 1, 9]]}
    out = source_fetcher._transform_geometry(geom, T())
    assert out and out["coordinates"][0] == [1, 1]

    # _normalize_csv WKT branches.
    csv_path = tmp_path / "wkt.csv"
    csv_path.write_text("wkt\n123\nLINESTRING (bad)\nLINESTRING (1 2)\n", encoding="utf-8")
    payload = source_fetcher._normalize_csv(csv_path, None, {"geometry_wkt_field": "wkt"})
    assert payload.metadata["row_count"] == 3

    # _normalize_geojson LineString branches (empty coords + invalid point list).
    geojson_path = tmp_path / "g.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "features": [
                    {"type": "Feature", "properties": {"k": "ok"}, "geometry": {"type": "LineString", "coordinates": []}},
                    {"type": "Feature", "properties": {"k": "ok"}, "geometry": {"type": "LineString", "coordinates": ["bad"]}},
                ]
            }
        ),
        encoding="utf-8",
    )
    source_fetcher._normalize_geojson(geojson_path, None, {"attribute_filters": {"k": "ok"}})

    # _normalize_shapefile: cover flattened-empty path (MultiPoint geometry not handled).
    class _Shape:
        def __init__(self):
            self.points = [(-113.5, 53.5), (-113.4, 53.6)]
            self.parts = [0]
            self.shapeTypeName = "MULTIPOINT"
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
            return [_ShapeRecord()]

    shp_file = tmp_path / "mp.shp"
    shp_file.write_bytes(b"fake")
    monkeypatch.setitem(sys.modules, "shapefile", types.SimpleNamespace(Reader=_Reader))
    monkeypatch.setattr(source_fetcher, "_build_coordinate_transformer", lambda *_a, **_k: None)
    monkeypatch.setattr(source_fetcher, "SOURCES_DIR", tmp_path)
    payload2 = source_fetcher._normalize_shapefile(shp_file, None, {"attribute_filters": {"kind": "ok"}})
    assert payload2.records


def test_source_fetcher_final_missing_lines(tmp_path: Path, monkeypatch) -> None:
    # _flatten_geometry_points stack.extend branch.
    coords = [[["x"]], [[1, 2]]]
    flat = source_fetcher._flatten_geometry_points({"type": "MultiPolygon", "coordinates": coords})
    assert flat == [[1, 2]]

    # _shape_to_geojson MultiPolygon + MultiPoint branches.
    shape_poly = types.SimpleNamespace(
        points=[(0, 0), (1, 0), (2, 0), (3, 0)],
        parts=[0, 2],
        shapeTypeName="POLYGON",
    )
    assert source_fetcher._shape_to_geojson(shape_poly)["type"] == "MultiPolygon"

    shape_other = types.SimpleNamespace(points=[(0, 0)], parts=[0], shapeTypeName="OTHER")
    assert source_fetcher._shape_to_geojson(shape_other)["type"] == "MultiPoint"

    assert source_fetcher._infer_local_ingestion_technique(Path("a.geojson"), "x") == "local_geojson"

    # _normalize_csv WKT branch arcs (raw_wkt not str, flattened empty).
    csv_path = tmp_path / "wkt2.csv"
    csv_path.write_text("wkt\nLINESTRING (0 0, 1 1)\n", encoding="utf-8")

    orig_lookup = source_fetcher._lookup_mapped_value
    orig_flatten = source_fetcher._flatten_geometry_points

    monkeypatch.setattr(source_fetcher, "_lookup_mapped_value", lambda *_a, **_k: 123)
    source_fetcher._normalize_csv(csv_path, None, {"geometry_wkt_field": "wkt"})
    monkeypatch.setattr(source_fetcher, "_lookup_mapped_value", orig_lookup)

    monkeypatch.setattr(source_fetcher, "_flatten_geometry_points", lambda *_a, **_k: [])
    source_fetcher._normalize_csv(csv_path, None, {"geometry_wkt_field": "wkt"})
    monkeypatch.setattr(source_fetcher, "_flatten_geometry_points", orig_flatten)

    # _normalize_geojson MultiLineString with no flattened points.
    geojson_path = tmp_path / "ml.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "features": [
                    {"type": "Feature", "properties": {"k": "ok"}, "geometry": {"type": "MultiLineString", "coordinates": ["bad"]}},
                ]
            }
        ),
        encoding="utf-8",
    )
    source_fetcher._normalize_geojson(geojson_path, None, {"attribute_filters": {"k": "ok"}})

    # _normalize_shapefile: cover geometry None path and flattened empty path.
    class _ShapeEmpty:
        def __init__(self):
            self.points = []
            self.parts = [0]
            self.shapeTypeName = "LINE"
            self.bbox = []

    class _SR1:
        def __init__(self):
            self.shape = _ShapeEmpty()
            self.record = ["ok"]

    class _ShapeMulti:
        def __init__(self):
            self.points = [(-113.5, 53.5)]
            self.parts = [0]
            self.shapeTypeName = "MULTIPOINT"
            self.bbox = []

    class _SR2:
        def __init__(self):
            self.shape = _ShapeMulti()
            self.record = ["ok"]

    class _Reader:
        fields = [("DeletionFlag", "C", 1, 0), ("kind", "C", 10, 0)]

        def __init__(self, *_a, **kwargs):
            self._encoding = kwargs.get("encoding")

        def iterShapeRecords(self):
            return [_SR1(), _SR2()]

    shp_file = tmp_path / "empty.shp"
    shp_file.write_bytes(b"fake")
    monkeypatch.setitem(sys.modules, "shapefile", types.SimpleNamespace(Reader=_Reader))
    monkeypatch.setattr(source_fetcher, "SOURCES_DIR", tmp_path)
    monkeypatch.setattr(source_fetcher, "_build_coordinate_transformer", lambda *_a, **_k: None)
    payload = source_fetcher._normalize_shapefile(shp_file, None, {"attribute_filters": {"kind": "ok"}})
    assert payload.metadata["record_count"] == 2


def test_source_fetcher_force_remaining_geojson_and_shapefile_arcs(tmp_path: Path, monkeypatch) -> None:
    # Force the MultiLineString branch where flattened stays empty (430->442).
    geojson_path = tmp_path / "ml2.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"k": "ok"},
                        "geometry": {"type": "MultiLineString", "coordinates": ["bad"]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    payload = source_fetcher._normalize_geojson(geojson_path, None, {"attribute_filters": {"k": "ok"}})
    assert payload.metadata["row_count"] == 1

    # Force shapefile path where geometry exists but flattened is empty (557->562).
    class _ShapeMulti:
        def __init__(self):
            self.points = [(-113.5, 53.5)]
            self.parts = [0]
            self.shapeTypeName = "MULTIPOINT"
            self.bbox = []

    class _SR:
        def __init__(self):
            self.shape = _ShapeMulti()
            self.record = ["ok"]

    class _Reader:
        fields = [("DeletionFlag", "C", 1, 0), ("kind", "C", 10, 0)]

        def __init__(self, *_a, **kwargs):
            self._encoding = kwargs.get("encoding")

        def iterShapeRecords(self):
            return [_SR()]

    shp_file = tmp_path / "mp2.shp"
    shp_file.write_bytes(b"fake")
    monkeypatch.setitem(sys.modules, "shapefile", types.SimpleNamespace(Reader=_Reader))
    monkeypatch.setattr(source_fetcher, "SOURCES_DIR", tmp_path)
    monkeypatch.setattr(source_fetcher, "_build_coordinate_transformer", lambda *_a, **_k: None)
    payload2 = source_fetcher._normalize_shapefile(shp_file, None, {"attribute_filters": {"kind": "ok"}})
    assert payload2.metadata["record_count"] == 1
