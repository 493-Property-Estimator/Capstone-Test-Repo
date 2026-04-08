import time

from src.backend.src.services.cache import MemoryCache
from src.backend.src.services import warnings as warning_service
from src.backend.src.services import routing
from src.backend.src.services import features
from src.backend.src.services.metrics import Metrics
from src.backend.src.services import property_viewport


def test_memory_cache_stale_and_ratio(monkeypatch):
    cache = MemoryCache(ttl_seconds=1)

    now = time.time()
    monkeypatch.setattr("src.backend.src.services.cache.time.time", lambda: now)
    cache.set("key", {"value": 1}, "v1")

    monkeypatch.setattr("src.backend.src.services.cache.time.time", lambda: now + 5)
    value, status = cache.get("key", "v1")
    assert value is None
    assert status == "stale"

    empty_cache = MemoryCache(ttl_seconds=1)
    assert empty_cache.ratio() == 0.0


def test_warnings_helpers():
    assert warning_service.build_missing_data_warning([]) == []
    warning_list = warning_service.build_missing_data_warning(["schools"])
    assert warning_list[0]["code"] == "MISSING_DATA"

    routing_warning = warning_service.build_routing_warning(["schools"], "reason")
    assert routing_warning["code"] == "ROUTING_FALLBACK_USED"


def test_routing_distance_variants():
    metrics = Metrics()
    result = routing.compute_distance((0, 0), (1, 1), routing_enabled=False, metrics=metrics)
    assert result.fallback_used is True
    assert metrics.routing_fallback_usage > 0

    result = routing.compute_distance((0, 0), (1, 1), routing_enabled=True, routing_provider="mock_road")
    assert result.mode == "road"

    result = routing.compute_distance((0, 0), (1, 1), routing_enabled=True, routing_provider="unknown", metrics=Metrics())
    assert result.fallback_used is True


def test_features_missing_branches(monkeypatch, test_db_path):
    monkeypatch.setattr(features.proximity, "get_nearest_schools", lambda *_a, **_k: [])
    monkeypatch.setattr(features.proximity, "get_nearest_parks", lambda *_a, **_k: [])
    monkeypatch.setattr(features.proximity, "get_nearest_police_stations", lambda *_a, **_k: [])
    monkeypatch.setattr(features.proximity, "get_nearest_playgrounds", lambda *_a, **_k: [])
    monkeypatch.setattr(features.proximity, "get_top_closest_properties", lambda *_a, **_k: [])

    results, missing = features.compute_proximity_factors((0, 0), test_db_path)
    assert "schools" in missing
    assert any(item.status == "missing" for item in results)

    assert features.compute_comparable_adjustment((0, 0), 100.0, test_db_path) == 0.0

    monkeypatch.setattr(
        features.proximity,
        "get_top_closest_properties",
        lambda *_a, **_k: [{"assessment_value": 200.0}, {"assessment_value": 100.0}],
    )
    assert features.compute_comparable_adjustment((0, 0), 100.0, test_db_path) == 10.0


def test_features_available_branches(monkeypatch, test_db_path):
    monkeypatch.setattr(features.proximity, "get_nearest_schools", lambda *_a, **_k: [{"distance_m": 100}])
    monkeypatch.setattr(features.proximity, "get_nearest_parks", lambda *_a, **_k: [{"distance_m": 1000}])
    monkeypatch.setattr(features.proximity, "get_nearest_police_stations", lambda *_a, **_k: [{"distance_m": 2500}])
    monkeypatch.setattr(features.proximity, "get_nearest_playgrounds", lambda *_a, **_k: [{"distance_m": 300}])
    monkeypatch.setattr(features.proximity, "get_top_closest_properties", lambda *_a, **_k: [{"assessment_value": 100}])

    results, missing = features.compute_proximity_factors((0, 0), test_db_path)
    assert not missing
    assert all(item.status == "available" for item in results)


def test_property_viewport_parse_cursor():
    assert property_viewport._parse_cursor("bad") == 0
