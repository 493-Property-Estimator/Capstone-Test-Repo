from __future__ import annotations

import argparse
import importlib.util
import json
import runpy
import sys
from pathlib import Path

from scripts import ingest_data_folder as module


def _write(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_normalize_for_match_compacts_non_alnum() -> None:
    assert module._normalize_for_match("Road-Network 2026!.ZIP") == "road network 2026 zip"


def test_pick_latest_matching_respects_suffix_and_mtime(tmp_path: Path) -> None:
    older = _write(tmp_path / "Property Assessment Data old.csv")
    newer = _write(tmp_path / "nested" / "Property Assessment Data new.csv")
    _write(tmp_path / "Property Assessment Data ignored.txt")

    older.touch()
    newer.touch()
    selected = module._pick_latest_matching(
        tmp_path,
        required_fragments=["Property Assessment Data"],
        allowed_suffixes=(".csv",),
    )
    assert selected == newer


def test_pick_latest_matching_returns_none_when_no_match(tmp_path: Path) -> None:
    _write(tmp_path / "nothing-here.csv")
    assert module._pick_latest_matching(tmp_path, ["crime", "police"], (".json",)) is None


def test_pick_crime_summary_prefers_police_then_falls_back(tmp_path: Path) -> None:
    fallback = _write(tmp_path / "crime-summary.csv")
    assert module._pick_crime_summary_path(tmp_path) == fallback

    preferred = _write(tmp_path / "crime_police_service.csv")
    assert module._pick_crime_summary_path(tmp_path) == preferred


def test_pick_osm_paths_prefer_shp_then_zip_fallback(tmp_path: Path) -> None:
    roads_shp = _write(tmp_path / "_tmp_alberta_layers" / "gis_osm_roads_free_1.shp")
    pois_shp = _write(tmp_path / "_tmp_alberta_layers" / "gis_osm_pois_free_1.shp")
    assert module._pick_osm_roads_path(tmp_path) == roads_shp
    assert module._pick_osm_pois_path(tmp_path) == pois_shp

    roads_shp.unlink()
    pois_shp.unlink()
    alberta_zip = _write(tmp_path / "alberta-latest.zip")
    assert module._pick_osm_roads_path(tmp_path) == alberta_zip
    assert module._pick_osm_pois_path(tmp_path) == alberta_zip


def test_discover_sources_empty_dir_returns_notes_and_bundled_road(tmp_path: Path) -> None:
    planned, notes = module.discover_sources(tmp_path, include_osm=True)
    planned_keys = {item.source_key for item in planned}

    assert "geospatial.roads" in planned_keys
    assert any("No assessment CSV" in note for note in notes)
    assert any("No OSM roads file found" in note for note in notes)
    assert any("No OSM POIs file found" in note for note in notes)


def test_run_returns_failed_for_missing_data_dir(monkeypatch, tmp_path: Path, capsys) -> None:
    missing_data_dir = tmp_path / "missing"
    args = argparse.Namespace(
        data_dir=str(missing_data_dir),
        db=str(tmp_path / "open_data.db"),
        dry_run=False,
        continue_on_error=False,
        include_osm=False,
    )
    monkeypatch.setattr(module, "_parse_args", lambda: args)

    status = module.run()
    assert status == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert "does not exist" in payload["error"]


def test_run_dry_run_prints_plan(monkeypatch, tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    args = argparse.Namespace(
        data_dir=str(data_dir),
        db=str(tmp_path / "open_data.db"),
        dry_run=True,
        continue_on_error=False,
        include_osm=False,
    )
    monkeypatch.setattr(module, "_parse_args", lambda: args)

    status = module.run()
    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "dry_run"
    assert "planned_sources" in payload


def test_parse_args_reads_cli_values(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "ingest_data_folder.py",
            "--data-dir",
            "/tmp/data",
            "--db",
            "/tmp/db.sqlite",
            "--dry-run",
            "--continue-on-error",
            "--include-osm",
        ],
    )
    args = module._parse_args()
    assert args.data_dir == "/tmp/data"
    assert args.db == "/tmp/db.sqlite"
    assert args.dry_run is True
    assert args.continue_on_error is True
    assert args.include_osm is True


def test_discover_sources_full_matches(tmp_path: Path) -> None:
    files = [
        "Property Assessment Data sample.csv",
        "Property Information sample.csv",
        "Edmonton Public School Board School Locations.csv",
        "Police Stations.csv",
        "Playgrounds.csv",
        "Parks.csv",
        "Edmonton Business Census.csv",
        "crime police summary.csv",
        "Recreation Facilities.csv",
        "Road Network.geojson",
        "ETS Bus Schedule GTFS Data Feed Stops.zip",
        "ETS Bus Schedule GTFS Data Feed Trips.zip",
    ]
    for name in files:
        _write(tmp_path / name)
    _write(tmp_path / "_tmp_alberta_layers" / "gis_osm_roads_free_1.shp")
    _write(tmp_path / "_tmp_alberta_layers" / "gis_osm_pois_free_1.shp")

    planned, notes = module.discover_sources(tmp_path, include_osm=True)
    assert notes == []
    keys = {item.source_key for item in planned}
    assert {
        "assessments.property_tax_csv",
        "assessments.property_information",
        "geospatial.school_locations",
        "geospatial.police_stations",
        "geospatial.playgrounds",
        "geospatial.parks",
        "geospatial.business_census",
        "crime.statscan_police_service",
        "geospatial.recreation_facilities",
        "geospatial.roads",
        "transit.ets_stops",
        "transit.ets_trips",
        "geospatial.osm_alberta",
        "geospatial.osm_pois_alberta",
    }.issubset(keys)


def test_discover_sources_road_missing_without_snapshot(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(module, "_bundled_roads_snapshot", lambda: None)
    planned, notes = module.discover_sources(tmp_path, include_osm=False)
    assert not any(item.source_key == "geospatial.roads" for item in planned)
    assert any("No Edmonton Road Network file matched" in note for note in notes)


def test_run_executes_ingest_and_stops_on_first_failure(monkeypatch, tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    planned = [
        module.PlannedSource("a", data_dir / "a.csv", "a"),
        module.PlannedSource("b", data_dir / "b.csv", "b"),
    ]

    args = argparse.Namespace(
        data_dir=str(data_dir),
        db=str(tmp_path / "open_data.db"),
        dry_run=False,
        continue_on_error=False,
        include_osm=False,
    )
    monkeypatch.setattr(module, "_parse_args", lambda: args)
    monkeypatch.setattr(module, "discover_sources", lambda *_args, **_kwargs: (planned, ["n1"]))

    calls = {"ingest": 0}

    class FakeService:
        def __init__(self, db_path):
            assert db_path == str(tmp_path / "open_data.db")

        def init_database(self):
            return {"status": "ok"}

        def ingest(self, **kwargs):
            calls["ingest"] += 1
            return {"status": "failed" if calls["ingest"] == 1 else "succeeded", "kwargs": kwargs}

    monkeypatch.setattr(module, "IngestionService", FakeService)
    status = module.run()
    payload = json.loads(capsys.readouterr().out)
    assert status == 1
    assert payload["status"] == "failed"
    assert len(payload["runs"]) == 1


def test_run_executes_ingest_with_continue_on_error(monkeypatch, tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    planned = [
        module.PlannedSource("a", data_dir / "a.csv", "a"),
        module.PlannedSource("b", data_dir / "b.csv", "b"),
    ]

    args = argparse.Namespace(
        data_dir=str(data_dir),
        db=str(tmp_path / "open_data.db"),
        dry_run=False,
        continue_on_error=True,
        include_osm=False,
    )
    monkeypatch.setattr(module, "_parse_args", lambda: args)
    monkeypatch.setattr(module, "discover_sources", lambda *_args, **_kwargs: (planned, []))

    class FakeService:
        def __init__(self, db_path):
            assert db_path == str(tmp_path / "open_data.db")

        def init_database(self):
            return {"status": "ok"}

        def ingest(self, **kwargs):
            key = kwargs["source_keys"][0]
            return {"status": "failed" if key == "a" else "succeeded"}

    monkeypatch.setattr(module, "IngestionService", FakeService)
    status = module.run()
    payload = json.loads(capsys.readouterr().out)
    assert status == 1
    assert len(payload["runs"]) == 2
    assert payload["runs"][0]["status"] == "failed"
    assert payload["runs"][1]["status"] == "succeeded"


def test_module_bootstrap_inserts_src_path_when_missing(monkeypatch) -> None:
    module_path = Path(module.__file__)
    original = list(sys.path)
    src_path = str(module_path.resolve().parents[1] / "src")
    filtered = [p for p in original if p != src_path]
    monkeypatch.setattr(sys, "path", filtered)

    spec = importlib.util.spec_from_file_location("tmp_ingest_mod", module_path)
    loaded = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules["tmp_ingest_mod"] = loaded
    spec.loader.exec_module(loaded)
    assert src_path in sys.path


def test_module_main_guard_executes(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["ingest_data_folder.py", "--dry-run", "--data-dir", "/tmp/does-not-exist"])
    sys.modules.pop("scripts.ingest_data_folder", None)
    try:
        runpy.run_module("scripts.ingest_data_folder", run_name="__main__")
    except SystemExit:
        pass
