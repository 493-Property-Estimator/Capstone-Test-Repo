import asyncio
import importlib
from types import SimpleNamespace

from starlette.requests import Request

from src.backend.src import app as app_module


class _DummyMetrics:
    def __init__(self):
        self.calls = []

    def record_request(self, latency_ms, is_error=False):
        self.calls.append((latency_ms, is_error))


class _DummyConn:
    def close(self):
        return None


def _dummy_connect(*_a, **_k):
    return _DummyConn()


def _dummy_init(*_a, **_k):
    return None


def test_add_request_id_and_metrics_error(monkeypatch):
    dummy_metrics = _DummyMetrics()
    monkeypatch.setattr(app_module, "metrics", dummy_metrics)

    scope = {"type": "http", "headers": []}
    request = Request(scope)

    async def _raise(_req):
        raise RuntimeError("boom")

    try:
        asyncio.run(app_module.add_request_id_and_metrics(request, _raise))
    except RuntimeError:
        pass
    assert dummy_metrics.calls and dummy_metrics.calls[-1][1] is True


def test_value_error_handler():
    scope = {"type": "http", "headers": []}
    request = Request(scope)
    response = asyncio.run(app_module.value_error_handler(request, ValueError("bad")))
    assert response.status_code == 400


def test_lifespan_initializes_and_cleans(monkeypatch):
    monkeypatch.setattr(app_module, "connect_data_db", _dummy_connect)
    monkeypatch.setattr(app_module, "init_data_db", _dummy_init)
    monkeypatch.setattr(app_module, "warm_estimator", lambda *_a, **_k: None)

    monkeypatch.setattr(
        app_module,
        "settings",
        SimpleNamespace(
            data_db_path="/tmp/none.db",
            refresh_scheduler_enabled=False,
        ),
    )

    async def _run():
        async with app_module.lifespan(app_module.app):
            assert app_module.app.state.refresh_scheduler_task is None
            assert app_module.app.state.refresh_scheduler_active is False

    try:
        asyncio.run(_run())
    except asyncio.CancelledError:
        pass


def test_app_import_adds_sys_path(monkeypatch):
    import sys as _sys
    # Remove existing paths to force append branches.
    removed = []
    for path in list(_sys.path):
        if path.endswith("/ECE_493/Capstone-Test-Repo") or path.endswith("/ECE_493/Capstone-Test-Repo/src"):
            _sys.path.remove(path)
            removed.append(path)
    try:
        importlib.reload(app_module)
    finally:
        for path in removed:
            if path not in _sys.path:
                _sys.path.append(path)


def test_refresh_scheduler_loop_exception(monkeypatch):
    class _DummyService:
        def __init__(self, db_path):
            self.db_path = db_path

        def run_refresh(self, *_a, **_k):
            raise RuntimeError("fail")

    monkeypatch.setattr(app_module, "IngestionService", _DummyService)

    async def _cancel_sleep(*_a, **_k):
        raise asyncio.CancelledError

    monkeypatch.setattr(app_module.asyncio, "sleep", _cancel_sleep)

    app_module.app.state.settings = SimpleNamespace(
        data_db_path="/tmp/none.db",
        refresh_schedule_seconds=1,
        refresh_schedule_min_seconds=1,
    )

    async def _run():
        task = asyncio.create_task(app_module._refresh_scheduler_loop())
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return
        raise AssertionError("Expected CancelledError")

    try:
        asyncio.run(_run())
    except asyncio.CancelledError:
        pass


def test_refresh_scheduler_loop_success(monkeypatch):
    class _DummyService:
        def __init__(self, db_path):
            self.db_path = db_path

        def run_refresh(self, *_a, **_k):
            return {"status": "ok"}

    monkeypatch.setattr(app_module, "IngestionService", _DummyService)

    async def _to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(app_module.asyncio, "to_thread", _to_thread)
    app_module.app.state.settings = SimpleNamespace(
        data_db_path="/tmp/none.db",
        refresh_schedule_seconds=1,
        refresh_schedule_min_seconds=1,
    )
    app_module.app.state.last_refresh_run = None

    async def _run():
        task = asyncio.create_task(app_module._refresh_scheduler_loop())
        # Yield until the loop records a result.
        for _ in range(10):
            if app_module.app.state.last_refresh_run is not None:
                break
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    try:
        asyncio.run(_run())
    except asyncio.CancelledError:
        pass
    assert app_module.app.state.last_refresh_run == {"status": "ok"}


def test_refresh_scheduler_loop_sets_error(monkeypatch):
    class _DummyService:
        def __init__(self, db_path):
            self.db_path = db_path

        def run_refresh(self, *_a, **_k):
            raise RuntimeError("boom")

    async def _to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(app_module, "IngestionService", _DummyService)
    monkeypatch.setattr(app_module.asyncio, "to_thread", _to_thread)

    app_module.app.state.settings = SimpleNamespace(
        data_db_path="/tmp/none.db",
        refresh_schedule_seconds=1,
        refresh_schedule_min_seconds=1,
    )
    app_module.app.state.last_refresh_run = None

    async def _run():
        task = asyncio.create_task(app_module._refresh_scheduler_loop())
        for _ in range(10):
            if app_module.app.state.last_refresh_run is not None:
                break
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    try:
        asyncio.run(_run())
    except asyncio.CancelledError:
        pass
    assert app_module.app.state.last_refresh_run["status"] == "failed"


def test_lifespan_refresh_scheduler_enabled(monkeypatch):
    monkeypatch.setattr(app_module, "connect_data_db", _dummy_connect)
    monkeypatch.setattr(app_module, "init_data_db", _dummy_init)
    monkeypatch.setattr(app_module, "warm_estimator", lambda *_a, **_k: None)

    monkeypatch.setattr(
        app_module,
        "settings",
        SimpleNamespace(
            data_db_path="/tmp/none.db",
            refresh_scheduler_enabled=True,
            refresh_schedule_seconds=1,
            refresh_schedule_min_seconds=1,
        ),
    )

    async def _fake_loop():
        await asyncio.sleep(0)

    monkeypatch.setattr(app_module, "_refresh_scheduler_loop", _fake_loop)

    async def _run():
        async with app_module.lifespan(app_module.app):
            assert app_module.app.state.refresh_scheduler_task is not None
        # task cancellation branch in lifespan

    try:
        asyncio.run(_run())
    except asyncio.CancelledError:
        pass
