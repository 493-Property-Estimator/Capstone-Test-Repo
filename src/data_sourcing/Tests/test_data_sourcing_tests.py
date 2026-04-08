from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path

import pytest

from data_sourcing import cli
from data_sourcing.source_loader import load_json_source, require_fields
from data_sourcing.source_registry import get_source_spec, list_sources, load_source_registry


def test_parse_source_overrides_handles_empty_and_valid() -> None:
    assert cli._parse_source_overrides(None) == {}
    assert cli._parse_source_overrides(["a=b", " key = value "]) == {"a": "b", "key": "value"}


def test_parse_source_overrides_rejects_invalid_entry() -> None:
    with pytest.raises(ValueError):
        cli._parse_source_overrides(["missing-separator"])


def test_format_column_and_db_summary_render_expected_shapes() -> None:
    column = {"name": "id", "type": "INTEGER", "primary_key_position": 1, "not_null": 1}
    assert cli._format_column(column) == "id INTEGER PK NOT NULL"
    assert cli._format_column({"name": "name", "type": "", "primary_key_position": 0, "not_null": 0}) == "name"

    summary = {
        "db": "/tmp/test.db",
        "tables": [
            {"table": "alerts", "row_count": 1, "columns": [column]},
            {"table": "runs", "row_count": 2, "columns": [column]},
        ],
    }
    text = cli._format_db_summary(summary)
    assert "Rows: 1 row" in text
    assert "Rows: 2 rows" in text
    assert "alerts" in text
    assert "runs" in text


def test_load_json_source_and_require_fields(tmp_path: Path) -> None:
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps({"metadata": {"source": "x"}, "records": [{"a": 1}]}), encoding="utf-8")

    payload = load_json_source(payload_path)
    assert payload.metadata == {"source": "x"}
    assert payload.records == [{"a": 1}]
    assert payload.size_bytes > 0
    assert len(payload.checksum) == 64

    assert require_fields({"a": 1}, ("a", "b")) == ["b"]


def test_source_registry_load_list_and_get(tmp_path: Path) -> None:
    missing = load_source_registry(tmp_path / "missing.json")
    assert missing == {"datasets": {}}

    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "datasets": {
                    "z.last": {"pipeline": "geospatial", "enabled": True},
                    "a.first": {"pipeline": "transit", "enabled": False},
                }
            }
        ),
        encoding="utf-8",
    )

    all_sources = list_sources(registry_path)
    assert [item["key"] for item in all_sources] == ["a.first", "z.last"]
    assert [item["key"] for item in list_sources(registry_path, pipeline="geospatial")] == ["z.last"]
    assert [item["key"] for item in list_sources(registry_path, enabled_only=True)] == ["z.last"]
    assert get_source_spec("z.last", registry_path)["pipeline"] == "geospatial"
    with pytest.raises(KeyError):
        get_source_spec("missing", registry_path)


def test_cli_main_db_summary_prints_text(monkeypatch, capsys) -> None:
    args = argparse.Namespace(command="db-summary", db="/tmp/test.db")

    class FakeParser:
        def parse_args(self):
            return args

    class FakeService:
        def __init__(self, db_path):
            assert db_path == "/tmp/test.db"

        def database_summary(self):
            return {
                "db": "/tmp/test.db",
                "tables": [{"table": "alerts", "row_count": 0, "columns": []}],
            }

    monkeypatch.setattr(cli, "_build_parser", lambda: FakeParser())
    monkeypatch.setattr(cli, "IngestionService", FakeService)
    cli.main()
    out = capsys.readouterr().out
    assert "Database: /tmp/test.db" in out
    assert "alerts" in out


def test_cli_main_ingest_bedbath_uses_disabled_promotion_when_requested(monkeypatch, capsys) -> None:
    args = argparse.Namespace(
        command="ingest-bedbath",
        db="/tmp/test.db",
        trigger="manual",
        listings_json=None,
        listings_csv=None,
        listings_map=None,
        permits_json=None,
        permits_csv=None,
        permits_map=None,
        ambiguous_csv="reports/a.csv",
        review_export_dir="reports/b",
        min_training_rows=10,
        shadow_mode=False,
        disable_promotion=True,
        shadow_table_name=None,
        backfill_location_fields=False,
        overwrite_location_fields=False,
    )

    class FakeParser:
        def parse_args(self):
            return args

    class FakeService:
        def __init__(self, db_path):
            assert db_path == "/tmp/test.db"

    called = {}

    def fake_run_bedbath_enrichment(db, **kwargs):
        called["db"] = db
        called["kwargs"] = kwargs
        return {"status": "ok"}

    monkeypatch.setattr(cli, "_build_parser", lambda: FakeParser())
    monkeypatch.setattr(cli, "IngestionService", FakeService)
    monkeypatch.setattr(cli, "run_bedbath_enrichment", fake_run_bedbath_enrichment)
    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert called["db"] == "/tmp/test.db"
    assert called["kwargs"]["config"].promotion_target == "disabled"


def test_cli_main_commands_route_to_service(monkeypatch, capsys) -> None:
    commands = [
        argparse.Namespace(command="init-db", db="/tmp/test.db"),
        argparse.Namespace(
            command="ingest",
            db="/tmp/test.db",
            source_key=["s1"],
            trigger="manual",
            source=["a=b"],
            taxonomy_version="v1",
            mapping_version="v1",
        ),
        argparse.Namespace(command="run-refresh", db="/tmp/test.db", trigger="on_demand", source=["x=y"]),
        argparse.Namespace(command="list-sources", db="/tmp/test.db", pipeline=None, enabled_only=False),
        argparse.Namespace(command="show-source", db="/tmp/test.db", key="a"),
        argparse.Namespace(command="db-path", db="/tmp/test.db"),
    ]
    idx = {"i": 0}

    class FakeParser:
        def parse_args(self):
            args = commands[idx["i"]]
            idx["i"] += 1
            return args

    class FakeService:
        def __init__(self, db_path):
            assert db_path == "/tmp/test.db"

        def init_database(self):
            return {"cmd": "init-db"}

        def ingest(self, **kwargs):
            assert kwargs["source_overrides"] == {"a": "b"}
            return {"cmd": "ingest"}

        def run_refresh(self, **kwargs):
            assert kwargs["source_overrides"] == {"x": "y"}
            return {"cmd": "run-refresh"}

        def list_sources(self, **kwargs):
            return {"cmd": "list-sources"}

        def get_source(self, key):
            assert key == "a"
            return {"cmd": "show-source"}

        def database_path(self):
            return {"cmd": "db-path"}

    monkeypatch.setattr(cli, "_build_parser", lambda: FakeParser())
    monkeypatch.setattr(cli, "IngestionService", FakeService)
    for _ in commands:
        cli.main()
    output = capsys.readouterr().out
    assert "init-db" in output
    assert "ingest" in output
    assert "run-refresh" in output
    assert "list-sources" in output
    assert "show-source" in output
    assert "db-path" in output


def test_cli_main_ingest_bedbath_prod_and_shadow_paths(monkeypatch, capsys) -> None:
    args_list = [
        argparse.Namespace(
            command="ingest-bedbath",
            db="/tmp/test.db",
            trigger="manual",
            listings_json=None,
            listings_csv="listing.csv",
            listings_map=None,
            permits_json=None,
            permits_csv="permits.csv",
            permits_map=None,
            ambiguous_csv="reports/a.csv",
            review_export_dir="reports/b",
            min_training_rows=10,
            shadow_mode=False,
            disable_promotion=False,
            shadow_table_name=None,
            backfill_location_fields=True,
            overwrite_location_fields=True,
        ),
        argparse.Namespace(
            command="ingest-bedbath",
            db="/tmp/test.db",
            trigger="manual",
            listings_json=None,
            listings_csv=None,
            listings_map=None,
            permits_json=None,
            permits_csv=None,
            permits_map=None,
            ambiguous_csv="reports/a.csv",
            review_export_dir="reports/b",
            min_training_rows=10,
            shadow_mode=False,
            disable_promotion=False,
            shadow_table_name="shadow_table",
            backfill_location_fields=False,
            overwrite_location_fields=False,
        ),
    ]
    idx = {"i": 0}
    seen = []

    class FakeParser:
        def parse_args(self):
            args = args_list[idx["i"]]
            idx["i"] += 1
            return args

    class FakeService:
        def __init__(self, db_path):
            assert db_path == "/tmp/test.db"

    def fake_run_bedbath_enrichment(db, **kwargs):
        seen.append(kwargs["config"].promotion_target)
        return {"status": "ok"}

    monkeypatch.setattr(cli, "_build_parser", lambda: FakeParser())
    monkeypatch.setattr(cli, "IngestionService", FakeService)
    monkeypatch.setattr(cli, "run_bedbath_enrichment", fake_run_bedbath_enrichment)
    cli.main()
    cli.main()
    payload = capsys.readouterr().out
    assert "ok" in payload
    assert seen == ["prod", "shadow"]


def test_cli_main_unknown_command_raises(monkeypatch) -> None:
    args = argparse.Namespace(command="nope", db="/tmp/test.db")

    class FakeParser:
        def parse_args(self):
            return args

    class FakeService:
        def __init__(self, db_path):
            assert db_path == "/tmp/test.db"

    monkeypatch.setattr(cli, "_build_parser", lambda: FakeParser())
    monkeypatch.setattr(cli, "IngestionService", FakeService)
    with pytest.raises(ValueError):
        cli.main()


def test_build_parser_accepts_commands() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["init-db"])
    assert args.command == "init-db"
    args = parser.parse_args(["ingest", "--source-key", "a"])
    assert args.command == "ingest"
    assert args.source_key == ["a"]


def test_cli_module_main_guard_executes(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["cli.py"])
    sys.modules.pop("data_sourcing.cli", None)
    with pytest.raises(SystemExit):
        runpy.run_module("data_sourcing.cli", run_name="__main__")
