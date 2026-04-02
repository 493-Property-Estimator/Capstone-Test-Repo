import sys
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from backend.src.app import app
from backend.src.config import Settings
from backend.src.services.cache import MemoryCache
from backend.src.services.metrics import Metrics


@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    _init_db(db_path)
    return db_path


def _init_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE property_locations_prod (
            canonical_location_id TEXT PRIMARY KEY,
            assessment_value REAL,
            house_number TEXT,
            street_name TEXT,
            neighbourhood TEXT,
            ward TEXT,
            lat REAL,
            lon REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE geospatial_prod (
            dataset_type TEXT,
            entity_id TEXT,
            source_id TEXT,
            name TEXT,
            raw_category TEXT,
            canonical_geom_type TEXT,
            lon REAL,
            lat REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE dataset_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_type TEXT,
            version_id TEXT,
            promoted_at TEXT,
            run_id TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO property_locations_prod (
            canonical_location_id, assessment_value, house_number, street_name,
            neighbourhood, ward, lat, lon
        ) VALUES (
            'loc_001', 410000, '123', 'Main St', 'Downtown', 'Ward 1', 53.5461, -113.4938
        )
        """
    )
    conn.execute(
        """
        INSERT INTO geospatial_prod (
            dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat
        ) VALUES
            ('schools', 'school_001', 'geospatial.school_locations', 'Test School', 'school', 'point', -113.4938, 53.5461),
            ('parks', 'park_001', 'geospatial.parks', 'Test Park', 'park', 'point', -113.4940, 53.5460),
            ('police', 'police_001', 'geospatial.police_stations', 'Police', 'police', 'point', -113.4935, 53.5462),
            ('playgrounds', 'pg_001', 'geospatial.playgrounds', 'Playground', 'playground', 'point', -113.4930, 53.5463)
        """
    )
    conn.execute(
        """
        INSERT INTO dataset_versions (dataset_type, version_id, promoted_at, run_id)
        VALUES ('assessments', 'v1', '2026-03-17T00:00:00Z', 'run-1')
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def client(test_db_path, monkeypatch):
    settings = Settings(
        data_db_path=test_db_path,
        cache_ttl_seconds=3600,
        grid_cell_size_deg=0.01,
        enable_routing=True,
        enable_strict_mode_default=False,
        ingestion_freshness_days=30,
    )
    app.state.settings = settings
    app.state.cache = MemoryCache(settings.cache_ttl_seconds)
    app.state.metrics = Metrics()
    return TestClient(app)
