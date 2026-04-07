import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.src.app import app
from backend.src.config import Settings
from backend.src.services.cache import MemoryCache
from backend.src.services.metrics import Metrics


@pytest.fixture()
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
            assessment_year INTEGER,
            assessment_value REAL,
            suite TEXT,
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
            point_location TEXT,
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
            lat REAL,
            geometry_json TEXT
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
        CREATE TABLE assessments_prod (
            canonical_location_id TEXT PRIMARY KEY,
            assessment_year INTEGER,
            assessment_value REAL,
            chosen_record_id TEXT,
            confidence REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE poi_prod (
            canonical_poi_id TEXT PRIMARY KEY,
            name TEXT,
            raw_category TEXT,
            raw_subcategory TEXT,
            address TEXT,
            lon REAL,
            lat REAL,
            neighbourhood TEXT,
            source_dataset TEXT,
            source_provider TEXT,
            source_ids_json TEXT,
            source_entity_ids_json TEXT,
            metadata_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE census_prod (
            area_id TEXT,
            geography_level TEXT,
            population INTEGER,
            households INTEGER,
            median_income REAL,
            area_sq_km REAL,
            population_density REAL,
            limited_accuracy INTEGER
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
            canonical_location_id, assessment_year, assessment_value, suite, house_number, street_name,
            neighbourhood_id, neighbourhood, ward, zoning, lot_size, total_gross_area,
            year_built, tax_class, garage, assessment_class_1, assessment_class_2, assessment_class_3,
            point_location, lat, lon
        ) VALUES (
            'loc_001', 2026, 410000, NULL, '123', 'Main St',
            'N1090', 'Downtown', 'Ward 1', 'DC1', 300.0, 175.0,
            2005, 'Residential', 'Y', 'Residential', NULL, NULL,
            NULL, 53.5461, -113.4938
        )
        """
    )
    conn.execute(
        """
        INSERT INTO property_attributes_prod (
            canonical_location_id, bedrooms, bathrooms, bedrooms_estimated, bathrooms_estimated
        ) VALUES ('loc_001', 3, 2, NULL, NULL)
        """
    )
    conn.execute(
        """
        INSERT INTO assessments_prod (
            canonical_location_id, assessment_year, assessment_value, chosen_record_id, confidence
        ) VALUES ('loc_001', 2026, 410000, 'assess_001', 1.0)
        """
    )
    conn.execute(
        """
        INSERT INTO geospatial_prod (
            dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat, geometry_json
        ) VALUES
            ('schools', 'school_001', 'geospatial.school_locations', 'Test School', 'school', 'point', -113.4938, 53.5461, NULL),
            ('parks', 'park_001', 'geospatial.parks', 'Test Park', 'park', 'point', -113.4940, 53.5460, NULL),
            ('police', 'police_001', 'geospatial.police_stations', 'Police', 'police', 'point', -113.4935, 53.5462, NULL),
            ('playgrounds', 'pg_001', 'geospatial.playgrounds', 'Playground', 'playground', 'point', -113.4930, 53.5463, NULL)
        """
    )
    conn.execute(
        """
        INSERT INTO poi_prod (
            canonical_poi_id, name, raw_category, raw_subcategory, address, lon, lat, neighbourhood,
            source_dataset, source_provider, source_ids_json, source_entity_ids_json, metadata_json
        ) VALUES (
            'library_001', 'Test Library', 'Business', 'library', '1 Test Ave', -113.4937, 53.54615, 'Downtown',
            'osm', 'osm', '[]', '[]', '{}'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO dataset_versions (dataset_type, version_id, promoted_at, run_id)
        VALUES ('assessments', 'v1', '2026-03-17T00:00:00Z', 'run-1')
        """
    )
    conn.execute(
        """
        INSERT INTO census_prod (
            area_id, geography_level, population, households, median_income, area_sq_km, population_density, limited_accuracy
        ) VALUES (
            'N1090', 'neighbourhood', 25000, 10000, 75000, 5.0, 5000.0, 0
        )
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
        search_provider="db",
        estimate_time_budget_seconds=5.0,
        estimate_auth_required=False,
        estimate_api_token="test-token",
        routing_provider="mock_road",
        health_rate_limit_per_minute=10_000,
        health_rate_limit_window_seconds=60.0,
        memory_high_rss_kb=1_200_000,
        refresh_scheduler_enabled=False,
        refresh_schedule_seconds=3600,
        refresh_schedule_min_seconds=30,
        search_query_min_chars=3,
        search_suggestions_default_limit=5,
        search_suggestions_limit_min=1,
        search_suggestions_limit_max=10,
        search_resolve_match_limit=5,
        properties_default_limit=5000,
        properties_limit_min=100,
        properties_limit_max=10000,
        properties_zoom_min=0.0,
        properties_zoom_max=25.0,
        properties_cluster_zoom_threshold=17.0,
        enabled_layers=(
            "schools",
            "parks",
            "playgrounds",
            "police_stations",
            "transit_stops",
            "unknown",
        ),
    )
    app.state.settings = settings
    app.state.cache = MemoryCache(settings.cache_ttl_seconds)
    app.state.metrics = Metrics()
    return TestClient(app)
