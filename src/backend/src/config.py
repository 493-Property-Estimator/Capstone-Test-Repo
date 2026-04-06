import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    data_db_path: Path
    cache_ttl_seconds: int
    grid_cell_size_deg: float
    enable_routing: bool
    enable_strict_mode_default: bool
    ingestion_freshness_days: int
    search_provider: str
    enabled_layers: tuple[str, ...]
    estimate_time_budget_seconds: float
    estimate_auth_required: bool
    estimate_api_token: str
    routing_provider: str
    health_rate_limit_per_minute: int
    health_rate_limit_window_seconds: float
    memory_high_rss_kb: int
    refresh_scheduler_enabled: bool
    refresh_schedule_seconds: int
    refresh_schedule_min_seconds: int
    search_query_min_chars: int
    search_suggestions_default_limit: int
    search_suggestions_limit_min: int
    search_suggestions_limit_max: int
    search_resolve_match_limit: int
    properties_default_limit: int
    properties_limit_min: int
    properties_limit_max: int
    properties_zoom_min: float
    properties_zoom_max: float
    properties_cluster_zoom_threshold: float


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _parse_enabled_layers(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return tuple()
    items = [item.strip() for item in raw.split(",")]
    return tuple(item for item in items if item)


def _get_setting(
    env: dict[str, str],
    shared: dict[str, str],
    key: str,
    default: Any,
) -> Any:
    if key in env:
        return env[key]
    if key in shared:
        return shared[key]
    return default


def load_settings() -> Settings:
    env = dict(os.environ)
    shared_env_file = Path(env.get("SHARED_ENV_FILE", ".env"))
    shared = _parse_env_file(shared_env_file)

    db_path = _get_setting(env, shared, "DATA_DB_PATH", "src/data_sourcing/open_data.db")
    search_provider = str(_get_setting(env, shared, "SEARCH_PROVIDER", "db")).strip().lower()
    if search_provider not in {"db", "osrm"}:
        search_provider = "db"

    enabled_layers = _parse_enabled_layers(
        str(
            _get_setting(
                env,
                shared,
                "ENABLED_LAYERS",
                "schools,parks,playgrounds,police_stations,municipal_wards,provincial_districts,federal_districts,census_subdivisions,census_boundaries,assessment_zones,assessment_properties",
            )
        )
    )

    return Settings(
        data_db_path=Path(db_path),
        cache_ttl_seconds=int(_get_setting(env, shared, "CACHE_TTL_SECONDS", "900")),
        grid_cell_size_deg=float(_get_setting(env, shared, "GRID_CELL_SIZE_DEG", "0.01")),
        enable_routing=str(_get_setting(env, shared, "ENABLE_ROUTING", "1")) == "1",
        enable_strict_mode_default=str(_get_setting(env, shared, "ENABLE_STRICT_MODE_DEFAULT", "0")) == "1",
        ingestion_freshness_days=int(_get_setting(env, shared, "INGESTION_FRESHNESS_DAYS", "30")),
        search_provider=search_provider,
        enabled_layers=enabled_layers,
        estimate_time_budget_seconds=float(_get_setting(env, shared, "ESTIMATE_TIME_BUDGET_SECONDS", "60.0")),
        estimate_auth_required=str(_get_setting(env, shared, "ESTIMATE_AUTH_REQUIRED", "1")) == "1",
        estimate_api_token=str(_get_setting(env, shared, "ESTIMATE_API_TOKEN", "dev-local-token")),
        routing_provider=str(_get_setting(env, shared, "ROUTING_PROVIDER", "mock_road")).strip().lower(),
        health_rate_limit_per_minute=int(_get_setting(env, shared, "HEALTH_RATE_LIMIT_PER_MINUTE", "120")),
        health_rate_limit_window_seconds=float(_get_setting(env, shared, "HEALTH_RATE_LIMIT_WINDOW_SECONDS", "60.0")),
        memory_high_rss_kb=int(_get_setting(env, shared, "MEMORY_HIGH_RSS_KB", "1200000")),
        refresh_scheduler_enabled=str(_get_setting(env, shared, "REFRESH_SCHEDULER_ENABLED", "0")) == "1",
        refresh_schedule_seconds=int(_get_setting(env, shared, "REFRESH_SCHEDULE_SECONDS", "3600")),
        refresh_schedule_min_seconds=int(_get_setting(env, shared, "REFRESH_SCHEDULE_MIN_SECONDS", "30")),
        search_query_min_chars=int(_get_setting(env, shared, "SEARCH_QUERY_MIN_CHARS", "3")),
        search_suggestions_default_limit=int(_get_setting(env, shared, "SEARCH_SUGGESTIONS_DEFAULT_LIMIT", "5")),
        search_suggestions_limit_min=int(_get_setting(env, shared, "SEARCH_SUGGESTIONS_LIMIT_MIN", "1")),
        search_suggestions_limit_max=int(_get_setting(env, shared, "SEARCH_SUGGESTIONS_LIMIT_MAX", "10")),
        search_resolve_match_limit=int(_get_setting(env, shared, "SEARCH_RESOLVE_MATCH_LIMIT", "5")),
        properties_default_limit=int(_get_setting(env, shared, "PROPERTIES_DEFAULT_LIMIT", "5000")),
        properties_limit_min=int(_get_setting(env, shared, "PROPERTIES_LIMIT_MIN", "100")),
        properties_limit_max=int(_get_setting(env, shared, "PROPERTIES_LIMIT_MAX", "10000")),
        properties_zoom_min=float(_get_setting(env, shared, "PROPERTIES_ZOOM_MIN", "0")),
        properties_zoom_max=float(_get_setting(env, shared, "PROPERTIES_ZOOM_MAX", "25")),
        properties_cluster_zoom_threshold=float(_get_setting(env, shared, "PROPERTIES_CLUSTER_ZOOM_THRESHOLD", "17")),
    )


EDMONTON_BOUNDS = {
    "west": -113.7136,
    "south": 53.3958,
    "east": -113.2714,
    "north": 53.7160,
}
