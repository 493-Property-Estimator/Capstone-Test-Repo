from __future__ import annotations

from pathlib import Path

import estimator
from estimator import property_estimator as pe
from estimator.simple_estimator import summarize_property_cluster


def test_simple_estimator_returns_empty_summary_for_missing_values() -> None:
    payload = summarize_property_cluster([{"assessment_value": None}, {"other": 1}])
    assert payload == {"sample_size": 0, "mean": None, "median": None, "mode": []}


def test_simple_estimator_computes_summary_values() -> None:
    payload = summarize_property_cluster(
        [
            {"assessment_value": "100000"},
            {"assessment_value": 200000},
            {"assessment_value": 200000},
        ]
    )
    assert payload["sample_size"] == 3
    assert payload["mean"] == 166666.67
    assert payload["median"] == 200000.0
    assert payload["mode"] == [200000.0]


def test_estimator_init_exports_expected_symbols() -> None:
    assert "estimate_property_value" in estimator.__all__
    assert "warm_estimator" in estimator.__all__
    assert callable(estimator.estimate_property_value)


def test_estimate_property_value_uses_cached_estimator(monkeypatch, tmp_path: Path) -> None:
    calls = []

    class FakeEstimator:
        def estimate(self, *, lat, lon, property_attributes):
            calls.append((lat, lon, property_attributes))
            return {"ok": True}

    monkeypatch.setattr(pe, "_get_estimator_cached", lambda _: FakeEstimator())
    payload = pe.estimate_property_value(
        tmp_path / "open_data.db",
        lat=53.5,
        lon=-113.5,
        property_attributes={"bedrooms": 3},
    )
    assert payload == {"ok": True}
    assert calls == [(53.5, -113.5, {"bedrooms": 3})]


def test_get_estimator_cached_is_lru_cached(monkeypatch, tmp_path: Path) -> None:
    pe._get_estimator_cached.cache_clear()
    init_calls = []

    class FakePropertyEstimator:
        def __init__(self, db_path):
            init_calls.append(str(db_path))

    monkeypatch.setattr(pe, "PropertyEstimator", FakePropertyEstimator)
    resolved = str((tmp_path / "open_data.db").resolve())
    first = pe._get_estimator_cached(resolved)
    second = pe._get_estimator_cached(resolved)
    assert first is second
    assert len(init_calls) == 1


def test_warm_estimator_resolves_path_and_primes_cache(monkeypatch, tmp_path: Path) -> None:
    recorded = []

    def fake_get(path: str):
        recorded.append(path)
        return object()

    monkeypatch.setattr(pe, "_get_estimator_cached", fake_get)
    pe.warm_estimator(tmp_path / "open_data.db")
    assert recorded == [str((tmp_path / "open_data.db").resolve())]
