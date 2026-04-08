from __future__ import annotations

import asyncio
import csv
import json
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from data_sourcing.service import IngestionService
from data_sourcing.source_fetcher import load_payload_for_source

router = APIRouter()

DATASET_SOURCE_KEYS = {
    "assessment_properties": "assessments.property_tax_csv",
    "schools": "geospatial.school_locations",
    "parks": "geospatial.parks",
    "playgrounds": "geospatial.playgrounds",
    "transit_stops": "transit.ets_stops",
}

ALLOWED_EXTENSIONS_BY_DATASET = {
    "assessment_properties": {"csv", "json", "geojson", "zip"},
    "schools": {"csv", "json", "geojson", "zip"},
    "parks": {"csv", "json", "geojson", "zip"},
    "playgrounds": {"csv", "json", "geojson", "zip"},
    "transit_stops": {"csv", "json", "geojson", "zip"},
}

SCHEMA_REQUIRED_FIELDS = {
    "assessment_properties": [
        {"assessmentvalue", "assessmentvalue", "assessedvalue"},
        {"lat", "latitude"},
        {"lon", "lng", "longitude"},
    ],
    "schools": [
        {"name", "schoolname", "schoolnam"},
        {"lat", "latitude"},
        {"lon", "lng", "longitude"},
    ],
    "parks": [
        {"name", "officialname", "officialn"},
        {"lat", "latitude"},
        {"lon", "lng", "longitude"},
    ],
    "playgrounds": [
        {"name"},
        {"lat", "latitude"},
        {"lon", "lng", "longitude"},
    ],
    "transit_stops": [
        {"stopid", "entityid"},
        {"name", "stopname"},
        {"lat", "latitude", "stoplat"},
        {"lon", "lng", "longitude", "stoplon"},
    ],
}


def _normalize_field_name(value: str | None) -> str:
    return "".join(ch.lower() for ch in str(value or "") if ch.isalnum())


def _parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_service_status(status: str | None) -> str:
    normalized = str(status or "").lower().strip()
    if normalized in {"succeeded", "success", "ok", "completed", "complete"}:
        return "success"
    if normalized in {"partial", "partial_success", "partially_successful"}:
        return "partial"
    return "failed"


def _extract_record_keys_from_path(path: Path, extension: str) -> set[str]:
    normalized_ext = extension.lower()

    if normalized_ext == "csv":
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            return {_normalize_field_name(item) for item in headers if item}

    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return set()

    payload = json.loads(text)
    keys: set[str] = set()

    if isinstance(payload, list):
        sample = payload[0] if payload else {}
    elif isinstance(payload, dict) and isinstance(payload.get("features"), list):
        features = payload.get("features") or []
        sample = features[0] if features else {}
        if isinstance(sample, dict):
            geometry = sample.get("geometry")
            coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
            if (
                isinstance(coordinates, (list, tuple))
                and len(coordinates) >= 2
                and isinstance(coordinates[0], (int, float))
                and isinstance(coordinates[1], (int, float))
            ):
                keys.update({"lat", "lon"})
            properties = sample.get("properties")
            if isinstance(properties, dict):
                keys.update(_normalize_field_name(item) for item in properties.keys())
                return {item for item in keys if item}
    elif isinstance(payload, dict):
        sample = payload
    else:
        sample = {}

    if isinstance(sample, dict):
        keys.update(_normalize_field_name(item) for item in sample.keys())
    return {item for item in keys if item}


def _validate_dataset_schema(dataset_type: str, file_path: Path, extension: str) -> tuple[bool, list[str]]:
    required_groups = SCHEMA_REQUIRED_FIELDS.get(dataset_type, [])

    try:
        available_fields = _extract_record_keys_from_path(file_path, extension)
    except Exception as exc:
        return False, [f"could not parse file: {exc}"]

    if not available_fields:
        return False, ["no readable fields found in uploaded file"]

    missing_groups: list[str] = []
    for alias_group in required_groups:
        if available_fields.intersection(alias_group):
            continue
        missing_groups.append("/".join(sorted(alias_group)))

    return len(missing_groups) == 0, missing_groups


def _safe_int(value: object) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _derive_counts_from_metadata(metadata: dict[str, object]) -> tuple[int, int]:
    ingested = 0
    skipped = 0

    counts = metadata.get("counts")
    if isinstance(counts, dict):
        raw = _safe_int(counts.get("raw"))
        normalized = _safe_int(counts.get("normalized"))
        linked = _safe_int(counts.get("linked"))
        unlinked = _safe_int(counts.get("unlinked"))
        ambiguous = _safe_int(counts.get("ambiguous"))

        ingested += linked or normalized
        skipped += unlinked + ambiguous + max(raw - normalized, 0)

    row_count = _safe_int(metadata.get("row_count"))
    if row_count:
        ingested += row_count

    datasets = metadata.get("datasets")
    if isinstance(datasets, list):
        for dataset in datasets:
            if not isinstance(dataset, dict):
                continue
            ingested += _safe_int(dataset.get("row_count"))

    return ingested, skipped


def _derive_counts_from_pipeline_payload(payload: object) -> tuple[int, int, int]:
    if not isinstance(payload, dict):
        return 0, 0, 0

    ingested = _safe_int(payload.get("row_count"))
    skipped = 0
    errors = 0

    counts = payload.get("counts")
    if isinstance(counts, dict):
        raw = _safe_int(counts.get("raw"))
        normalized = _safe_int(counts.get("normalized"))
        linked = _safe_int(counts.get("linked"))
        unlinked = _safe_int(counts.get("unlinked"))
        ambiguous = _safe_int(counts.get("ambiguous"))

        if not ingested:
            ingested += linked or normalized
        skipped += unlinked + ambiguous + max(raw - normalized, 0)

    datasets = payload.get("datasets")
    if isinstance(datasets, list):
        for dataset in datasets:
            if isinstance(dataset, dict):
                ingested += _safe_int(dataset.get("row_count"))

    errors += len(payload.get("errors") or [])
    return ingested, skipped, errors


def _collect_ingestion_stats(db_path: Path | str, ingestion_result: dict[str, object]) -> dict[str, int]:
    run_ids: list[str] = []
    fallback_ingested = 0
    fallback_skipped = 0
    fallback_errors = 0

    pipelines = ingestion_result.get("pipelines")
    if isinstance(pipelines, dict):
        for value in pipelines.values():
            if isinstance(value, dict):
                run_id = value.get("run_id")
                if run_id:
                    run_ids.append(str(run_id))
                ingested, skipped, errors = _derive_counts_from_pipeline_payload(value)
                fallback_ingested += ingested
                fallback_skipped += skipped
                fallback_errors += errors
                if str(value.get("status", "")).lower() == "skipped":
                    fallback_skipped += 1
                if str(value.get("status", "")).lower() == "failed":
                    fallback_errors += 1

    unique_run_ids = sorted(set(run_ids))
    if not unique_run_ids:
        return {
            "ingested": fallback_ingested,
            "skipped": fallback_skipped,
            "errors": fallback_errors,
        }

    ingested = 0
    skipped = 0
    errors = 0

    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" for _ in unique_run_ids)
            rows = conn.execute(
                f"""
                SELECT run_id, metadata_json, errors_json
                FROM run_logs
                WHERE run_id IN ({placeholders})
                """,
                unique_run_ids,
            ).fetchall()
    except sqlite3.Error:
        return {
            "ingested": fallback_ingested,
            "skipped": fallback_skipped,
            "errors": fallback_errors,
        }

    found_run_ids = set()
    for row in rows:
        found_run_ids.add(str(row["run_id"]))
        metadata_raw = row["metadata_json"] or "{}"
        errors_raw = row["errors_json"] or "[]"
        try:
            metadata = json.loads(metadata_raw)
            if not isinstance(metadata, dict):
                metadata = {}
        except json.JSONDecodeError:
            metadata = {}

        run_ingested, run_skipped = _derive_counts_from_metadata(metadata)
        ingested += run_ingested
        skipped += run_skipped

        try:
            parsed_errors = json.loads(errors_raw)
            if isinstance(parsed_errors, list):
                errors += len(parsed_errors)
        except json.JSONDecodeError:
            pass

    missing_runs = set(unique_run_ids) - found_run_ids
    if missing_runs:
        ingested += fallback_ingested
        skipped += fallback_skipped
        errors += fallback_errors

    return {
        "ingested": max(0, ingested),
        "skipped": max(0, skipped),
        "errors": max(0, errors),
    }


@router.post("/jobs/ingest")
async def ingest_uploaded_dataset(
    request: Request,
    source_name: str = Form(...),
    dataset_type: str = Form(...),
    trigger: str = Form("on_demand"),
    validate_only: str | bool = Form(False),
    overwrite: str | bool = Form(True),
    file: UploadFile = File(...),
):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    normalized_dataset_type = str(dataset_type or "").strip().lower()

    if normalized_dataset_type not in DATASET_SOURCE_KEYS:
        raise HTTPException(
            status_code=400,
            detail={
                "msg": (
                    "Unsupported dataset_type. "
                    f"Expected one of: {', '.join(sorted(DATASET_SOURCE_KEYS.keys()))}."
                )
            },
        )

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail={"msg": "Data file is required."})

    extension = Path(file.filename).suffix.lower().lstrip(".")
    allowed_extensions = ALLOWED_EXTENSIONS_BY_DATASET[normalized_dataset_type]
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail={
                "msg": (
                    f"Wrong datatype for {normalized_dataset_type}: .{extension or 'unknown'} is not allowed. "
                    f"Allowed: {', '.join(sorted(allowed_extensions))}."
                )
            },
        )

    source_key = DATASET_SOURCE_KEYS[normalized_dataset_type]
    temp_file_path: Path | None = None

    try:
        suffix = Path(file.filename).suffix or ".dat"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                temp_file.write(chunk)
            temp_file_path = Path(temp_file.name)
    finally:
        await file.close()

    source_overrides = {source_key: str(temp_file_path)}
    parsed_validate_only = _parse_bool(validate_only, False)
    parsed_overwrite = _parse_bool(overwrite, True)

    try:
        is_valid_schema, missing_requirements = _validate_dataset_schema(
            normalized_dataset_type,
            temp_file_path,
            extension,
        )
        if not is_valid_schema:
            raise HTTPException(
                status_code=400,
                detail={
                    "msg": (
                        f"File kind cannot be ingested for {normalized_dataset_type}. "
                        f"Missing required fields: {', '.join(missing_requirements)}."
                    )
                },
            )

        if parsed_validate_only:
            await asyncio.to_thread(
                load_payload_for_source,
                source_key,
                source_overrides,
                None,
            )
            return {
                "request_id": request_id,
                "status": "success",
                "message": "Validation successful. Dataset payload is ingestible.",
                "source_name": source_name,
                "dataset_type": normalized_dataset_type,
                "source_key": source_key,
                "trigger": trigger,
                "validate_only": True,
                "overwrite": parsed_overwrite,
            }

        service = IngestionService(db_path=request.app.state.settings.data_db_path)
        result = await asyncio.to_thread(
            service.ingest,
            [source_key],
            trigger,
            source_overrides,
            "v1",
            "v1",
        )

        status = _normalize_service_status(result.get("status"))
        message = {
            "success": "Ingestion completed successfully.",
            "partial": "Ingestion completed with partial success.",
            "failed": "Ingestion failed.",
        }[status]
        stats = _collect_ingestion_stats(
            request.app.state.settings.data_db_path,
            result,
        )

        return {
            "request_id": request_id,
            "status": status,
            "message": message,
            "source_name": source_name,
            "dataset_type": normalized_dataset_type,
            "source_key": source_key,
            "trigger": trigger,
            "validate_only": False,
            "overwrite": parsed_overwrite,
            "stats": stats,
            "ingestion_result": result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"msg": f"Ingestion could not be completed: {exc}"},
        ) from exc
    finally:
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except OSError:
                pass
