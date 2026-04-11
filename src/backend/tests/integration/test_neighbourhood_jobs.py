from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest


def test_precompute_neighbourhood_model_endpoint_succeeds(client, test_db_path):
    resp = client.post("/api/v1/jobs/precompute-neighbourhood-model")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "succeeded"
    assert "neighbourhood_count" in payload["metrics"]

    conn = sqlite3.connect(test_db_path)
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='neighbourhood_model_prod'"
    ).fetchone()
    assert int(row[0]) == 1
    row = conn.execute("SELECT COUNT(*) FROM neighbourhood_model_prod").fetchone()
    assert int(row[0]) >= 1
    conn.close()


def test_precompute_neighbourhood_model_endpoint_failure(client, monkeypatch):
    from src.backend.src.jobs import precompute_neighbourhood_model as job

    monkeypatch.setattr(job, "_compute_neighbourhood_model", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    resp = client.post("/api/v1/jobs/precompute-neighbourhood-model")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "failed"
    assert any("boom" in item for item in payload["warnings"])


def test_precompute_neighbourhood_model_compute_paths(tmp_path):
    from src.backend.src.jobs import precompute_neighbourhood_model as job

    db_path = tmp_path / "x.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE property_locations_prod (neighbourhood TEXT, assessment_value REAL, lat REAL, lon REAL)"
    )
    conn.commit()
    conn.close()

    job._ensure_neighbourhood_model_table(db_path)
    warnings: list[str] = []
    metrics = job._compute_neighbourhood_model(db_path, warnings)
    assert metrics["neighbourhood_count"] == 0
    assert warnings

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE dataset_versions (dataset_type TEXT, version_id TEXT, promoted_at TEXT)"
    )
    conn.execute(
        "INSERT INTO dataset_versions (dataset_type, version_id, promoted_at) VALUES ('a','v1','2026-01-01')"
    )
    conn.execute(
        "INSERT INTO property_locations_prod (neighbourhood, assessment_value, lat, lon) VALUES ('Downtown', 99999999999, 53.5, -113.5)"
    )
    conn.execute(
        "INSERT INTO property_locations_prod (neighbourhood, assessment_value, lat, lon) VALUES ('Downtown', 'bad', 53.5, -113.5)"
    )
    conn.commit()
    conn.close()

    warnings = []
    metrics = job._compute_neighbourhood_model(db_path, warnings)
    assert metrics["neighbourhood_count"] == 1
    assert metrics["flagged_neighbourhoods"] == 1
    assert metrics["dataset_version"] == "v1"
    assert any("Outlier" in item for item in warnings)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT neighbourhood, average_assessment, median_assessment, property_count FROM neighbourhood_model_prod"
    ).fetchone()
    assert row[0] == "Downtown"
    assert float(row[1]) <= 10_000_000.0
    assert int(row[3]) == 1
    conn.close()


def test_train_neighbourhood_value_models_endpoint_success(client, monkeypatch, test_db_path):
    from src.backend.src.jobs import train_neighbourhood_value_models as job
    import importlib

    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "INSERT INTO dataset_versions (dataset_type, version_id, promoted_at, run_id) VALUES ('a','v2','2026-02-01','r')"
    )
    conn.commit()
    conn.close()

    class FakeNVM:
        @staticmethod
        def train_neighbourhood_models(_rows):
            return [
                SimpleNamespace(
                    neighbourhood="Downtown",
                    model_type="ridge",
                    version="test-ridge",
                    feature_schema={"dummy_columns": ["a"], "numeric": [], "categorical": []},
                    payload={"coefficients": [1], "intercept": 0},
                    metrics={"train_count": 1, "test_count": 1, "r2": 0.0, "mae": 0.0},
                ),
                SimpleNamespace(
                    neighbourhood="Downtown",
                    model_type="rf",
                    version="test-rf",
                    feature_schema={"dummy_columns": ["a"], "numeric": [], "categorical": []},
                    payload={"pickle_b64": "AA=="},
                    metrics={},
                ),
            ]

        @staticmethod
        def serialize_feature_schema(schema):
            import json

            return json.dumps(schema, sort_keys=True)

        @staticmethod
        def serialize_payload(payload):
            import json

            return json.dumps(payload, sort_keys=True)

    original_reload = importlib.reload

    def fake_reload(_mod):
        return FakeNVM

    monkeypatch.setattr(importlib, "reload", fake_reload)

    resp = client.post("/api/v1/jobs/train-neighbourhood-value-models")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "succeeded"
    assert payload["metrics"]["model_count"] == 2
    assert payload["metrics"]["neighbourhood_count"] == 1

    conn = sqlite3.connect(test_db_path)
    row = conn.execute("SELECT COUNT(*) FROM neighbourhood_value_models_prod").fetchone()
    assert int(row[0]) == 2
    conn.close()

    monkeypatch.setattr(importlib, "reload", original_reload)


def test_train_neighbourhood_value_models_endpoint_failure(client, monkeypatch):
    from src.backend.src.jobs import train_neighbourhood_value_models as job

    monkeypatch.setattr(job, "_train_and_store", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    resp = client.post("/api/v1/jobs/train-neighbourhood-value-models")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "failed"
    assert any("boom" in item for item in payload["warnings"])


def test_train_neighbourhood_value_models_endpoint_warns_when_no_models_trained(client, monkeypatch):
    from src.backend.src.jobs import train_neighbourhood_value_models as job
    import importlib

    class FakeNVM:
        @staticmethod
        def train_neighbourhood_models(_rows):
            return []

    monkeypatch.setattr(importlib, "reload", lambda _mod: FakeNVM)

    resp = client.post("/api/v1/jobs/train-neighbourhood-value-models")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "succeeded"
    assert payload["metrics"]["model_count"] == 0
    assert payload["warnings"]


def test_train_and_store_warns_when_no_rows(tmp_path):
    from src.backend.src.jobs import train_neighbourhood_value_models as job

    db_path = tmp_path / "train.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE property_locations_prod (
            canonical_location_id TEXT,
            neighbourhood TEXT,
            assessment_value REAL,
            lot_size REAL,
            total_gross_area REAL,
            year_built INTEGER,
            zoning TEXT,
            tax_class TEXT,
            garage TEXT,
            assessment_class_1 TEXT
        )
        """
    )
    conn.execute("CREATE TABLE property_attributes_prod (canonical_location_id TEXT, bedrooms_estimated REAL, bathrooms_estimated REAL)")
    conn.commit()
    conn.close()

    warnings: list[str] = []
    metrics = job._train_and_store(db_path, warnings)
    assert metrics["model_count"] == 0
    assert warnings
