from __future__ import annotations

import io
import json
import runpy
import sqlite3
import sys
import types
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from scripts import create_db_sample as sample_mod
from scripts import download_and_prepare_crime_data as crime_mod
from scripts import init_and_ingest_open_data as init_mod
from src.data_sourcing import validate_bedbath as validate_mod
from src.estimator import runtime_services as rs


def _mk_validate_db(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE property_locations_prod (canonical_location_id TEXT)")
    conn.execute(
        """
        CREATE TABLE property_attributes_staging (
            canonical_location_id TEXT,
            bedrooms REAL,
            bathrooms REAL,
            bedrooms_estimated REAL,
            bathrooms_estimated REAL,
            source_type TEXT,
            source_name TEXT,
            confidence REAL,
            run_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE property_attributes_prod (
            canonical_location_id TEXT,
            bedrooms REAL,
            bathrooms REAL,
            bedrooms_estimated REAL,
            bathrooms_estimated REAL,
            source_type TEXT,
            source_name TEXT,
            confidence REAL
        )
        """
    )
    conn.executemany(
        "INSERT INTO property_locations_prod VALUES (?)",
        [("loc-1",), ("loc-2",), ("loc-3",)],
    )
    conn.executemany(
        "INSERT INTO property_attributes_prod VALUES (?,?,?,?,?,?,?,?)",
        [
            ("loc-1", 3, 2, None, None, "observed", "a", 0.9),
            ("loc-2", None, None, 2, 1.5, "inferred", "b", 0.7),
        ],
    )
    conn.executemany(
        "INSERT INTO property_attributes_staging VALUES (?,?,?,?,?,?,?,?,?)",
        [
            ("loc-1", 3, 2, None, None, "observed", "a", 0.9, "run-1"),
            ("loc-3", None, None, 1, 1, "imputed", "c", 0.4, "run-2"),
        ],
    )
    conn.commit()
    conn.close()
    return path


def test_validate_bedbath_with_and_without_run_id(tmp_path: Path) -> None:
    db = _mk_validate_db(tmp_path / "v.db")
    no_run = validate_mod.validate_bedbath(db, limit=5)
    assert no_run["counts"]["candidate_properties"] == 3
    assert no_run["counts"]["prod_rows"] == 2
    assert no_run["counts"]["remaining_nulls"] == 1
    assert no_run["samples"]

    with_run = validate_mod.validate_bedbath(db, run_id="run-1", limit=5)
    assert with_run["samples"]
    assert with_run["samples"][0]["canonical_location_id"] == "loc-1"


def test_validate_bedbath_main_prints_json(monkeypatch, tmp_path: Path, capsys) -> None:
    db = _mk_validate_db(tmp_path / "m.db")
    monkeypatch.setattr(sys, "argv", ["validate_bedbath.py", "--db-path", str(db), "--run-id", "run-1", "--limit", "1"])
    validate_mod.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["candidate_properties"] == 3
    assert len(payload["samples"]) == 1


def test_validate_bedbath_module_main_guard(monkeypatch, tmp_path: Path, capsys) -> None:
    db = _mk_validate_db(tmp_path / "g.db")
    monkeypatch.setattr(sys, "argv", ["validate_bedbath.py", "--db-path", str(db)])
    sys.modules.pop("src.data_sourcing.validate_bedbath", None)
    runpy.run_module("src.data_sourcing.validate_bedbath", run_name="__main__")
    assert "counts" in capsys.readouterr().out


def test_runtime_helpers_and_osrm_errors(monkeypatch) -> None:
    assert rs.haversine_meters(53.5, -113.5, 53.5, -113.5) == 0.0
    assert rs.round_coord(1.23456789) == 1.234568
    assert rs.safe_text(None) is None
    assert rs.safe_text("  x  ") == "x"
    assert rs.safe_text("   ") is None
    with pytest.raises(NotImplementedError):
        rs.CrimeProvider().summary_by_neighbourhood("n")
    with pytest.raises(NotImplementedError):
        rs.CrimeProvider().summary_by_point(1, 2, 3)
    with pytest.raises(ValueError):
        rs.OsrmService(base_url="http://x").resolve_profile("train")

    osrm = rs.OsrmService(base_url=None)
    with pytest.raises(rs.OsrmError):
        osrm._request("route", "driving", [(53.5, -113.5), (53.6, -113.4)], {"a": "b"})

    class FakeHTTPError(urllib.error.HTTPError):
        def __init__(self):
            super().__init__("http://x", 500, "bad", hdrs=None, fp=None)

        def read(self):  # type: ignore[override]
            return b"boom"

    monkeypatch.setattr(rs.urllib.request, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(FakeHTTPError()))
    with pytest.raises(rs.OsrmError):
        rs.OsrmService(base_url="http://x")._request("route", "driving", [(1, 2), (3, 4)], {"a": "b"})

    monkeypatch.setattr(
        rs.urllib.request,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(urllib.error.URLError("down")),
    )
    with pytest.raises(rs.OsrmError):
        rs.OsrmService(base_url="http://x")._request("route", "driving", [(1, 2), (3, 4)], {"a": "b"})


def test_runtime_osrm_success_and_route(monkeypatch) -> None:
    class Resp:
        def __init__(self, payload: dict):
            self._payload = payload

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

    monkeypatch.setenv("TESTING_STAGE_OSRM_PROFILE_DRIVING", "car")
    monkeypatch.setattr(
        rs.urllib.request,
        "urlopen",
        lambda *_a, **_k: Resp({"code": "Ok", "routes": [{"distance": 100.12, "duration": 60.0, "geometry": {"x": 1}}]}),
    )
    svc = rs.OsrmService(base_url="http://osrm")
    assert svc.is_configured() is True
    assert svc.resolve_profile("driving") == "car"
    out = svc.route(53.5, -113.5, 53.6, -113.4, "driving")
    assert out["distance_m"] == 100.12
    assert out["duration_min"] == 1.0

    monkeypatch.setattr(rs.urllib.request, "urlopen", lambda *_a, **_k: Resp({"code": "Nope", "message": "x"}))
    with pytest.raises(rs.OsrmError):
        svc._request("route", "driving", [(1, 2), (3, 4)], {"a": "b"})

    monkeypatch.setattr(rs.urllib.request, "urlopen", lambda *_a, **_k: Resp({"code": "Ok", "routes": []}))
    with pytest.raises(rs.OsrmError):
        svc.route(53.5, -113.5, 53.6, -113.4, "driving")


def test_runtime_crime_provider_modes(tmp_path: Path) -> None:
    db = tmp_path / "crime.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE crime_summary_prod (neighbourhood TEXT, crime_type TEXT, incident_count INTEGER)")
    conn.execute("INSERT INTO crime_summary_prod VALUES ('Downtown','Theft',5)")
    conn.commit()
    conn.close()

    provider = rs.SQLiteCrimeProvider(db)
    assert provider.is_available() is True
    out = provider.summary_by_neighbourhood("Downtown")
    assert out["total_incidents"] == 5

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("DROP TABLE crime_summary_prod")
    conn.execute("CREATE TABLE crime_incidents_prod (neighbourhood_name TEXT, offence_type TEXT, latitude REAL, longitude REAL)")
    conn.execute("INSERT INTO crime_incidents_prod VALUES ('Downtown','Theft',53.5,-113.5)")
    conn.commit()
    conn.close()
    provider2 = rs.SQLiteCrimeProvider(db)
    assert provider2.summary_by_neighbourhood("Downtown")["total_incidents"] == 1
    point = provider2.summary_by_point(53.5, -113.5, 500.0)
    assert point["total_incidents"] == 1

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("DROP TABLE crime_incidents_prod")
    conn.execute("CREATE TABLE crime_incidents_prod (x INTEGER)")
    conn.execute("INSERT INTO crime_incidents_prod VALUES (1)")
    conn.commit()
    conn.close()
    provider3 = rs.SQLiteCrimeProvider(db)
    assert provider3.summary_by_neighbourhood("Downtown")["available"] is False
    assert provider3.summary_by_point(53.5, -113.5, 100.0)["available"] is False
    assert rs.SQLiteCrimeProvider(tmp_path / "missing.db").is_available() is False


def test_create_db_sample_parse_and_copy_rows(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_db_sample.py",
            "--source-db",
            str(tmp_path / "src.db"),
            "--output-db",
            str(tmp_path / "out.db"),
            "--property-limit",
            "2",
            "--poi-limit",
            "3",
        ],
    )
    args = sample_mod._parse_args()
    assert args.property_limit == 2
    assert args.poi_limit == 3

    missing_code = sample_mod.main()
    assert missing_code == 2
    assert "source db does not exist" in capsys.readouterr().err

    src = sqlite3.connect(":memory:")
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(":memory:")
    dst.execute("CREATE TABLE x (id INTEGER PRIMARY KEY, v TEXT)")
    src.execute("CREATE TABLE x (id INTEGER PRIMARY KEY, v TEXT)")
    src.executemany("INSERT INTO x VALUES (?,?)", [(1, "a"), (2, "b")])
    assert sample_mod._copy_rows(src, dst, "x", "SELECT * FROM x ORDER BY id", ()) == 2
    assert sample_mod._copy_rows(src, dst, "x", "SELECT * FROM x WHERE 1=0", ()) == 0


def test_create_db_sample_main_success_with_fakes(tmp_path: Path, monkeypatch, capsys) -> None:
    src_db = tmp_path / "src.db"
    src_db.write_bytes(b"x")
    out_db = tmp_path / "out.db"

    class FakeConn:
        def __init__(self):
            self.closed = False
            self.committed = False

        def close(self):
            self.closed = True

        def commit(self):
            self.committed = True

    src_conn = FakeConn()
    dst_conn = FakeConn()
    calls = {"n": 0, "tables": []}

    def fake_connect(path):
        calls["n"] += 1
        return src_conn if calls["n"] == 1 else dst_conn

    monkeypatch.setattr(sample_mod, "connect", fake_connect)
    monkeypatch.setattr(sample_mod, "init_db", lambda _d: None)
    monkeypatch.setattr(sample_mod, "_copy_rows", lambda _s, _d, table, _q, _p: calls["tables"].append(table) or 1)
    monkeypatch.setattr(
        sample_mod,
        "_parse_args",
        lambda: types.SimpleNamespace(source_db=str(src_db), output_db=str(out_db), property_limit=2, poi_limit=3),
    )
    assert sample_mod.main() == 0
    output = capsys.readouterr().out
    assert "sample db created" in output
    assert len(calls["tables"]) == len(sample_mod.PROPERTY_TABLES) + len(sample_mod.POI_TABLES)
    assert src_conn.closed and dst_conn.closed and dst_conn.committed


def test_init_and_ingest_open_data_main_paths(monkeypatch, tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    out_db = tmp_path / "db.sqlite"

    args = types.SimpleNamespace(
        data_dir=str(data_dir),
        db=str(out_db),
        dry_run=True,
        continue_on_error=False,
        include_osm=False,
    )
    monkeypatch.setattr(init_mod, "_parse_args", lambda: args)
    status = init_mod.main()
    assert status == 2
    assert "data_dir does not exist" in capsys.readouterr().out

    data_dir.mkdir()
    planned_item = types.SimpleNamespace(source_key="a", file_path=data_dir / "a.csv", reason="x")
    monkeypatch.setattr(init_mod, "discover_sources", lambda *_a, **_k: ([planned_item], ["n"]))
    status = init_mod.main()
    assert status == 0
    assert json.loads(capsys.readouterr().out)["status"] == "dry_run"

    class FakeService:
        def __init__(self, db_path):
            assert db_path == str(out_db)

        def init_database(self):
            return {"ok": True}

        def ingest(self, **_kwargs):
            return {"status": "failed"}

    args2 = types.SimpleNamespace(
        data_dir=str(data_dir),
        db=str(out_db),
        dry_run=False,
        continue_on_error=False,
        include_osm=True,
    )
    monkeypatch.setattr(init_mod, "_parse_args", lambda: args2)
    monkeypatch.setattr(init_mod, "IngestionService", FakeService)
    status = init_mod.main()
    payload = json.loads(capsys.readouterr().out)
    assert status == 1 and payload["status"] == "failed"


def test_init_and_ingest_open_data_module_main_guard(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(
        sys,
        "argv",
        ["init_and_ingest_open_data.py", "--data-dir", str(data_dir), "--db", str(tmp_path / "x.db"), "--dry-run"],
    )
    sys.modules.pop("scripts.init_and_ingest_open_data", None)
    monkeypatch.setattr(init_mod, "discover_sources", lambda *_a, **_k: ([], []))
    monkeypatch.setattr(init_mod, "IngestionService", lambda **_k: types.SimpleNamespace(init_database=lambda: {}, ingest=lambda **_x: {"status": "succeeded"}))
    with pytest.raises(SystemExit):
        runpy.run_module("scripts.init_and_ingest_open_data", run_name="__main__")


def test_crime_download_prepare_and_main_paths(monkeypatch, tmp_path: Path, capsys) -> None:
    class Resp:
        def read(self):
            return b"zip-bytes"

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

    monkeypatch.setattr(crime_mod.urllib.request, "urlopen", lambda *_a, **_k: Resp())
    info = crime_mod._download_zip("http://example.com/x.zip", tmp_path / "x.zip")
    assert info["zip_size_bytes"] == 9

    zip_path = tmp_path / "crime.zip"
    import zipfile

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("metadata.csv", "a,b\n1,2\n")
        zf.writestr("crime.csv", 'GEO,Statistics,val\n"Edmonton, Alberta, municipal",Actual incidents,1\n')
    assert crime_mod._find_csv_member(zip_path) == "crime.csv"
    out = crime_mod._prepare_edmonton_csv(
        zip_path,
        tmp_path / "filtered.csv",
        geo_match="Edmonton, Alberta, municipal",
        allowed_stats={"Actual incidents"},
    )
    assert out["kept_rows"] == 1

    empty_zip = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty_zip, "w"):
        pass
    with pytest.raises(FileNotFoundError):
        crime_mod._find_csv_member(empty_zip)

    bad_zip = tmp_path / "badheader.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("crime.csv", "")
    with pytest.raises(ValueError):
        crime_mod._prepare_edmonton_csv(bad_zip, tmp_path / "o.csv", geo_match="x", allowed_stats={"y"})

    monkeypatch.setattr(crime_mod, "_parse_args", lambda: types.SimpleNamespace(
        download_url="x",
        zip_path=str(tmp_path / "missing.zip"),
        output_csv=str(tmp_path / "out.csv"),
        geo_match="x",
        stats=["y"],
        skip_download=True,
        ingest=False,
        db=str(tmp_path / "db.sqlite"),
    ))
    assert crime_mod.main() == 2
    assert json.loads(capsys.readouterr().out)["status"] == "failed"

    monkeypatch.setattr(crime_mod, "_parse_args", lambda: types.SimpleNamespace(
        download_url="x",
        zip_path=str(zip_path),
        output_csv=str(tmp_path / "out2.csv"),
        geo_match="Edmonton, Alberta, municipal",
        stats=["Actual incidents"],
        skip_download=True,
        ingest=True,
        db=str(tmp_path / "db.sqlite"),
    ))
    monkeypatch.setattr(crime_mod, "_run_ingest", lambda _db, _csv: {"status": "succeeded"})
    assert crime_mod.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "succeeded"


def test_crime_module_main_guard(monkeypatch, tmp_path: Path) -> None:
    zip_path = tmp_path / "ok.zip"
    import zipfile

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("crime.csv", "GEO,Statistics,val\nx,y,1\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_and_prepare_crime_data.py",
            "--skip-download",
            "--zip-path",
            str(zip_path),
            "--output-csv",
            str(tmp_path / "out.csv"),
            "--geo-match",
            "x",
            "--stats",
            "y",
        ],
    )
    sys.modules.pop("scripts.download_and_prepare_crime_data", None)
    with pytest.raises(SystemExit):
        runpy.run_module("scripts.download_and_prepare_crime_data", run_name="__main__")
