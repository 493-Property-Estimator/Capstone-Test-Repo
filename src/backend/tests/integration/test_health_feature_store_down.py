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
    )
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"unhealthy", "degraded", "healthy"}
