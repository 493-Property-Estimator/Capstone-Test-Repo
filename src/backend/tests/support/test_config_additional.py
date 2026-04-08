from pathlib import Path

from src.backend.src import config


def test_parse_env_file_and_layers(tmp_path):
    missing = config._parse_env_file(tmp_path / "missing.env")
    assert missing == {}

    env_file = tmp_path / "app.env"
    env_file.write_text("A=1\n#comment\nB=2\n", encoding="utf-8")
    parsed = config._parse_env_file(env_file)
    assert parsed["A"] == "1"

    assert config._parse_enabled_layers(None) == tuple()
    assert config._parse_enabled_layers("schools, ,parks") == ("schools", "parks")


def test_load_settings_invalid_search_provider(monkeypatch, tmp_path):
    env_file = tmp_path / "app.env"
    env_file.write_text("SEARCH_PROVIDER=invalid\n", encoding="utf-8")
    monkeypatch.setenv("SHARED_ENV_FILE", str(env_file))
    settings = config.load_settings()
    assert settings.search_provider == "db"
