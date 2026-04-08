import sqlite3

from src.backend.src.jobs import precompute_grid as grid


def _init_grid_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE property_locations_prod (canonical_location_id TEXT, assessment_value REAL, neighbourhood TEXT, lat REAL, lon REAL)"
    )
    conn.execute(
        "CREATE TABLE dataset_versions (version_id TEXT, promoted_at TEXT)"
    )
    conn.execute(
        "INSERT INTO dataset_versions VALUES ('v1', '2026-01-01T00:00:00Z')"
    )
    conn.execute(
        "CREATE TABLE geospatial_prod (raw_category TEXT, lat REAL, lon REAL)"
    )
    conn.execute(
        "CREATE TABLE crime_summary_prod (neighbourhood TEXT, rate_per_100k REAL, incident_count REAL)"
    )
    conn.commit()
    conn.close()


def test_compute_grid_no_rows(tmp_path):
    db_path = tmp_path / "grid.db"
    _init_grid_db(db_path)
    metrics = grid._compute_grid(db_path, 0.01, warnings=[])
    assert metrics["cell_count"] == 0


def test_compute_grid_with_data(tmp_path):
    db_path = tmp_path / "grid_data.db"
    _init_grid_db(db_path)
    grid._ensure_grid_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO property_locations_prod VALUES ('loc1', 20000000, 'Downtown', 53.5461, -113.4938)"
    )
    conn.execute(
        "INSERT INTO geospatial_prod VALUES ('store', 53.5461, -113.4938)"
    )
    conn.execute(
        "INSERT INTO geospatial_prod VALUES ('school', 53.5462, -113.4937)"
    )
    conn.execute(
        "INSERT INTO geospatial_prod VALUES ('park', NULL, NULL)"
    )
    # Geospatial-only cell to exercise empty property bucket.
    conn.execute(
        "INSERT INTO geospatial_prod VALUES ('store', 10.0, 10.0)"
    )
    conn.execute(
        "INSERT INTO crime_summary_prod VALUES ('downtown', 10.0, 5.0)"
    )
    conn.commit()
    conn.close()

    warnings = []
    metrics = grid._compute_grid(db_path, 0.01, warnings)
    assert metrics["cell_count"] >= 1
    assert warnings


def test_compute_grid_geospatial_none(monkeypatch, tmp_path):
    db_path = tmp_path / "grid_none.db"
    _init_grid_db(db_path)
    grid._ensure_grid_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO property_locations_prod VALUES ('loc1', 200000, 'Downtown', 53.5461, -113.4938)"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(grid, "_load_geospatial_rows", lambda _conn: [{"lat": None, "lon": None}])
    metrics = grid._compute_grid(db_path, 0.01, warnings=[])
    assert metrics["cell_count"] >= 1


def test_grid_helpers():
    assert grid._crime_indexes([], {}) == (0.0, 0.0)
    assert grid._crime_indexes([{"neighbourhood": "X"}], {}) == (0.0, 0.0)
    assert grid._crime_indexes([{"neighbourhood": "X"}], {"x": {"rate_idx": 1.0, "sev_idx": 2.0}}) == (1.0, 2.0)
    assert grid._crime_indexes([{"neighbourhood": "Y"}], {"x": {"rate_idx": 1.0, "sev_idx": 2.0}}) == (0.0, 0.0)
    assert grid._school_median_distance([], []) is None
    assert grid._school_median_distance([{"lat": 0, "lon": 0}], []) is None
    distances = grid._school_median_distance(
        [{"lat": 0, "lon": 0}],
        [{"lat": 0, "lon": 1}, {"lat": 0, "lon": 0.1}],
    )
    assert distances is not None
    distances = grid._school_median_distance(
        [{"lat": 0, "lon": 0}],
        [{"lat": 0, "lon": 0.1}, {"lat": 0, "lon": 1}],
    )
    assert distances is not None
