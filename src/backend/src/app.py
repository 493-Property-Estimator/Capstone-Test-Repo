from __future__ import annotations

import sys
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure repo root and src/ are importable
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))

from backend.src.config import load_settings
from backend.src.services.metrics import Metrics
from backend.src.services.cache import MemoryCache
from backend.src.api.search import router as search_router
from backend.src.api.locations import router as locations_router
from backend.src.api.estimates import router as estimates_router
from backend.src.api.layers import router as layers_router
from backend.src.api.properties import router as properties_router
from backend.src.api.health import router as health_router
from backend.src.jobs.precompute_grid import router as jobs_router
from data_sourcing.database import connect as connect_data_db, init_db as init_data_db

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
app.include_router(estimates_router, prefix="/api/v1", dependencies=[])
app.include_router(layers_router, prefix="/api/v1")
app.include_router(properties_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(health_router)

# Shared objects for routers
app.state.settings = settings
app.state.metrics = metrics
app.state.cache = cache
