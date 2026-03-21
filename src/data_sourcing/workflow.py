"""Story 22 workflow orchestration for scheduled/on-demand refresh jobs."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Callable

from .config import REFRESH_BACKOFF_SECONDS, REFRESH_DEPENDENCIES, REFRESH_MAX_RETRIES
from .database import add_alert, record_dataset_version, utc_now
from .pipelines import (
    run_assessment_ingest,
    run_census_ingest,
    run_deduplication,
    run_geospatial_ingest,
    run_poi_standardization,
)

StepFn = Callable[[Any, str], dict[str, Any]]


def _new_run_id(prefix: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{timestamp}-{uuid.uuid4().hex[:6]}"


def run_refresh_workflow(
    conn,
    trigger: str = "on_demand",
    source_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    run_id = _new_run_id("refresh")
    started_at = utc_now()
    correlation_id = f"corr-{uuid.uuid4().hex[:10]}"

    conn.execute(
        """
        INSERT INTO workflow_runs (run_id, trigger_type, correlation_id, status, started_at)
        VALUES (?, ?, ?, 'running', ?)
        """,
        (run_id, trigger, correlation_id, started_at),
    )
    conn.commit()

    # Simulate required secret enforcement for scheduled runs.
    if trigger == "scheduled" and not os.getenv("OPEN_DATA_REFRESH_SECRET"):
        message = "required secret OPEN_DATA_REFRESH_SECRET missing for scheduled refresh"
        add_alert(conn, run_id, "error", message)
        conn.execute(
            """
            UPDATE workflow_runs
               SET status='failed', completed_at=?, errors_json=?
             WHERE run_id=?
            """,
            (utc_now(), json.dumps([message]), run_id),
        )
        conn.commit()
        return {
            "run_id": run_id,
            "status": "failed",
            "step_runs": [],
            "summary": {"promoted": [], "skipped": [], "failed": [], "reasons": {}},
            "warnings": [],
            "errors": [message],
            "completed_at": utc_now(),
        }

    step_map: dict[str, StepFn] = {
        "geospatial": lambda c, t: run_geospatial_ingest(c, trigger=t, source_overrides=source_overrides),
        "census": lambda c, t: run_census_ingest(c, trigger=t, source_overrides=source_overrides),
        "assessments": lambda c, t: run_assessment_ingest(c, trigger=t, source_overrides=source_overrides),
        "poi_standardization": lambda c, t: run_poi_standardization(
            c,
            trigger=t,
            taxonomy_version="v1",
            mapping_version="v1",
            source_overrides=source_overrides,
        ),
        "deduplication": lambda c, t: run_deduplication(c, trigger=t),
    }

    order = ["geospatial", "census", "assessments", "poi_standardization", "deduplication"]
    step_status: dict[str, str] = {}
    reasons: dict[str, str] = {}
    warnings: list[str] = []
    errors: list[str] = []
    step_runs: list[dict[str, Any]] = []

    for dataset in order:
        dep_failures = [dep for dep in REFRESH_DEPENDENCIES.get(dataset, []) if step_status.get(dep) != "succeeded"]
        step_id = f"step-{uuid.uuid4().hex[:8]}"
        step_started = utc_now()

        if dep_failures:
            reason = f"skipped due to failed dependency: {', '.join(dep_failures)}"
            step_status[dataset] = "skipped"
            reasons[dataset] = reason
            conn.execute(
                """
                INSERT INTO workflow_steps (
                    step_id, run_id, dataset_type, status, retry_count, started_at, completed_at,
                    warnings_json, errors_json
                ) VALUES (?, ?, ?, 'skipped', 0, ?, ?, '[]', ?)
                """,
                (step_id, run_id, dataset, step_started, utc_now(), json.dumps([reason])),
            )
            step_runs.append({"dataset": dataset, "status": "skipped", "retry_count": 0})
            continue

        retry_count = 0
        last_error: str | None = None
        result: dict[str, Any] | None = None
        while retry_count <= REFRESH_MAX_RETRIES:
            result = step_map[dataset](conn, "scheduled" if trigger == "scheduled" else "on_demand")
            if result.get("status") == "succeeded":
                break
            last_error = "; ".join(result.get("errors", [])) or "unknown step failure"
            retry_count += 1
            if retry_count <= REFRESH_MAX_RETRIES:
                time.sleep(REFRESH_BACKOFF_SECONDS)

        if result and result.get("status") == "succeeded":
            step_status[dataset] = "succeeded"
            if retry_count > 0:
                warnings.append(f"{dataset} succeeded after retry x{retry_count}")
            record_dataset_version(
                conn,
                dataset_type=f"refresh:{dataset}",
                version_id=result.get("run_id", step_id),
                source_version=None,
                provenance=f"refresh workflow {run_id}",
                run_id=run_id,
            )
            conn.execute(
                """
                INSERT INTO workflow_steps (
                    step_id, run_id, dataset_type, status, retry_count, started_at, completed_at,
                    warnings_json, errors_json
                ) VALUES (?, ?, ?, 'succeeded', ?, ?, ?, ?, '[]')
                """,
                (step_id, run_id, dataset, retry_count, step_started, utc_now(), json.dumps(result.get("warnings", []))),
            )
            step_runs.append({"dataset": dataset, "status": "succeeded", "retry_count": retry_count})
        else:
            step_status[dataset] = "failed"
            reason = last_error or "step failed"
            reasons[dataset] = reason
            errors.append(f"{dataset}: {reason}")
            add_alert(conn, run_id, "error", f"refresh step failed [{dataset}]: {reason}")
            conn.execute(
                """
                INSERT INTO workflow_steps (
                    step_id, run_id, dataset_type, status, retry_count, started_at, completed_at,
                    warnings_json, errors_json
                ) VALUES (?, ?, ?, 'failed', ?, ?, ?, '[]', ?)
                """,
                (step_id, run_id, dataset, retry_count, step_started, utc_now(), json.dumps([reason])),
            )
            step_runs.append({"dataset": dataset, "status": "failed", "retry_count": retry_count})

    promoted = [dataset for dataset, status in step_status.items() if status == "succeeded"]
    skipped = [dataset for dataset, status in step_status.items() if status == "skipped"]
    failed = [dataset for dataset, status in step_status.items() if status == "failed"]

    if failed and promoted:
        final_status = "partial_success"
    elif failed and not promoted:
        final_status = "failed"
    else:
        final_status = "succeeded"

    conn.execute(
        """
        INSERT INTO workflow_summaries (run_id, promoted_json, skipped_json, failed_json, reasons_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (run_id, json.dumps(promoted), json.dumps(skipped), json.dumps(failed), json.dumps(reasons)),
    )

    conn.execute(
        """
        UPDATE workflow_runs
           SET status=?, completed_at=?, warnings_json=?, errors_json=?
         WHERE run_id=?
        """,
        (final_status, utc_now(), json.dumps(warnings), json.dumps(errors), run_id),
    )
    conn.commit()

    return {
        "run_id": run_id,
        "status": final_status,
        "step_runs": step_runs,
        "summary": {
            "promoted": promoted,
            "skipped": skipped,
            "failed": failed,
            "reasons": reasons,
        },
        "warnings": warnings,
        "errors": errors,
        "completed_at": utc_now(),
    }
