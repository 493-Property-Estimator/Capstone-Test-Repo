import sqlite3
from pathlib import Path

from src.backend.src.db import queries


def _init_full_property_schema(db_path: Path):
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
            legal_description TEXT,
            zoning TEXT,
            lot_size REAL,
            total_gross_area REAL,
            year_built INTEGER,
            neighbourhood_id TEXT,
            neighbourhood TEXT,
            ward TEXT,
            tax_class TEXT,
            garage TEXT,
            assessment_class_1 TEXT,
            assessment_class_2 TEXT,
            assessment_class_3 TEXT,
            assessment_class_pct_1 REAL,
            assessment_class_pct_2 REAL,
            assessment_class_pct_3 REAL,
            lat REAL,
            lon REAL,
            point_location TEXT,
            source_ids_json TEXT,
            record_ids_json TEXT,
            link_method TEXT,
            confidence REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE property_attributes_prod (
            canonical_location_id TEXT,
            bedrooms REAL,
            bathrooms REAL,
            bedrooms_estimated REAL,
            bathrooms_estimated REAL,
            source_type TEXT,
            source_name TEXT,
            confidence REAL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO property_locations_prod (
            canonical_location_id, assessment_year, assessment_value, suite, house_number, street_name,
            legal_description, zoning, lot_size, total_gross_area, year_built, neighbourhood_id, neighbourhood,
            ward, tax_class, garage, assessment_class_1, assessment_class_2, assessment_class_3,
            assessment_class_pct_1, assessment_class_pct_2, assessment_class_pct_3,
            lat, lon, point_location, source_ids_json, record_ids_json, link_method, confidence
        ) VALUES (
            'loc_full', 2026, 410000, NULL, '123', 'Main St',
            NULL, 'DC1', 300.0, 175.0, 2005, 'N1090', 'Downtown',
            'Ward 1', 'Residential', 'Y', 'Residential', NULL, NULL,
            NULL, NULL, NULL,
            53.5461, -113.4938, NULL, '[]', '[]', 'auto', 1.0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO property_attributes_prod (
            canonical_location_id, bedrooms, bathrooms, bedrooms_estimated, bathrooms_estimated,
            source_type, source_name, confidence
        ) VALUES ('loc_full', 3, 2, NULL, NULL, 'manual', 'test', 1.0)
        """
    )
    conn.commit()
    conn.close()


def test_db_queries(test_db_path):
    suggestions = queries.search_address_suggestions(test_db_path, "123", 5)
    assert suggestions
    matches = queries.resolve_address(test_db_path, "123", limit=1)
    assert matches
    loc = queries.get_location_by_id(test_db_path, "loc_001")
    assert loc
    features = queries.fetch_geospatial_features(test_db_path, "schools", -114, 53, -113, 54)
    assert features
    version = queries.get_latest_dataset_version(test_db_path)
    assert version == "v1"


def test_db_queries_empty_and_decode(tmp_path):
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE property_locations_prod (canonical_location_id TEXT, house_number TEXT, street_name TEXT, neighbourhood TEXT, lat REAL, lon REAL, ward TEXT, assessment_value REAL)"
    )
    conn.execute("CREATE TABLE dataset_versions (version_id TEXT, promoted_at TEXT)")
    conn.commit()
    conn.close()

    assert queries.search_address_suggestions(db_path, "", 5) == []
    assert queries.resolve_address(db_path, "", limit=1) == []
    assert queries.get_location_by_id(db_path, "missing") is None
    assert queries.resolve_coordinates_to_location(db_path, 0, 0) is None
    assert queries.get_latest_dataset_version(db_path) is None

    geometry = queries.decode_geometry({"lon": 1, "lat": 2})
    assert geometry["coordinates"] == [1, 2]
    geometry = queries.decode_geometry({"geometry_json": "bad", "lon": 1, "lat": 2})
    assert geometry["type"] == "Point"
    geometry = queries.decode_geometry({"geometry_json": "{\"type\": null}", "lon": 1, "lat": 2})
    assert geometry["type"] == "Point"
    geometry = queries.decode_geometry({"geometry_json": "{\"type\": \"Point\", \"coordinates\": [1, 2]}", "lon": 1, "lat": 2})
    assert geometry["type"] == "Point"
    assert geometry["coordinates"] == [1, 2]
    assert queries._format_address({"house_number": None, "street_name": "Main"}) == "Main"


def test_fetch_geospatial_features_special_layers(test_db_path):
    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "CREATE TABLE canonical_entities_prod (canonical_id TEXT, name TEXT, canonical_category TEXT, lon REAL, lat REAL)"
    )
    conn.execute(
        "INSERT INTO canonical_entities_prod VALUES ('biz_1', 'Biz', 'Commerce', -113.5, 53.5)"
    )
    conn.execute(
        "INSERT INTO canonical_entities_prod VALUES ('green_1', 'Park', 'Green Space', -113.5, 53.5)"
    )
    conn.execute(
        "CREATE TABLE transit_prod (transit_type TEXT, entity_id TEXT, source_id TEXT, stop_name TEXT, name TEXT, stop_lon REAL, stop_lat REAL)"
    )
    conn.execute(
        "INSERT INTO transit_prod VALUES ('stops', 'stop_1', 'src', 'Stop', 'Stop', -113.5, 53.5)"
    )
    conn.execute(
        "CREATE TABLE road_segments_prod (segment_id TEXT, source_id TEXT, official_road_name TEXT, segment_name TEXT, road_id TEXT, roadway_category TEXT, segment_type TEXT, center_lon REAL, center_lat REAL, geometry_json TEXT)"
    )
    conn.execute(
        "INSERT INTO road_segments_prod VALUES ('r1', 'src', 'Road', NULL, 'r1', 'road', NULL, -113.5, 53.5, '{}')"
    )
    conn.commit()
    conn.close()

    assert queries.fetch_geospatial_features(test_db_path, "businesses", -114, 53, -113, 54)
    assert queries.fetch_geospatial_features(test_db_path, "green_space", -114, 53, -113, 54)
    assert queries.fetch_geospatial_features(test_db_path, "transit_stops", -114, 53, -113, 54)
    assert queries.fetch_geospatial_features(test_db_path, "roads", -114, 53, -113, 54)


def test_fetch_geospatial_features_boundary_and_matches_layer(test_db_path):
    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "INSERT INTO geospatial_prod (dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat, geometry_json) VALUES ('municipal_wards', 'ward1', 'geospatial.municipal_wards', 'Ward', 'ward', 'Polygon', -113.5, 53.5, '{}')"
    )
    conn.commit()
    conn.close()

    features = queries.fetch_geospatial_features(test_db_path, "municipal_wards", -114, 53, -113, 54)
    assert features

    assert queries._matches_layer("schools", {"source_id": "geospatial.school_locations", "raw_category": ""}) is True
    assert queries._matches_layer("parks", {"source_id": "", "raw_category": "park"}) is True
    assert queries._matches_layer("unknown", {"dataset_type": "schools", "raw_category": ""}) is False


def test_property_location_queries(tmp_path):
    db_path = tmp_path / "props.db"
    _init_full_property_schema(db_path)

    rows = queries.fetch_property_locations_bbox(db_path, -114, 53, -113, 54, limit=10, offset=0)
    assert rows
    detail = queries.fetch_property_location_detail(db_path, "loc_full")
    assert detail
    assert queries.fetch_property_location_detail(db_path, "missing") is None
