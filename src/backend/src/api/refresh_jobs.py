from __future__ import annotations

from fastapi import APIRouter, Request

from src.backend.src.db.connection import connect

router = APIRouter()


@router.get("/jobs/refresh-status")
async def refresh_status(request: Request):
    settings = request.app.state.settings
    request_id = request.state.request_id
    runs = []
    try:
        with connect(settings.data_db_path) as conn:
            rows = conn.execute(
                """
                SELECT run_id, trigger_type, status, started_at, completed_at, correlation_id
                FROM workflow_runs
                ORDER BY started_at DESC
                LIMIT 10
                """
            ).fetchall()
            runs = [dict(row) for row in rows]
    except Exception:
        runs = []

    return {
        "request_id": request_id,
        "scheduler_enabled": settings.refresh_scheduler_enabled,
        "scheduler_active": bool(getattr(request.app.state, "refresh_scheduler_active", False)),
        "last_refresh_run": getattr(request.app.state, "last_refresh_run", None),
        "recent_runs": runs,
    }
