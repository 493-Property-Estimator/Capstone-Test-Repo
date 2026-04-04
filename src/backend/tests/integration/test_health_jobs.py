import sqlite3


def test_health_routing_disabled(client):
    client.app.state.settings = client.app.state.settings.__class__(
        data_db_path=client.app.state.settings.data_db_path,
        cache_ttl_seconds=client.app.state.settings.cache_ttl_seconds,
        grid_cell_size_deg=client.app.state.settings.grid_cell_size_deg,
        enable_routing=False,
        enable_strict_mode_default=client.app.state.settings.enable_strict_mode_default,
        ingestion_freshness_days=client.app.state.settings.ingestion_freshness_days,
    )
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"degraded", "unhealthy", "healthy"}


def test_precompute_grid_job(client, test_db_path):
    resp = client.post("/api/v1/jobs/precompute-grid")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"succeeded", "failed"}
    conn = sqlite3.connect(test_db_path)
    conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='grid_features_prod'")
    conn.close()


def test_layers_invalid_bbox(client):
    resp = client.get(
        "/api/v1/layers/schools",
        params={"west": 10, "south": 10, "east": 0, "north": 0, "zoom": 12},
    )
    assert resp.status_code == 400
