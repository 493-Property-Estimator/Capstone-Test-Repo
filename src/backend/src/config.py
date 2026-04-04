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
    )


EDMONTON_BOUNDS = {
    "west": -113.7136,
    "south": 53.3958,
    "east": -113.2714,
    "north": 53.7160,
}
