from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request

from src.backend.src.db.connection import connect
from src.data_sourcing import neighbourhood_valuation_models as nvm

router = APIRouter()


@router.post("/jobs/train-neighbourhood-value-models")
async def train_neighbourhood_value_models(request: Request):
    settings = request.app.state.settings
    run_id = f"neighbourhood-ml-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    warnings: list[str] = []
    metrics: dict[str, int | str | None] = {
        "model_count": 0,
        "neighbourhood_count": 0,
        "dataset_version": None,
    }
    try:
        _ensure_model_table(settings.data_db_path)
        metrics = _train_and_store(settings.data_db_path, warnings)
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


def _ensure_model_table(db_path):
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS neighbourhood_value_models_prod (
                neighbourhood TEXT,
                model_type TEXT,
                model_version TEXT,
                feature_schema_json TEXT,
                payload_json TEXT,
                train_count INTEGER,
                test_count INTEGER,
                r2 REAL,
                mae REAL,
                dataset_version TEXT,
                created_at TEXT,
                PRIMARY KEY (neighbourhood, model_type, model_version)
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


def _training_rows(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            pl.canonical_location_id,
            pl.neighbourhood,
            pl.assessment_value,
            pl.lot_size,
            pl.total_gross_area,
            pl.year_built,
            pl.zoning,
            pl.tax_class,
            pl.garage,
            pl.assessment_class_1,
            pa.bedrooms_estimated,
            pa.bathrooms_estimated
        FROM property_locations_prod pl
        LEFT JOIN property_attributes_prod pa
          ON pa.canonical_location_id = pl.canonical_location_id
        WHERE pl.assessment_value IS NOT NULL
          AND pl.neighbourhood IS NOT NULL
          AND TRIM(pl.neighbourhood) <> ''
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _train_and_store(db_path, warnings: list[str]) -> dict[str, int | str | None]:
    # `neighbourhood_valuation_models` detects optional pandas/sklearn at import time.
    # In dev it's common to `pip install` those deps after the backend has already started,
    # so reload the module here to re-evaluate availability without requiring a server restart.
    import importlib

    nvm_reloaded = importlib.reload(nvm)
    with connect(db_path) as conn:
        rows = _training_rows(conn)
        if not rows:
            warnings.append("No rows available for neighbourhood model training.")
            return {"model_count": 0, "neighbourhood_count": 0, "dataset_version": _dataset_version(conn)}

        trained = nvm_reloaded.train_neighbourhood_models(rows)
        if not trained:
            warnings.append(
                "Neighbourhood models were not trained because pandas/scikit-learn are unavailable. "
                "Install pandas + scikit-learn to enable ridge/RF training."
            )
            return {"model_count": 0, "neighbourhood_count": 0, "dataset_version": _dataset_version(conn)}

        dataset_version = _dataset_version(conn)
        now = datetime.now(UTC).isoformat()
        conn.execute("DELETE FROM neighbourhood_value_models_prod")
        for model in trained:
            metrics = model.metrics or {}
            conn.execute(
                """
                INSERT INTO neighbourhood_value_models_prod (
                    neighbourhood, model_type, model_version,
                    feature_schema_json, payload_json,
                    train_count, test_count, r2, mae,
                    dataset_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model.neighbourhood,
                    model.model_type,
                    model.version,
                    nvm_reloaded.serialize_feature_schema(model.feature_schema),
                    nvm_reloaded.serialize_payload(model.payload),
                    int(metrics.get("train_count") or 0),
                    int(metrics.get("test_count") or 0),
                    float(metrics.get("r2") or 0.0),
                    float(metrics.get("mae") or 0.0),
                    dataset_version,
                    now,
                ),
            )
        conn.commit()

        neighbourhoods = {m.neighbourhood for m in trained}
        return {
            "model_count": len(trained),
            "neighbourhood_count": len(neighbourhoods),
            "dataset_version": dataset_version,
        }
