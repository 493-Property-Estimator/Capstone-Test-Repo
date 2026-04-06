from __future__ import annotations

from datetime import UTC, datetime
import os
import threading
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.db.connection import connect
from backend.src.services.errors import error_response
from estimator import estimate_property_value

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    request_id = request.state.request_id
    settings = request.app.state.settings

    limited = _apply_health_rate_limit(request)
    if limited:
        return JSONResponse(
            status_code=429,
            content=error_response(
                request_id=request_id,
                code="HEALTH_RATE_LIMITED",
                message="Health endpoint polling rate limit exceeded.",
                details={"limit_per_minute": settings.health_rate_limit_per_minute},
                retryable=True,
            ),
        )

    status = "healthy"
    dependencies = []

    internal_details = {
        "api_process": "ok",
        "pid": os.getpid(),
        "active_threads": threading.active_count(),
        "thread_pool": "ok",
        "memory": _memory_health_status(settings),
    }
    dependencies.append({"name": "internal_service", "status": "ok", "details": internal_details})

    # Feature store
    try:
        with connect(settings.data_db_path) as conn:
            conn.execute("SELECT 1")
        dependencies.append({"name": "feature_store", "status": "ok", "details": ""})
    except Exception as exc:
        dependencies.append({"name": "feature_store", "status": "down", "details": str(exc)})
        status = "unhealthy"

    # Cache
    dependencies.append({"name": "cache_service", "status": "ok", "details": "in_memory"})

    # Routing provider
    if settings.enable_routing and settings.routing_provider == "mock_road":
        dependencies.append({"name": "routing_provider", "status": "ok", "details": "mock_road"})
    elif settings.enable_routing:
        dependencies.append({"name": "routing_provider", "status": "degraded", "details": "fallback_only"})
        if status == "healthy":
            status = "degraded"
    else:
        dependencies.append({"name": "routing_provider", "status": "down", "details": "disabled"})
        if status == "healthy":
            status = "degraded"

    # Valuation engine
    valuation_status = "ok" if callable(estimate_property_value) else "down"
    dependencies.append({"name": "valuation_engine", "status": valuation_status, "details": "import_check"})
    if valuation_status != "ok" and status == "healthy":
        status = "degraded"

    # Ingestion freshness
    freshness = _latest_dataset_freshness(settings.data_db_path, settings.ingestion_freshness_days)
    dependencies.append(freshness["dependency"])
    if freshness["dependency"]["status"] == "degraded" and status == "healthy":
        status = "degraded"

    return {"request_id": request_id, "status": status, "dependencies": dependencies}


@router.get("/metrics")
async def metrics(request: Request):
    request_id = request.state.request_id
    metrics = request.app.state.metrics
    return {
        "request_id": request_id,
        "request_count": metrics.request_count,
        "error_count": metrics.error_count,
        "cache_hit_ratio": metrics.cache_hit_ratio,
        "routing_fallback_usage": metrics.routing_fallback_usage,
        "avg_latency_ms": metrics.avg_latency_ms,
        "valuation_time_ms": metrics.valuation_time_ms,
    }


def _memory_health_status(settings) -> str:
    try:
        import resource

        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Conservative threshold for a small local service process.
        threshold_kb = max(1, int(settings.memory_high_rss_kb))
        return "high" if rss_kb > threshold_kb else "ok"
    except Exception:
        return "unknown"


def _latest_dataset_freshness(db_path, freshness_days: int) -> dict:
    try:
        with connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT version_id, promoted_at
                FROM dataset_versions
                ORDER BY promoted_at DESC
                LIMIT 1
                """
            ).fetchone()
    except Exception as exc:
        return {
            "dependency": {"name": "ingestion_freshness", "status": "degraded", "details": str(exc)},
        }

    if not row:
        return {
            "dependency": {"name": "ingestion_freshness", "status": "degraded", "details": "no dataset version"},
        }

    promoted_at = str(row["promoted_at"] or "").replace("Z", "+00:00")
    stale = False
    age_days = None
    try:
        promoted_dt = datetime.fromisoformat(promoted_at)
        if promoted_dt.tzinfo is None:
            promoted_dt = promoted_dt.replace(tzinfo=UTC)
        age_days = max((datetime.now(UTC) - promoted_dt).days, 0)
        stale = age_days > max(int(freshness_days), 1)
    except Exception:
        stale = False

    return {
        "dependency": {
            "name": "ingestion_freshness",
            "status": "degraded" if stale else "ok",
            "details": {"version_id": row["version_id"], "age_days": age_days},
        },
    }


def _apply_health_rate_limit(request: Request) -> bool:
    now = time.time()
    settings = request.app.state.settings
    window_seconds = max(0.1, float(settings.health_rate_limit_window_seconds))
    limit = max(1, int(settings.health_rate_limit_per_minute))
    stamps = getattr(request.app.state, "health_request_timestamps", None)
    if stamps is None:
        stamps = []
        request.app.state.health_request_timestamps = stamps
    request.app.state.health_request_timestamps = [ts for ts in stamps if now - ts < window_seconds]
    request.app.state.health_request_timestamps.append(now)
    return len(request.app.state.health_request_timestamps) > limit
