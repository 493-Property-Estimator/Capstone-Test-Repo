from __future__ import annotations

from datetime import datetime, UTC, timedelta

from fastapi import APIRouter, Request

from backend.src.db.connection import connect
from backend.src.db.queries import get_latest_dataset_version
from backend.src.services.errors import error_response

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    request_id = request.state.request_id
    settings = request.app.state.settings
    status = "healthy"
    dependencies = []

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
    if settings.enable_routing:
        dependencies.append({"name": "routing_provider", "status": "degraded", "details": "fallback_only"})
        if status == "healthy":
            status = "degraded"
    else:
        dependencies.append({"name": "routing_provider", "status": "down", "details": "disabled"})
        if status == "healthy":
            status = "degraded"

    # Ingestion freshness
    version = get_latest_dataset_version(settings.data_db_path)
    if not version:
        dependencies.append({"name": "ingestion_freshness", "status": "degraded", "details": "no dataset version"})
        if status == "healthy":
            status = "degraded"
    else:
        dependencies.append({"name": "ingestion_freshness", "status": "ok", "details": version})

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
