from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import json
import sqlite3

from src.backend.src.api import ingestion_jobs as jobs


def _upload_payload(dataset_type: str, filename: str, body: bytes):
    return {
        "source_name": "uploaded_source",
        "dataset_type": dataset_type,
        "trigger": "on_demand",
        "validate_only": "0",
        "overwrite": "1",
    }, {"file": (filename, BytesIO(body), "application/octet-stream")}


def _schema_body(dataset_type: str) -> bytes:
    if dataset_type == "assessment_properties":
        return b"Assessed Value,Latitude,Longitude\n410000,53.54,-113.49\n"
    if dataset_type == "transit_stops":
        return b"stop_id,stop_name,stop_lat,stop_lon\n100,Main,53.54,-113.49\n"
    return b"name,latitude,longitude\nSample,53.54,-113.49\n"


def test_parse_bool_variants():
    assert jobs._parse_bool(True) is True
    assert jobs._parse_bool(False) is False
    assert jobs._parse_bool("1") is True
    assert jobs._parse_bool("yes") is True
    assert jobs._parse_bool("0", default=True) is False
    assert jobs._parse_bool("off", default=True) is False
    assert jobs._parse_bool("maybe", default=True) is True
    assert jobs._parse_bool(None, default=True) is True


def test_normalize_service_status_variants():
    assert jobs._normalize_service_status("succeeded") == "success"
    assert jobs._normalize_service_status("partial_success") == "partial"
    assert jobs._normalize_service_status("failed") == "failed"
    assert jobs._normalize_service_status(None) == "failed"


def test_safe_int_and_derive_helpers():
    assert jobs._safe_int("5") == 5
    assert jobs._safe_int("-3") == 0
    assert jobs._safe_int("not-a-number") == 0

    ingested_meta, skipped_meta = jobs._derive_counts_from_metadata(
        {
            "counts": {"raw": 10, "normalized": 8, "linked": 6, "unlinked": 1, "ambiguous": 2},
            "row_count": 3,
            "datasets": [{"row_count": 4}, "skip-me"],
        }
    )
    assert ingested_meta == 13
    assert skipped_meta == 5

    assert jobs._derive_counts_from_pipeline_payload("no-dict") == (0, 0, 0)
    ingested_pipe, skipped_pipe, errors_pipe = jobs._derive_counts_from_pipeline_payload(
        {
            "counts": {"raw": 10, "normalized": 8, "linked": 6, "unlinked": 1, "ambiguous": 2},
            "datasets": [{"row_count": 2}, "ignore"],
            "errors": ["e1", "e2"],
        }
    )
    assert ingested_pipe == 8
    assert skipped_pipe == 5
    assert errors_pipe == 2


def test_validate_schema_from_csv_and_json(tmp_path):
    csv_path = tmp_path / "schools.csv"
    csv_path.write_text("name,latitude,longitude\nS,53.54,-113.49\n", encoding="utf-8")
    valid_csv, missing_csv = jobs._validate_dataset_schema("schools", csv_path, "csv")
    assert valid_csv is True
    assert missing_csv == []

    bad_csv = tmp_path / "schools_bad.csv"
    bad_csv.write_text("title,x,y\nS,1,2\n", encoding="utf-8")
    valid_bad_csv, missing_bad_csv = jobs._validate_dataset_schema("schools", bad_csv, "csv")
    assert valid_bad_csv is False
    assert missing_bad_csv

    geojson_path = tmp_path / "parks.geojson"
    geojson_path.write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[-113.49,53.54]},"properties":{"official_name":"Park A"}}]}',
        encoding="utf-8",
    )
    valid_geo, missing_geo = jobs._validate_dataset_schema("parks", geojson_path, "geojson")
    assert valid_geo is True
    assert missing_geo == []


def test_validate_schema_parse_failure(tmp_path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{", encoding="utf-8")
    valid, missing = jobs._validate_dataset_schema("schools", bad_json, "json")
    assert valid is False
    assert missing and "could not parse file" in missing[0]


def test_ingestion_job_success_status(client, monkeypatch):
    def fake_ingest(self, source_keys=None, trigger="manual", source_overrides=None, taxonomy_version="v1", mapping_version="v1"):
        assert source_keys == ["geospatial.school_locations"]
        assert trigger == "on_demand"
        assert source_overrides
        return {
            "status": "succeeded",
            "pipeline_order": ["geospatial"],
            "pipelines": {
                "geospatial": {
                    "status": "succeeded",
                    "row_count": 7,
                    "errors": [],
                }
            },
        }

    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.IngestionService.ingest", fake_ingest)

    data, files = _upload_payload("schools", "schools.csv", _schema_body("schools"))
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["dataset_type"] == "schools"
    assert payload["source_key"] == "geospatial.school_locations"
    assert payload["stats"]["ingested"] == 7
    assert payload["stats"]["skipped"] == 0
    assert payload["stats"]["errors"] == 0


def test_ingestion_job_partial_status(client, monkeypatch):
    def fake_ingest(self, *_args, **_kwargs):
        return {
            "status": "partial_success",
            "pipeline_order": ["geospatial"],
            "pipelines": {
                "geospatial": {
                    "status": "failed",
                    "row_count": 2,
                    "errors": ["bad_row"],
                }
            },
        }

    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.IngestionService.ingest", fake_ingest)

    data, files = _upload_payload("parks", "parks.geojson", b'{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[-113.49,53.54]},"properties":{"name":"Park A"}}]}')
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["stats"]["ingested"] == 2
    assert payload["stats"]["errors"] >= 1


def test_ingestion_job_service_failed_status(client, monkeypatch):
    def fake_ingest(self, *_args, **_kwargs):
        return {"status": "failed", "pipeline_order": [], "pipelines": {}}

    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.IngestionService.ingest", fake_ingest)

    data, files = _upload_payload("assessment_properties", "assessment.csv", _schema_body("assessment_properties"))
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_ingestion_job_rejects_wrong_datatype(client):
    data, files = _upload_payload("transit_stops", "stops.parquet", b"test")
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)

    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert "Wrong datatype" in detail.get("msg", "")


def test_ingestion_job_rejects_unsupported_dataset(client):
    data, files = _upload_payload("libraries", "libraries.csv", b"name,lat,lon\nL,53.54,-113.49\n")
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)

    assert response.status_code == 400
    assert "Unsupported dataset_type" in response.json().get("detail", {}).get("msg", "")


def test_ingestion_job_rejects_wrong_kind_schema(client):
    data, files = _upload_payload("schools", "schools.csv", b"title,x,y\nNope,1,2\n")
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)

    assert response.status_code == 400
    assert "File kind cannot be ingested" in response.json().get("detail", {}).get("msg", "")


def test_ingestion_job_validate_only(client, monkeypatch):
    called = {"value": False}

    def fake_load_payload(source_key, overrides=None, registry_path=None):
        called["value"] = True
        assert source_key == "geospatial.playgrounds"
        assert overrides and source_key in overrides
        return object()

    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.load_payload_for_source", fake_load_payload)

    data, files = _upload_payload("playgrounds", "playgrounds.json", b'{"name":"Playground","lat":53.54,"lon":-113.49}')
    data["validate_only"] = "1"
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["validate_only"] is True
    assert called["value"] is True


def test_ingestion_job_validate_only_failure(client, monkeypatch):
    def fake_load_payload(_source_key, _overrides=None, _registry_path=None):
        raise ValueError("bad payload")

    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.load_payload_for_source", fake_load_payload)

    data, files = _upload_payload("playgrounds", "playgrounds.json", b'{"name":"Playground","lat":53.54,"lon":-113.49}')
    data["validate_only"] = "1"
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)

    assert response.status_code == 400
    assert "Ingestion could not be completed" in response.json().get("detail", {}).get("msg", "")


def test_extract_record_keys_empty_json(tmp_path):
    empty_path = tmp_path / "empty.json"
    empty_path.write_text("{}", encoding="utf-8")
    keys = jobs._extract_record_keys_from_path(empty_path, "json")
    assert isinstance(keys, set)


def test_extract_record_keys_csv_with_no_headers(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")
    keys = jobs._extract_record_keys_from_path(csv_path, "csv")
    assert keys == set()


def test_normalize_field_name():
    assert jobs._normalize_field_name(" Stop Name ") == "stopname"
    assert jobs._normalize_field_name(None) == ""


def test_validate_schema_with_missing_file_parse(tmp_path):
    path = Path(tmp_path / "bad.geojson")
    path.write_text("not json", encoding="utf-8")
    valid, missing = jobs._validate_dataset_schema("parks", path, "geojson")
    assert valid is False
    assert missing


def test_collect_ingestion_stats_from_fallback_payload():
    result = {
        "pipelines": {
            "geospatial": {
                "status": "failed",
                "row_count": 3,
                "errors": ["x"],
            },
            "transit": {
                "status": "skipped",
                "row_count": 0,
                "errors": [],
            },
        }
    }
    stats = jobs._collect_ingestion_stats("/tmp/nonexistent.db", result)
    assert stats == {"ingested": 3, "skipped": 1, "errors": 2}


def test_collect_ingestion_stats_from_run_logs(tmp_path):
    db = tmp_path / "stats.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE run_logs (
            run_id TEXT PRIMARY KEY,
            story TEXT,
            trigger_type TEXT,
            status TEXT,
            started_at TEXT,
            completed_at TEXT,
            warnings_json TEXT,
            errors_json TEXT,
            metadata_json TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO run_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-a",
            "017",
            "on_demand",
            "succeeded",
            "",
            "",
            "[]",
            json.dumps(["e1", "e2"]),
            json.dumps({"row_count": 5}),
        ),
    )
    conn.commit()
    conn.close()

    result = {"pipelines": {"geospatial": {"run_id": "run-a", "status": "succeeded"}}}
    stats = jobs._collect_ingestion_stats(db, result)
    assert stats == {"ingested": 5, "skipped": 0, "errors": 2}


def test_collect_ingestion_stats_missing_runs_and_bad_json(tmp_path):
    db = tmp_path / "stats_bad.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE run_logs (
            run_id TEXT PRIMARY KEY,
            story TEXT,
            trigger_type TEXT,
            status TEXT,
            started_at TEXT,
            completed_at TEXT,
            warnings_json TEXT,
            errors_json TEXT,
            metadata_json TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO run_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-a",
            "017",
            "on_demand",
            "succeeded",
            "",
            "",
            "[]",
            "not-json",
            "{",
        ),
    )
    conn.execute(
        "INSERT INTO run_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-b",
            "017",
            "on_demand",
            "succeeded",
            "",
            "",
            "[]",
            "[]",
            "[]",
        ),
    )
    conn.commit()
    conn.close()

    result = {
        "pipelines": {
            "geo": {"run_id": "run-a", "status": "succeeded", "row_count": 3, "errors": []},
            "geo2": {"run_id": "run-b", "status": "succeeded", "row_count": 0, "errors": []},
            "other": {"run_id": "run-missing", "status": "failed", "row_count": 1, "errors": ["x"]},
        }
    }
    stats = jobs._collect_ingestion_stats(db, result)
    assert stats["ingested"] >= 1
    assert stats["errors"] >= 2


def test_collect_ingestion_stats_sqlite_error(monkeypatch):
    def bad_connect(*_args, **_kwargs):
        raise sqlite3.Error("db down")

    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.sqlite3.connect", bad_connect)
    result = {"pipelines": {"geospatial": {"run_id": "run-a", "row_count": 4, "status": "succeeded", "errors": []}}}
    stats = jobs._collect_ingestion_stats("/tmp/x.db", result)
    assert stats == {"ingested": 4, "skipped": 0, "errors": 0}


def test_extract_record_keys_empty_and_scalar_json(tmp_path):
    empty_txt = tmp_path / "empty.txt"
    empty_txt.write_text("", encoding="utf-8")
    assert jobs._extract_record_keys_from_path(empty_txt, "json") == set()

    scalar_json = tmp_path / "scalar.json"
    scalar_json.write_text("123", encoding="utf-8")
    assert jobs._extract_record_keys_from_path(scalar_json, "json") == set()

    list_json = tmp_path / "list.json"
    list_json.write_text("[]", encoding="utf-8")
    assert jobs._extract_record_keys_from_path(list_json, "json") == set()


def test_validate_dataset_schema_no_fields(tmp_path):
    empty_payload = tmp_path / "empty.json"
    empty_payload.write_text("[]", encoding="utf-8")
    valid, missing = jobs._validate_dataset_schema("schools", empty_payload, "json")
    assert valid is False
    assert missing == ["no readable fields found in uploaded file"]


def test_ingestion_job_direct_missing_file_rejected():
    async def run():
        request = SimpleNamespace(
            state=SimpleNamespace(request_id="r-1"),
            app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(data_db_path=Path("x.db")))),
        )
        try:
            await jobs.ingest_uploaded_dataset(
                request=request,
                source_name="source",
                dataset_type="schools",
                trigger="on_demand",
                validate_only=False,
                overwrite=True,
                file=None,
            )
            assert False, "Expected HTTPException"
        except jobs.HTTPException as exc:
            assert exc.status_code == 400
            assert "Data file is required" in exc.detail["msg"]

    import asyncio

    asyncio.run(run())


def test_ingestion_job_unlink_oserror_branch(client, monkeypatch):
    class FakeTempPath:
        def __init__(self, _value):
            self.value = _value

        def __str__(self):
            return self.value

        def exists(self):
            return True

        def unlink(self):
            raise OSError("cannot unlink")

    class FakeNamedTempFile:
        def __init__(self, *args, **kwargs):
            self.name = "/tmp/fake-upload.csv"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, _chunk):
            return None

    def fake_path(value):
        if value == "/tmp/fake-upload.csv":
            return FakeTempPath(value)
        return Path(value)

    def fake_ingest(self, *_args, **_kwargs):
        return {"status": "succeeded", "pipeline_order": [], "pipelines": {}}

    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.tempfile.NamedTemporaryFile", FakeNamedTempFile)
    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.Path", fake_path)
    monkeypatch.setattr("src.backend.src.api.ingestion_jobs.IngestionService.ingest", fake_ingest)

    data, files = _upload_payload("schools", "schools.csv", _schema_body("schools"))
    response = client.post("/api/v1/jobs/ingest", data=data, files=files)
    assert response.status_code == 400
