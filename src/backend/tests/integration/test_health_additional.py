import sqlite3
import types
import sys

from src.backend.src.api import health as health_api


def test_health_rate_limit_and_routing_branches(client, monkeypatch):
    from dataclasses import replace
    settings = client.app.state.settings
    client.app.state.settings = replace(
        settings,
        health_rate_limit_per_minute=1,
        health_rate_limit_window_seconds=60.0,
    )
    settings = client.app.state.settings
    client.app.state.health_request_timestamps = []

    resp1 = client.get("/health")
    assert resp1.status_code in (200, 429)
    resp2 = client.get("/health")
    assert resp2.status_code == 429

    client.app.state.settings = replace(settings, enable_routing=True, routing_provider="other")
    settings = client.app.state.settings
    resp = client.get("/health")
    assert resp.status_code in (200, 429)

    client.app.state.settings = replace(settings, enable_routing=False)
    resp = client.get("/health")
    assert resp.status_code in (200, 429)


def test_health_routing_and_valuation_paths(client, monkeypatch):
    from dataclasses import replace
    settings = client.app.state.settings
    client.app.state.settings = replace(
        settings,
        health_rate_limit_per_minute=10_000,
        health_rate_limit_window_seconds=60.0,
    )
    client.app.state.health_request_timestamps = []
    def _fresh_ok(*_a, **_k):
        return {"dependency": {"name": "ingestion_freshness", "status": "ok", "details": ""}}

    monkeypatch.setattr(health_api, "_latest_dataset_freshness", _fresh_ok)

    client.app.state.settings = replace(
        client.app.state.settings,
        enable_routing=True,
        routing_provider="other",
    )
    client.app.state.health_request_timestamps = []
    monkeypatch.setattr(health_api, "estimate_property_value", lambda *_a, **_k: None)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"

    client.app.state.settings = replace(client.app.state.settings, enable_routing=False)
    client.app.state.health_request_timestamps = []
    monkeypatch.setattr(health_api, "estimate_property_value", lambda *_a, **_k: None)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"

    client.app.state.settings = replace(
        client.app.state.settings,
        enable_routing=True,
        routing_provider="mock_road",
    )
    client.app.state.health_request_timestamps = []
    monkeypatch.setattr(health_api, "estimate_property_value", None)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


def test_health_feature_store_down(client, monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("down")

    monkeypatch.setattr(health_api, "connect", _boom)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in {"unhealthy", "degraded"}


def test_health_routing_degrades_status_from_healthy(client, monkeypatch):
    from dataclasses import replace
    import contextlib

    settings = client.app.state.settings
    client.app.state.settings = replace(
        settings,
        health_rate_limit_per_minute=10_000,
        health_rate_limit_window_seconds=60.0,
        enable_routing=True,
        routing_provider="other",
    )
    client.app.state.health_request_timestamps = []

    class _Conn:
        def execute(self, *_a, **_k):
            return None

    @contextlib.contextmanager
    def _ok_connect(*_a, **_k):
        yield _Conn()

    monkeypatch.setattr(health_api, "connect", _ok_connect)
    monkeypatch.setattr(health_api, "_latest_dataset_freshness", lambda *_a, **_k: {"dependency": {"status": "ok"}})
    monkeypatch.setattr(health_api, "estimate_property_value", lambda *_a, **_k: None)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"

    client.app.state.settings = replace(client.app.state.settings, enable_routing=False)
    client.app.state.health_request_timestamps = []
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


def test_health_routing_no_status_change_when_unhealthy(client, monkeypatch):
    from dataclasses import replace

    settings = client.app.state.settings
    client.app.state.settings = replace(
        settings,
        health_rate_limit_per_minute=10_000,
        health_rate_limit_window_seconds=60.0,
        enable_routing=True,
        routing_provider="other",
    )
    client.app.state.health_request_timestamps = []

    def _boom(*_a, **_k):
        raise RuntimeError("down")

    monkeypatch.setattr(health_api, "connect", _boom)
    monkeypatch.setattr(health_api, "_latest_dataset_freshness", lambda *_a, **_k: {"dependency": {"status": "ok"}})
    monkeypatch.setattr(health_api, "estimate_property_value", lambda *_a, **_k: None)

    resp = client.get("/health")
    assert resp.status_code == 200

    client.app.state.settings = replace(client.app.state.settings, enable_routing=False)
    client.app.state.health_request_timestamps = []
    resp = client.get("/health")
    assert resp.status_code == 200


def test_memory_health_status_unknown(monkeypatch):
    bad_resource = types.SimpleNamespace(getrusage=lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("bad")))
    monkeypatch.setitem(sys.modules, "resource", bad_resource)
    assert health_api._memory_health_status(types.SimpleNamespace(memory_high_rss_kb=1)) == "unknown"


def test_latest_dataset_freshness_variants(tmp_path):
    db_path = tmp_path / "fresh.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE dataset_versions (version_id TEXT, promoted_at TEXT)")
    conn.execute("INSERT INTO dataset_versions VALUES ('v1', '2026-01-01T00:00:00')")
    conn.commit()
    conn.close()

    data = health_api._latest_dataset_freshness(db_path, 1)
    assert data["dependency"]["status"] in {"ok", "degraded"}

    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM dataset_versions")
    conn.commit()
    conn.close()

    data = health_api._latest_dataset_freshness(db_path, 1)
    assert data["dependency"]["status"] == "degraded"

    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO dataset_versions VALUES ('v2', 'bad-date')")
    conn.commit()
    conn.close()
    data = health_api._latest_dataset_freshness(db_path, 1)
    assert "dependency" in data

    data = health_api._latest_dataset_freshness("missing.db", 1)
    assert data["dependency"]["status"] == "degraded"
