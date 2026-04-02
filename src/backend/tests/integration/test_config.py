import os

from backend.src.config import load_settings


def test_load_settings_env(monkeypatch, tmp_path):
    db_path = tmp_path / "db.sqlite"
    monkeypatch.setenv("DATA_DB_PATH", str(db_path))
    monkeypatch.setenv("CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("GRID_CELL_SIZE_DEG", "0.05")
    monkeypatch.setenv("ENABLE_ROUTING", "0")
    monkeypatch.setenv("ENABLE_STRICT_MODE_DEFAULT", "1")
    monkeypatch.setenv("INGESTION_FRESHNESS_DAYS", "10")
    settings = load_settings()
    assert settings.data_db_path == db_path
    assert settings.cache_ttl_seconds == 60
    assert settings.grid_cell_size_deg == 0.05
    assert settings.enable_routing is False
    assert settings.enable_strict_mode_default is True
    assert settings.ingestion_freshness_days == 10
