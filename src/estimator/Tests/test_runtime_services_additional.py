import json
import sqlite3
import math
from io import BytesIO
from pathlib import Path

import pytest

from src.estimator import runtime_services as rs


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _write_crime_summary_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE crime_summary_prod (neighbourhood TEXT, crime_type TEXT, incident_count INTEGER, rate_per_100k REAL)"
    )
    conn.execute(
        "INSERT INTO crime_summary_prod (neighbourhood, crime_type, incident_count, rate_per_100k) VALUES ('Downtown', 'Theft', 5, 12.5)"
    )
    conn.commit()
    conn.close()


def _write_crime_incidents_db(db_path: Path, *, columns: str, rows: list[tuple]):
    conn = sqlite3.connect(db_path)
    conn.execute(f"CREATE TABLE crime_incidents_prod ({columns})")
    if rows:
        placeholders = ",".join(["?"] * len(rows[0]))
        conn.executemany(f"INSERT INTO crime_incidents_prod VALUES ({placeholders})", rows)
    conn.commit()
    conn.close()


def test_runtime_helpers_cover_paths():
    assert rs.haversine_meters(0, 0, 0, 0) == 0
    assert rs.round_coord(1.23456789) == 1.234568
    assert rs.safe_text(None) is None
    assert rs.safe_text("  value ") == "value"


def test_osrm_service_profile_and_not_configured(monkeypatch):
    service = rs.OsrmService(base_url="", timeout_seconds=1)
    with pytest.raises(rs.OsrmError):
        service._request("route", "driving", [(0, 0), (1, 1)], {})

    monkeypatch.setenv("TESTING_STAGE_OSRM_PROFILE_DRIVING", "car")
    assert service.resolve_profile("driving") == "car"
    with pytest.raises(ValueError):
        service.resolve_profile("flying")


def test_osrm_request_http_and_url_errors(monkeypatch):
    service = rs.OsrmService(base_url="http://example", timeout_seconds=1)

    def _raise_http(*_a, **_k):
        fp = BytesIO(b"bad")
        raise rs.urllib.error.HTTPError("http://example", 500, "boom", {}, fp)

    monkeypatch.setattr(rs.urllib.request, "urlopen", _raise_http)
    with pytest.raises(rs.OsrmError):
        service._request("route", "driving", [(0, 0), (1, 1)], {})

    def _raise_url(*_a, **_k):
        raise rs.urllib.error.URLError("nope")

    monkeypatch.setattr(rs.urllib.request, "urlopen", _raise_url)
    with pytest.raises(rs.OsrmError):
        service._request("route", "driving", [(0, 0), (1, 1)], {})


def test_osrm_request_payload_error_and_route(monkeypatch):
    service = rs.OsrmService(base_url="http://example", timeout_seconds=1)

    def _bad_payload(*_a, **_k):
        return _FakeResponse({"code": "Error", "message": "bad"})

    monkeypatch.setattr(rs.urllib.request, "urlopen", _bad_payload)
    with pytest.raises(rs.OsrmError):
        service._request("route", "driving", [(0, 0), (1, 1)], {})

    def _no_routes(*_a, **_k):
        return _FakeResponse({"code": "Ok", "routes": []})

    monkeypatch.setattr(rs.urllib.request, "urlopen", _no_routes)
    with pytest.raises(rs.OsrmError):
        service.route(0, 0, 1, 1, "driving")

    def _ok_routes(*_a, **_k):
        return _FakeResponse({"code": "Ok", "routes": [{"distance": 1000, "duration": 60, "geometry": {}}]})

    monkeypatch.setattr(rs.urllib.request, "urlopen", _ok_routes)
    result = service.route(0, 0, 1, 1, "driving")
    assert result["distance_m"] == 1000
    assert result["duration_s"] == 60
    assert result["duration_min"] == 1.0


def test_unavailable_crime_provider():
    provider = rs.UnavailableCrimeProvider()
    assert provider.is_available() is False
    summary = provider.summary_by_neighbourhood("Downtown")
    assert summary["available"] is False
    point = provider.summary_by_point(53.5, -113.5, 1000)
    assert point["available"] is False


def test_crime_provider_base_methods():
    base = rs.CrimeProvider()
    with pytest.raises(NotImplementedError):
        base.summary_by_neighbourhood("Downtown")
    with pytest.raises(NotImplementedError):
        base.summary_by_point(0, 0, 1)


def test_sqlite_crime_provider_summary_mode(tmp_path):
    db_path = tmp_path / "crime_summary.db"
    _write_crime_summary_db(db_path)
    provider = rs.SQLiteCrimeProvider(db_path)
    assert provider.is_available() is True
    summary = provider.summary_by_neighbourhood("Downtown")
    assert summary["available"] is True
    point = provider.summary_by_point(53.5, -113.5, 1000)
    assert point["available"] is False


def test_sqlite_crime_provider_summary_empty_tables(tmp_path):
    db_path = tmp_path / "crime_empty.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE crime_summary_prod (neighbourhood TEXT, crime_type TEXT, incident_count INTEGER)")
    conn.execute("CREATE TABLE crime_incidents_prod (neighbourhood TEXT)")
    conn.commit()
    conn.close()
    provider = rs.SQLiteCrimeProvider(db_path)
    assert provider.is_available() is False
    summary = provider.summary_by_neighbourhood("Downtown")
    assert summary["available"] is False
    point = provider.summary_by_point(0, 0, 100)
    assert point["available"] is False


def test_write_crime_incidents_no_rows(tmp_path):
    db_path = tmp_path / "crime_empty_rows.db"
    _write_crime_incidents_db(db_path, columns="neighbourhood TEXT", rows=[])
    provider = rs.SQLiteCrimeProvider(db_path)
    assert provider.is_available() is False


def test_sqlite_crime_provider_incidents_missing_columns(tmp_path):
    db_path = tmp_path / "crime_incidents_missing.db"
    _write_crime_incidents_db(db_path, columns="id INTEGER", rows=[(1,)])
    provider = rs.SQLiteCrimeProvider(db_path)
    assert provider.is_available() is True
    summary = provider.summary_by_neighbourhood("Downtown")
    assert summary["available"] is False
    point = provider.summary_by_point(0, 0, 100)
    assert point["available"] is False


def test_sqlite_crime_provider_incidents_with_columns(tmp_path):
    db_path = tmp_path / "crime_incidents.db"
    lat0 = 53.5461
    lon0 = -113.4938
    delta = 50 / 111_320.0
    lon_delta = 50 / (111_320.0 * math.cos(math.radians(lat0)))
    _write_crime_incidents_db(
        db_path,
        columns="neighbourhood_name TEXT, offense_type TEXT, lat REAL, lon REAL",
        rows=[
            ("Downtown", "Theft", lat0, lon0),
            ("Downtown", "Theft", lat0 + delta, lon0 + lon_delta),
            ("Downtown", "Assault", lat0 + delta * 2, lon0 + lon_delta * 2),
        ],
    )
    provider = rs.SQLiteCrimeProvider(db_path)
    summary = provider.summary_by_neighbourhood("Downtown")
    assert summary["available"] is True
    point = provider.summary_by_point(lat0, lon0, 50)
    assert point["available"] is True
    assert point["total_incidents"] >= 1


def test_sqlite_crime_provider_incidents_alt_columns(tmp_path):
    db_path = tmp_path / "crime_incidents_alt.db"
    _write_crime_incidents_db(
        db_path,
        columns="neighbourhood TEXT, offence_type TEXT, latitude REAL, longitude REAL",
        rows=[
            ("Downtown", "Theft", 53.5461, -113.4938),
            ("Downtown", "Theft", 53.8, -113.9),
        ],
    )
    provider = rs.SQLiteCrimeProvider(db_path)
    summary = provider.summary_by_neighbourhood("Downtown")
    assert summary["available"] is True
    point = provider.summary_by_point(53.5461, -113.4938, 200)
    assert point["available"] is True
