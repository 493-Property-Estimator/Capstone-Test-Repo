from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure repo root and src/ are importable regardless of which backend tree this file lives in.
_THIS_FILE = Path(__file__).resolve()
REPO_ROOT = next(
    (
        parent
        for parent in _THIS_FILE.parents
        if (parent / "src").exists() and (parent / "backend").exists()
    ),
    _THIS_FILE.parents[2],
)
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))

from src.backend.src.config import load_settings
from src.backend.src.services.metrics import Metrics
from src.backend.src.services.cache import MemoryCache
from src.backend.src.api.search import router as search_router
from src.backend.src.api.locations import router as locations_router
from src.backend.src.api.estimates import router as estimates_router
from src.backend.src.api.layers import router as layers_router
from src.backend.src.api.properties import router as properties_router
from src.backend.src.api.health import router as health_router
from src.backend.src.api.refresh_jobs import router as refresh_jobs_router
from src.backend.src.jobs.precompute_grid import router as jobs_router
from src.backend.src.services.auth import require_estimate_access
from data_sourcing.database import connect as connect_data_db, init_db as init_data_db
from data_sourcing.service import IngestionService
from estimator import warm_estimator

settings = load_settings()
metrics = Metrics()
cache = MemoryCache(settings.cache_ttl_seconds)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def initialize_database() -> None:
    conn = connect_data_db(settings.data_db_path)
    try:
        init_data_db(conn)
    finally:
        conn.close()
    # Build heavy estimator dependencies once at startup so estimate requests
    # do not repeatedly pay initialization cost and hit time-budget failures.
    await asyncio.to_thread(warm_estimator, settings.data_db_path)
    app.state.refresh_scheduler_task = None
    app.state.refresh_scheduler_active = False
    app.state.last_refresh_run = None
    if settings.refresh_scheduler_enabled:
        app.state.refresh_scheduler_task = asyncio.create_task(_refresh_scheduler_loop())


@app.on_event("shutdown")
async def shutdown_background_tasks() -> None:
    task = getattr(app.state, "refresh_scheduler_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.middleware("http")
async def add_request_id_and_metrics(request: Request, call_next):
    start = time.time()
    request_id = request.headers.get("X-Request-Id", str(uuid4()))
    request.state.request_id = request_id
    response: Response
    try:
        response = await call_next(request)
    except Exception:
        metrics.record_request((time.time() - start) * 1000, is_error=True)
        raise
    latency_ms = (time.time() - start) * 1000
    metrics.record_request(latency_ms, is_error=response.status_code >= 400)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        status_code=400,
        content={
            "request_id": request_id,
            "error": {
                "code": "BAD_REQUEST",
                "message": str(exc),
                "details": {},
                "retryable": False,
            },
        },
    )


app.include_router(search_router, prefix="/api/v1")
app.include_router(locations_router, prefix="/api/v1")
app.include_router(estimates_router, prefix="/api/v1", dependencies=[Depends(require_estimate_access)])
app.include_router(layers_router, prefix="/api/v1")
app.include_router(properties_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(refresh_jobs_router, prefix="/api/v1")
app.include_router(health_router)

# Shared objects for routers
app.state.settings = settings
app.state.metrics = metrics
app.state.cache = cache


async def _refresh_scheduler_loop() -> None:
    while True:
        app.state.refresh_scheduler_active = True
        try:
            service = IngestionService(db_path=app.state.settings.data_db_path)
            run_result = await asyncio.to_thread(service.run_refresh, "scheduled", None)
            app.state.last_refresh_run = run_result
        except Exception as exc:
            app.state.last_refresh_run = {"status": "failed", "error": str(exc)}
        finally:
            app.state.refresh_scheduler_active = False
        await asyncio.sleep(
            max(app.state.settings.refresh_schedule_seconds, app.state.settings.refresh_schedule_min_seconds)
        )
