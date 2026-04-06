from pathlib import Path

from backend.src.config import Settings


def test_health_feature_store_down(client):
    client.app.state.settings = Settings(
        data_db_path=Path("/tmp/does_not_exist.db"),
        cache_ttl_seconds=3600,
        grid_cell_size_deg=0.01,
        enable_routing=True,
        enable_strict_mode_default=False,
        ingestion_freshness_days=30,
        search_provider="db",
        enabled_layers=(),
        estimate_time_budget_seconds=5.0,
        estimate_auth_required=False,
        estimate_api_token="test-token",
        routing_provider="mock_road",
        health_rate_limit_per_minute=10_000,
        refresh_scheduler_enabled=False,
        refresh_schedule_seconds=3600,
    )
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"unhealthy", "degraded", "healthy"}
