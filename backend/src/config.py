import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_db_path: Path
    cache_ttl_seconds: int
    grid_cell_size_deg: float
    enable_routing: bool
    enable_strict_mode_default: bool
    ingestion_freshness_days: int


def load_settings() -> Settings:
    db_path = os.environ.get("DATA_DB_PATH", "src/data_sourcing/open_data.db")
    return Settings(
        data_db_path=Path(db_path),
        cache_ttl_seconds=int(os.environ.get("CACHE_TTL_SECONDS", "900")),
        grid_cell_size_deg=float(os.environ.get("GRID_CELL_SIZE_DEG", "0.01")),
        enable_routing=os.environ.get("ENABLE_ROUTING", "1") == "1",
        enable_strict_mode_default=os.environ.get("ENABLE_STRICT_MODE_DEFAULT", "0") == "1",
        ingestion_freshness_days=int(os.environ.get("INGESTION_FRESHNESS_DAYS", "30")),
    )


EDMONTON_BOUNDS = {
    "west": -113.7134,
    "south": 53.3385,
    "east": -113.2784,
    "north": 53.7152,
}
