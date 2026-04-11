from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from statistics import median

from fastapi import APIRouter, Request

from src.backend.src.db.connection import connect

router = APIRouter()


@router.post("/jobs/precompute-neighbourhood-model")
async def precompute_neighbourhood_model(request: Request):
    settings = request.app.state.settings
    run_id = f"neighbourhood-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    warnings: list[str] = []
    metrics: dict[str, int | str | None] = {
        "neighbourhood_count": 0,
        "flagged_neighbourhoods": 0,
        "dataset_version": None,
    }
    try:
        _ensure_neighbourhood_model_table(settings.data_db_path)
        metrics = _compute_neighbourhood_model(settings.data_db_path, warnings)
        status = "succeeded"
    except Exception as exc:
        status = "failed"
        warnings.append(str(exc))
    return {
        "job_id": run_id,
        "status": status,
        "warnings": warnings,
        "metrics": metrics,
    }


def _ensure_neighbourhood_model_table(db_path):
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS neighbourhood_model_prod (
                neighbourhood TEXT PRIMARY KEY,
                average_assessment REAL,
                median_assessment REAL,
                property_count INTEGER,
                centroid_lat REAL,
                centroid_lon REAL,
                dataset_version TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _dataset_version(conn) -> str | None:
    if not _table_exists(conn, "dataset_versions"):
        return None
    row = conn.execute(
        """
        SELECT version_id
        FROM dataset_versions
        ORDER BY promoted_at DESC
        LIMIT 1
        """
    ).fetchone()
    return row["version_id"] if row else None


def _compute_neighbourhood_model(db_path, warnings: list[str]) -> dict[str, int | str | None]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT neighbourhood, assessment_value, lat, lon
            FROM property_locations_prod
            WHERE neighbourhood IS NOT NULL
              AND TRIM(neighbourhood) <> ''
              AND assessment_value IS NOT NULL
              AND lat IS NOT NULL
              AND lon IS NOT NULL
            """
        ).fetchall()
        if not rows:
            warnings.append("No property rows available for neighbourhood model precompute.")
            return {"neighbourhood_count": 0, "flagged_neighbourhoods": 0, "dataset_version": _dataset_version(conn)}

        dataset_version = _dataset_version(conn)
        now = datetime.now(UTC).isoformat()

        values_by_name: dict[str, list[float]] = defaultdict(list)
        lats_by_name: dict[str, list[float]] = defaultdict(list)
        lons_by_name: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            name = str(row["neighbourhood"]).strip()
            try:
                values_by_name[name].append(float(row["assessment_value"]))
                lats_by_name[name].append(float(row["lat"]))
                lons_by_name[name].append(float(row["lon"]))
            except (TypeError, ValueError):
                continue

        conn.execute("DELETE FROM neighbourhood_model_prod")
        flagged = 0
        for name, values in values_by_name.items():
            avg_val = sum(values) / len(values)
            med_val = float(median(values))
            centroid_lat = sum(lats_by_name[name]) / len(lats_by_name[name])
            centroid_lon = sum(lons_by_name[name]) / len(lons_by_name[name])

            if avg_val < 10_000 or avg_val > 10_000_000:
                flagged += 1
                warnings.append(f"Outlier average_assessment for neighbourhood '{name}'")
                avg_val = max(10_000.0, min(avg_val, 10_000_000.0))

            conn.execute(
                """
                INSERT INTO neighbourhood_model_prod (
                    neighbourhood,
                    average_assessment,
                    median_assessment,
                    property_count,
                    centroid_lat,
                    centroid_lon,
                    dataset_version,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    float(avg_val),
                    float(med_val),
                    int(len(values)),
                    float(centroid_lat),
                    float(centroid_lon),
                    dataset_version,
                    now,
                ),
            )
        conn.commit()

        return {
            "neighbourhood_count": len(values_by_name),
            "flagged_neighbourhoods": flagged,
            "dataset_version": dataset_version,
        }
