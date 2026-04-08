import builtins
import importlib
import sys

from src.estimator import property_estimator as pe


def test_estimator_init_handles_missing_proximity(monkeypatch):
    original_import = builtins.__import__
    original_estimator = sys.modules.get("estimator") or importlib.import_module("types").ModuleType("estimator")
    original_proximity = sys.modules.get("estimator.proximity") or importlib.import_module("types").ModuleType("estimator.proximity")

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 1 and name == "proximity" and globals and globals.get("__package__") == "estimator":
            raise ModuleNotFoundError("No module named 'estimator.proximity'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("estimator", None)
    sys.modules.pop("estimator.proximity", None)
    module = importlib.import_module("estimator")
    assert "get_nearest_schools" not in module.__all__

    sys.modules["estimator"] = original_estimator
    sys.modules["estimator.proximity"] = original_proximity


def test_road_graph_router_returns_road_distance(monkeypatch, tmp_path):
    router = pe._RoadGraphRouter(tmp_path / "db.sqlite")

    monkeypatch.setattr(pe.proximity_module, "_load_road_graph", lambda _path: {"graph": True})
    monkeypatch.setattr(pe.proximity_module, "_road_distances_from_origin", lambda *_a, **_k: {"a": 1})
    monkeypatch.setattr(pe.proximity_module, "_road_distance_to_target", lambda *_a, **_k: 123.4)

    result = router.route_distance(53.5, -113.5, 53.6, -113.6)
    assert result["routing_mode"] == "road"
    assert result["road_distance_m"] == 123.4
