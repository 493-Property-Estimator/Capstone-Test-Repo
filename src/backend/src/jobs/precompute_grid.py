from __future__ import annotations

import math
from datetime import datetime, UTC

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.db.connection import connect

router = APIRouter()


@router.post("/jobs/precompute-grid")
async def precompute_grid(request: Request):
    settings = request.app.state.settings
    run_id = f"grid-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    warnings: list[str] = []
    try:
        _ensure_grid_table(settings.data_db_path)
        _compute_grid(settings.data_db_path, settings.grid_cell_size_deg)
        status = "succeeded"
    except Exception as exc:
        status = "failed"
        warnings.append(str(exc))
    return {
        "job_id": run_id,
        "status": status,
        "warnings": warnings,
    }


def _ensure_grid_table(db_path):
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS grid_features_prod (
                grid_id TEXT PRIMARY KEY,
                west REAL,
                south REAL,
                east REAL,
                north REAL,
                property_count INTEGER,
                mean_baseline_value REAL,
                median_baseline_value REAL,
                created_at TEXT
            )
            """
        )
        conn.commit()


def _compute_grid(db_path, cell_size_deg: float):
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT canonical_location_id, assessment_value, lat, lon
            FROM property_locations_prod
            WHERE lat IS NOT NULL AND lon IS NOT NULL AND assessment_value IS NOT NULL
            """
        ).fetchall()
        if not rows:
            return
        grid = {}
        for row in rows:
            lat = row["lat"]
            lon = row["lon"]
            gx = math.floor(lon / cell_size_deg)
            gy = math.floor(lat / cell_size_deg)
            grid_id = f"{gx}_{gy}"
            grid.setdefault(grid_id, []).append(row["assessment_value"])
        now = datetime.now(UTC).isoformat()
        conn.execute("DELETE FROM grid_features_prod")
        for grid_id, values in grid.items():
            values_sorted = sorted(values)
            count = len(values_sorted)
            mean_val = sum(values_sorted) / count
            median_val = values_sorted[count // 2]
            gx, gy = (int(part) for part in grid_id.split("_"))
            west = gx * cell_size_deg
            east = west + cell_size_deg
            south = gy * cell_size_deg
            north = south + cell_size_deg
            conn.execute(
                """
                INSERT INTO grid_features_prod (
                    grid_id, west, south, east, north, property_count,
                    mean_baseline_value, median_baseline_value, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (grid_id, west, south, east, north, count, mean_val, median_val, now),
            )
        conn.commit()
