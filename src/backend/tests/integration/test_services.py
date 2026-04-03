from backend.src.services.validation import (
    validate_coordinates,
    validate_address,
    coords_in_bounds,
    validate_location_payload,
)
from backend.src.services.errors import error_response, validation_error_response
from backend.src.services.cache import MemoryCache
from backend.src.services.metrics import Metrics
from backend.src.services.routing import compute_distance
from backend.src.services.warnings import build_missing_data_warning, build_routing_warning
from backend.src.services.features import compute_proximity_factors, compute_comparable_adjustment, FactorResult


def test_validation_functions():
    assert validate_coordinates({"lat": 0, "lng": 0}) == []
    assert validate_coordinates({"lat": 200, "lng": 0})
    assert validate_address("123 Main St") == []
    assert validate_address("Main")
    assert coords_in_bounds({"lat": 53.5, "lng": -113.4})
    assert not coords_in_bounds({"lat": 0.0, "lng": 0.0})
    issues = validate_location_payload({"location": {"coordinates": {"lat": 200, "lng": 0}}})
    assert issues


def test_error_builders():
    err = error_response("req", "CODE", "msg", {"x": 1}, True)
    assert err["request_id"] == "req"
    issues = validate_coordinates({"lat": 200, "lng": 0})
    body, status = validation_error_response("req", issues, 422)
    assert status == 422
    assert body["error"]["details"]["errors"]


def test_cache_behavior():
    cache = MemoryCache(1)
    value, status = cache.get("k", "v1")
    assert value is None and status == "miss"
    cache.set("k", {"x": 1}, "v1")
    value, status = cache.get("k", "v1")
    assert value and status == "hit"
    value, status = cache.get("k", "v2")
    assert value is None and status == "stale"


def test_metrics_behavior():
    metrics = Metrics()
    metrics.record_request(10, is_error=False)
    metrics.record_request(20, is_error=True)
    metrics.record_valuation(30)
    metrics.record_routing_fallback()
    assert metrics.request_count == 2
    assert metrics.error_count == 1
    assert metrics.routing_fallback_usage == 1


def test_routing_fallback():
    result = compute_distance((53.5, -113.4), (53.5, -113.4), routing_enabled=False)
    assert result.fallback_used
    result2 = compute_distance((53.5, -113.4), (53.5, -113.4), routing_enabled=True)
    assert result2.fallback_used


def test_warning_builders():
    warnings = build_missing_data_warning(["crime"])
    assert warnings
    routing = build_routing_warning(["commute"], "routing_unavailable")
    assert routing


def test_features_with_monkeypatch(monkeypatch, test_db_path):
    from estimator import proximity

    monkeypatch.setattr(proximity, "get_nearest_schools", lambda *args, **kwargs: [{"distance_m": 100}])
    monkeypatch.setattr(proximity, "get_nearest_parks", lambda *args, **kwargs: [])
    monkeypatch.setattr(proximity, "get_nearest_police_stations", lambda *args, **kwargs: [])
    monkeypatch.setattr(proximity, "get_nearest_playgrounds", lambda *args, **kwargs: [])
    monkeypatch.setattr(proximity, "get_top_closest_properties", lambda *args, **kwargs: [])

    factors, missing = compute_proximity_factors((0, 0), test_db_path)
    assert factors
    assert "parks" in missing
    adjustment = compute_comparable_adjustment((0, 0), 100, test_db_path)
    assert adjustment == 0.0
