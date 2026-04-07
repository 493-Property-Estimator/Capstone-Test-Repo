import sqlite3

from src.backend.src.db.queries import (
    search_address_suggestions,
    resolve_address,
    get_location_by_id,
    fetch_geospatial_features,
    get_latest_dataset_version,
)


def test_db_queries(test_db_path):
    suggestions = search_address_suggestions(test_db_path, "123", 5)
    assert suggestions
    matches = resolve_address(test_db_path, "123", limit=1)
    assert matches
    loc = get_location_by_id(test_db_path, "loc_001")
    assert loc
    features = fetch_geospatial_features(test_db_path, "schools", -114, 53, -113, 54)
    assert features
    version = get_latest_dataset_version(test_db_path)
    assert version == "v1"
