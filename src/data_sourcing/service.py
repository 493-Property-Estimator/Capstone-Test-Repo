"""Server-facing API for source-driven ingestion pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

from .config import DEFAULT_DB_PATH
from .database import add_alert, connect, init_db, inspect_db, log_source_check, upsert_source_config
from .pipelines import (
    run_assessment_ingest,
    run_census_ingest,
    run_crime_ingest,
    run_deduplication,
    run_geospatial_ingest,
    run_poi_standardization,
    run_transit_ingest,
)
from .source_fetcher import load_payload_for_source, resolve_source_location
from .source_registry import get_source_spec, list_sources
from .workflow import run_refresh_workflow

PIPELINE_ORDER = ["geospatial", "transit", "census", "crime", "assessments", "poi_standardization", "deduplication"]
PIPELINE_DEPENDENCIES = {
    "geospatial": [],
    "transit": [],
    "census": ["geospatial"],
    "crime": [],
    "assessments": ["geospatial"],
    "poi_standardization": ["geospatial"],
    "deduplication": ["poi_standardization"],
}


@dataclass
class IngestionService:
    db_path: Path | str = DEFAULT_DB_PATH

    def _connect(self):
        conn = connect(Path(self.db_path))
        init_db(conn)
        return conn

    def _resolved_db_path(self) -> str:
        return str(Path(self.db_path).expanduser().resolve())

    def init_database(self) -> dict[str, Any]:
        conn = self._connect()
        try:
            self._sync_source_configs(conn)
            conn.commit()
            return {"status": "ok", "db": self._resolved_db_path()}
        finally:
            conn.close()

    def database_path(self) -> dict[str, Any]:
        return {"db": self._resolved_db_path()}

    def database_summary(self) -> dict[str, Any]:
        conn = self._connect()
        try:
            self._sync_source_configs(conn)
            conn.commit()
            summary = inspect_db(conn)
            summary["db"] = self._resolved_db_path()
            return summary
        finally:
            conn.close()

    def _sync_source_configs(self, conn) -> None:
        for entry in list_sources():
            spec = dict(entry)
            source_key = spec.pop("key")
            upsert_source_config(conn, source_key, spec)

    def _expand_with_dependencies(self, pipelines: set[str]) -> list[str]:
        expanded = set(pipelines)
        changed = True
        while changed:
            changed = False
            for pipeline in list(expanded):
                for dep in PIPELINE_DEPENDENCIES.get(pipeline, []):
                    if dep not in expanded:
                        expanded.add(dep)
                        changed = True
        return [name for name in PIPELINE_ORDER if name in expanded]

    def _resolve_pipeline_plan(self, source_keys: list[str] | None) -> list[str]:
        if not source_keys:
            return PIPELINE_ORDER[:]

        requested: set[str] = set()
        for key in source_keys:
            spec = get_source_spec(key)
            pipeline = spec.get("pipeline")
            if not pipeline:
                raise ValueError(f"source '{key}' is missing pipeline mapping")
            requested.add(pipeline)
            for downstream in spec.get("downstream_pipelines", []):
                requested.add(downstream)

        return self._expand_with_dependencies(requested)

    def ingest(
        self,
        source_keys: list[str] | None = None,
        trigger: str = "manual",
        source_overrides: dict[str, str] | None = None,
        taxonomy_version: str = "v1",
        mapping_version: str = "v1",
    ) -> dict[str, Any]:
        conn = self._connect()
        try:
            self._sync_source_configs(conn)
            requested_keys = (
                source_keys[:]
                if source_keys
                else [item["key"] for item in list_sources(enabled_only=True)]
            )
            run_group_id = f"ingest-{uuid.uuid4().hex[:10]}"
            source_checks: list[dict[str, Any]] = []
            valid_source_keys: list[str] = []

            for source_key in requested_keys:
                try:
                    location_kind, resolved_location = resolve_source_location(
                        source_key,
                        overrides=source_overrides,
                    )
                    # Probe actual source accessibility now so one bad source does not stop others.
                    load_payload_for_source(source_key, source_overrides)
                    log_source_check(conn, run_group_id, source_key, "ok", None, resolved_location)
                    source_checks.append(
                        {
                            "source_key": source_key,
                            "status": "ok",
                            "location_kind": location_kind,
                            "resolved_location": resolved_location,
                            "message": None,
                        }
                    )
                    valid_source_keys.append(source_key)
                except Exception as exc:
                    message = str(exc)
                    log_source_check(conn, run_group_id, source_key, "error", message, None)
                    add_alert(conn, run_group_id, "error", f"source check failed [{source_key}]: {message}")
                    source_checks.append(
                        {
                            "source_key": source_key,
                            "status": "error",
                            "location_kind": None,
                            "resolved_location": None,
                            "message": message,
                        }
                    )

            conn.commit()

            if not valid_source_keys:
                return {
                    "status": "failed",
                    "pipelines": {},
                    "pipeline_order": [],
                    "source_keys": requested_keys,
                    "source_checks": source_checks,
                    "errors": ["all requested sources failed validation/load checks"],
                }

            plan = self._resolve_pipeline_plan(valid_source_keys)
            outputs: dict[str, Any] = {}
            for pipeline in plan:
                if pipeline == "geospatial":
                    geospatial_source_keys = [key for key in valid_source_keys if key.startswith("geospatial.")]
                    if not geospatial_source_keys:
                        outputs[pipeline] = {
                            "status": "skipped",
                            "reason": "no valid geospatial sources selected",
                            "datasets": [],
                            "warnings": [],
                            "errors": [],
                        }
                        continue
                    outputs[pipeline] = run_geospatial_ingest(
                        conn,
                        trigger=trigger,
                        source_keys=geospatial_source_keys,
                        source_overrides=source_overrides,
                    )
                elif pipeline == "census":
                    outputs[pipeline] = run_census_ingest(conn, trigger=trigger, source_overrides=source_overrides)
                elif pipeline == "crime":
                    crime_source_keys = [key for key in valid_source_keys if key.startswith("crime.")]
                    if not crime_source_keys:
                        outputs[pipeline] = {
                            "status": "skipped",
                            "reason": "no valid crime sources selected",
                            "warnings": [],
                            "errors": [],
                        }
                        continue
                    outputs[pipeline] = run_crime_ingest(
                        conn,
                        trigger=trigger,
                        source_overrides=source_overrides,
                        source_keys=crime_source_keys,
                    )
                elif pipeline == "transit":
                    transit_source_keys = [key for key in valid_source_keys if key.startswith("transit.")]
                    if not transit_source_keys:
                        outputs[pipeline] = {
                            "status": "skipped",
                            "reason": "no valid transit sources selected",
                            "warnings": [],
                            "errors": [],
                        }
                        continue
                    outputs[pipeline] = run_transit_ingest(
                        conn,
                        trigger=trigger,
                        source_keys=transit_source_keys,
                        source_overrides=source_overrides,
                    )
                elif pipeline == "assessments":
                    assessment_source_keys = [key for key in valid_source_keys if key.startswith("assessments.")]
                    outputs[pipeline] = run_assessment_ingest(
                        conn,
                        trigger=trigger,
                        source_overrides=source_overrides,
                        source_keys=assessment_source_keys or None,
                    )
                elif pipeline == "poi_standardization":
                    outputs[pipeline] = run_poi_standardization(
                        conn,
                        trigger=trigger,
                        taxonomy_version=taxonomy_version,
                        mapping_version=mapping_version,
                        source_overrides=source_overrides,
                    )
                elif pipeline == "deduplication":
                    outputs[pipeline] = run_deduplication(conn, trigger=trigger)
                else:
                    raise ValueError(f"unsupported pipeline '{pipeline}'")

            statuses = [result.get("status") for result in outputs.values()]
            if all(status == "succeeded" for status in statuses):
                final_status = "succeeded"
            elif any(status == "succeeded" for status in statuses):
                final_status = "partial_success"
            else:
                final_status = "failed"

            if any(item["status"] == "error" for item in source_checks) and final_status == "succeeded":
                final_status = "partial_success"

            return {
                "status": final_status,
                "pipelines": outputs,
                "pipeline_order": plan,
                "source_keys": requested_keys,
                "source_checks": source_checks,
            }
        finally:
            conn.close()

    def ingest_all(
        self,
        trigger: str = "manual",
        source_overrides: dict[str, str] | None = None,
        taxonomy_version: str = "v1",
        mapping_version: str = "v1",
    ) -> dict[str, Any]:
        return self.ingest(
            source_keys=None,
            trigger=trigger,
            source_overrides=source_overrides,
            taxonomy_version=taxonomy_version,
            mapping_version=mapping_version,
        )

    def run_refresh(self, trigger: str = "on_demand", source_overrides: dict[str, str] | None = None) -> dict[str, Any]:
        conn = self._connect()
        try:
            return run_refresh_workflow(conn, trigger=trigger, source_overrides=source_overrides)
        finally:
            conn.close()

    def list_sources(self, pipeline: str | None = None, enabled_only: bool = False) -> list[dict[str, Any]]:
        return list_sources(pipeline=pipeline, enabled_only=enabled_only)

    def get_source(self, source_key: str) -> dict[str, Any]:
        return get_source_spec(source_key)
