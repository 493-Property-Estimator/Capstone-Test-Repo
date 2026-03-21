"""Pipelines for stories 17-21: sourcing, refinement, and DB insertion."""

from __future__ import annotations

import json
import math
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from .config import (
    ASSESSMENT_AMBIGUOUS_RATE_LIMIT,
    ASSESSMENT_INVALID_RATE_LIMIT,
    ASSESSMENT_UNLINKED_RATE_LIMIT,
    CENSUS_COVERAGE_THRESHOLD,
    DEDUPE_AUTO_MERGE_THRESHOLD,
    DEDUPE_MAX_DISTANCE_METERS,
    DEDUPE_REVIEW_THRESHOLD,
    GEOSPATIAL_DATASETS,
    GEOSPATIAL_REPAIR_RATE_LIMIT,
    GEOSPATIAL_SIZE_LIMIT_BYTES,
    UNMAPPED_POLICY,
    UNMAPPED_RATE_LIMIT,
)
from .database import add_alert, record_dataset_version, transaction, upsert_run_log, utc_now
from .source_fetcher import load_payload_for_source
from .source_registry import get_source_spec
from .source_loader import require_fields


def _new_run_id(prefix: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{timestamp}-{uuid.uuid4().hex[:6]}"


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "").replace("$", "")
            if cleaned == "":
                return None
            return float(cleaned)
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_geometry_points(record: dict[str, Any]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    raw_points = record.get("geometry_points")
    if isinstance(raw_points, list):
        for raw_point in raw_points:
            if not isinstance(raw_point, (list, tuple)) or len(raw_point) < 2:
                continue
            lon = _safe_float(raw_point[0])
            lat = _safe_float(raw_point[1])
            if lon is not None and lat is not None:
                points.append((lon, lat))

    if points:
        return points

    start_lon = _safe_float(record.get("start_lon"))
    start_lat = _safe_float(record.get("start_lat"))
    end_lon = _safe_float(record.get("end_lon"))
    end_lat = _safe_float(record.get("end_lat"))
    if None not in (start_lon, start_lat, end_lon, end_lat):
        return [(start_lon, start_lat), (end_lon, end_lat)]  # type: ignore[arg-type]

    lon = _safe_float(record.get("lon"))
    lat = _safe_float(record.get("lat"))
    if lon is not None and lat is not None:
        return [(lon, lat)]
    return []


def _polyline_length_m(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for idx in range(len(points) - 1):
        lon1, lat1 = points[idx]
        lon2, lat2 = points[idx + 1]
        total += _distance_meters(lat1, lon1, lat2, lon2)
    return total


def run_geospatial_ingest(
    conn,
    trigger: str = "manual",
    datasets: tuple[str, ...] = GEOSPATIAL_DATASETS,
    source_keys: list[str] | None = None,
    source_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    run_id = _new_run_id("geo")
    started_at = utc_now()
    warnings: list[str] = []
    errors: list[str] = []
    results: list[dict[str, Any]] = []

    geom_map = {
        "roads": "MultiLineString",
        "boundaries": "MultiPolygon",
        "pois": "Point",
    }

    if source_keys is not None:
        geospatial_sources = [key for key in source_keys if key.startswith("geospatial.")]
    else:
        geospatial_sources = [f"geospatial.{dataset}" for dataset in datasets]

    refined_by_dataset: dict[str, list[dict[str, Any]]] = {dataset: [] for dataset in GEOSPATIAL_DATASETS}
    repair_counts: dict[str, int] = {dataset: 0 for dataset in GEOSPATIAL_DATASETS}
    raw_counts: dict[str, int] = {dataset: 0 for dataset in GEOSPATIAL_DATASETS}
    source_versions: dict[str, str | None] = {dataset: None for dataset in GEOSPATIAL_DATASETS}
    roads_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    road_segments: list[dict[str, Any]] = []
    entity_key_counts: dict[tuple[str, str, str], int] = defaultdict(int)

    for source_key in geospatial_sources:
        try:
            spec = get_source_spec(source_key)
            payload = load_payload_for_source(source_key, source_overrides)
        except Exception as exc:
            errors.append(f"failed loading source {source_key}: {exc}")
            continue

        dataset_suffix = source_key.split(".", 1)[1]
        if dataset_suffix in GEOSPATIAL_DATASETS:
            dataset = dataset_suffix
        else:
            dataset = spec.get("target_dataset", "pois")
        if dataset not in GEOSPATIAL_DATASETS:
            errors.append(f"{source_key} has unsupported target dataset '{dataset}'")
            continue

        if payload.size_bytes > GEOSPATIAL_SIZE_LIMIT_BYTES:
            errors.append(f"{source_key} exceeds size limit")
            continue

        source_versions[dataset] = payload.metadata.get("version") or source_versions[dataset]
        raw_counts[dataset] += len(payload.records)

        for record in payload.records:
            missing = require_fields(record, ("entity_id",))
            if missing:
                errors.append(f"{source_key} missing fields {missing} for record {record.get('entity_id', 'unknown')}")
                continue

            source_id = str(record.get("source_id") or source_key)
            base_entity_id = str(record["entity_id"])
            raw_category = record.get("raw_category")
            if raw_category in (None, "") and dataset in {"roads", "pois"}:
                raw_category = record.get("fclass")
            entity_key = (dataset, source_id, base_entity_id)
            entity_key_counts[entity_key] += 1
            dup_index = entity_key_counts[entity_key]
            entity_id = base_entity_id if dup_index == 1 else f"{base_entity_id}__dup{dup_index}"
            if dup_index > 1:
                warnings.append(
                    f"{source_key}: duplicate entity_id '{base_entity_id}' for source '{source_id}'"
                    f" disambiguated as '{entity_id}'"
                )

            name = str(record.get("name") or record.get("road_name") or entity_id).strip()

            points = _extract_geometry_points(record)
            if not points:
                errors.append(f"{source_key} missing geometry for {entity_id}")
                continue

            center_lon = sum(p[0] for p in points) / len(points)
            center_lat = sum(p[1] for p in points) / len(points)
            lon = center_lon
            lat = center_lat

            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                if -180 <= lat <= 180 and -90 <= lon <= 90:
                    lon, lat = lat, lon
                    repair_counts[dataset] += 1
                    warnings.append(f"{source_key}: swapped lon/lat repaired for {entity_id}")
                else:
                    errors.append(f"{source_key} out-of-bounds coordinates for {entity_id}")
                    continue

            refined_by_dataset[dataset].append(
                {
                    "run_id": run_id,
                    "dataset_type": dataset,
                    "entity_id": entity_id,
                    "source_id": source_id,
                    "name": name,
                    "raw_category": raw_category,
                    "canonical_geom_type": geom_map[dataset],
                    "lon": float(lon),
                    "lat": float(lat),
                    "source_version": payload.metadata.get("version"),
                    "updated_at": payload.metadata.get("publish_date"),
                }
            )

            if dataset == "roads":
                road_id = str(record.get("road_id") or entity_id)
                road_name = str(record.get("road_name") or record.get("name") or road_id).strip()
                road_type = record.get("road_type") or raw_category or record.get("fclass")
                road_key = (road_id, source_id)
                if road_key not in roads_by_key:
                    roads_by_key[road_key] = {
                        "run_id": run_id,
                        "road_id": road_id,
                        "source_id": source_id,
                        "road_name": road_name,
                        "road_type": road_type,
                        "source_version": payload.metadata.get("version"),
                        "updated_at": payload.metadata.get("publish_date"),
                        "metadata_json": json.dumps({}),
                    }

                start_lon, start_lat = points[0]
                end_lon, end_lat = points[-1]
                segment_center_lon = sum(p[0] for p in points) / len(points)
                segment_center_lat = sum(p[1] for p in points) / len(points)
                lane_count = _safe_int(record.get("lane_count") or record.get("lanes"))
                sequence_no = _safe_int(record.get("sequence_no") or record.get("segment_sequence"))

                road_segments.append(
                    {
                        "run_id": run_id,
                        "segment_id": str(record.get("segment_id") or entity_id),
                        "road_id": road_id,
                        "source_id": source_id,
                        "sequence_no": sequence_no,
                        "segment_name": name,
                        "segment_type": road_type,
                        "lane_count": lane_count,
                        "start_lon": start_lon,
                        "start_lat": start_lat,
                        "end_lon": end_lon,
                        "end_lat": end_lat,
                        "center_lon": segment_center_lon,
                        "center_lat": segment_center_lat,
                        "length_m": _polyline_length_m(points),
                        "geometry_json": json.dumps([[p[0], p[1]] for p in points]),
                        "source_version": payload.metadata.get("version"),
                        "updated_at": payload.metadata.get("publish_date"),
                    }
                )

    for dataset, refined in refined_by_dataset.items():
        if raw_counts[dataset]:
            repair_rate = repair_counts[dataset] / raw_counts[dataset]
            if repair_rate > GEOSPATIAL_REPAIR_RATE_LIMIT:
                errors.append(f"{dataset} geometry repair rate {repair_rate:.2%} exceeds threshold")

        dup_count = len(refined) - len({(r["entity_id"], r["source_id"]) for r in refined})
        if dup_count > 0:
            errors.append(f"{dataset} duplicate entity/source pair count={dup_count}")

        conn.execute("DELETE FROM geospatial_staging WHERE run_id=? AND dataset_type=?", (run_id, dataset))
        conn.executemany(
            """
            INSERT INTO geospatial_staging (
                run_id, dataset_type, entity_id, source_id, name, raw_category,
                canonical_geom_type, lon, lat, source_version, updated_at
            ) VALUES (
                :run_id, :dataset_type, :entity_id, :source_id, :name, :raw_category,
                :canonical_geom_type, :lon, :lat, :source_version, :updated_at
            )
            """,
            refined,
        )

        if refined:
            results.append(
                {
                    "type": dataset,
                    "version": source_versions[dataset],
                    "row_count": len(refined),
                    "qa_status": "pass",
                    "promotion_status": "pending",
                    "warnings": [],
                }
            )

    segment_dups = len(road_segments) - len({(s["segment_id"], s["source_id"]) for s in road_segments})
    if segment_dups > 0:
        errors.append(f"roads duplicate segment/source pair count={segment_dups}")

    conn.execute("DELETE FROM roads_staging WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM road_segments_staging WHERE run_id=?", (run_id,))
    if roads_by_key:
        conn.executemany(
            """
            INSERT INTO roads_staging (
                run_id, road_id, source_id, road_name, road_type,
                source_version, updated_at, metadata_json
            ) VALUES (
                :run_id, :road_id, :source_id, :road_name, :road_type,
                :source_version, :updated_at, :metadata_json
            )
            """,
            list(roads_by_key.values()),
        )
    if road_segments:
        conn.executemany(
            """
            INSERT INTO road_segments_staging (
                run_id, segment_id, road_id, source_id, sequence_no, segment_name,
                segment_type, lane_count, start_lon, start_lat, end_lon, end_lat,
                center_lon, center_lat, length_m, geometry_json, source_version, updated_at
            ) VALUES (
                :run_id, :segment_id, :road_id, :source_id, :sequence_no, :segment_name,
                :segment_type, :lane_count, :start_lon, :start_lat, :end_lon, :end_lat,
                :center_lon, :center_lat, :length_m, :geometry_json, :source_version, :updated_at
            )
            """,
            road_segments,
        )

    status = "failed" if errors else "succeeded"
    if not errors:
        dataset_types = [result["type"] for result in results]
        try:
            with transaction(conn):
                for dataset in dataset_types:
                    conn.execute("DELETE FROM geospatial_prod WHERE dataset_type=?", (dataset,))
                    conn.execute(
                        """
                        INSERT INTO geospatial_prod (
                            dataset_type, entity_id, source_id, name, raw_category,
                            canonical_geom_type, lon, lat, source_version, updated_at
                        )
                        SELECT dataset_type, entity_id, source_id, name, raw_category,
                               canonical_geom_type, lon, lat, source_version, updated_at
                        FROM geospatial_staging
                        WHERE run_id=? AND dataset_type=?
                        """,
                        (run_id, dataset),
                    )
                if "roads" in dataset_types:
                    conn.execute("DELETE FROM road_segments_prod")
                    conn.execute("DELETE FROM roads_prod")
                    conn.execute(
                        """
                        INSERT INTO roads_prod (
                            road_id, source_id, road_name, road_type, source_version, updated_at, metadata_json
                        )
                        SELECT road_id, source_id, road_name, road_type, source_version, updated_at, metadata_json
                        FROM roads_staging
                        WHERE run_id=?
                        """,
                        (run_id,),
                    )
                    conn.execute(
                        """
                        INSERT INTO road_segments_prod (
                            segment_id, road_id, source_id, sequence_no, segment_name, segment_type, lane_count,
                            start_lon, start_lat, end_lon, end_lat, center_lon, center_lat, length_m, geometry_json,
                            source_version, updated_at
                        )
                        SELECT segment_id, road_id, source_id, sequence_no, segment_name, segment_type, lane_count,
                               start_lon, start_lat, end_lon, end_lat, center_lon, center_lat, length_m, geometry_json,
                               source_version, updated_at
                        FROM road_segments_staging
                        WHERE run_id=?
                        """,
                        (run_id,),
                    )
            for result in results:
                result["promotion_status"] = "promoted"
                if result["type"] == "roads":
                    result["road_count"] = len(roads_by_key)
                    result["segment_count"] = len(road_segments)
                record_dataset_version(
                    conn,
                    dataset_type=f"geospatial:{result['type']}",
                    version_id=result.get("version") or run_id,
                    source_version=result.get("version"),
                    provenance="open geospatial source",
                    run_id=run_id,
                )
        except Exception as exc:
            status = "failed"
            errors.append(f"promotion failed: {exc}")
            add_alert(conn, run_id, "error", f"geospatial promotion failed: {exc}")

    if errors:
        for result in results:
            result["qa_status"] = "fail"
            result["promotion_status"] = "failed"

    completed_at = utc_now()
    metadata = {"datasets": results}
    upsert_run_log(
        conn,
        run_id=run_id,
        story="017",
        trigger_type=trigger,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        warnings=warnings,
        errors=errors,
        metadata=metadata,
    )
    conn.commit()
    return {
        "run_id": run_id,
        "status": status,
        "datasets": results,
        "warnings": warnings,
        "errors": errors,
        "completed_at": completed_at,
    }


def run_census_ingest(conn, trigger: str = "manual", source_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    run_id = _new_run_id("census")
    started_at = utc_now()
    warnings: list[str] = []
    errors: list[str] = []

    payload = load_payload_for_source("census.neighbourhood_indicators", source_overrides)

    refined: list[dict[str, Any]] = []
    missing_areas: list[str] = []
    map_table = payload.metadata.get("area_map", {})

    for record in payload.records:
        missing = require_fields(record, ("source_area_id", "geography_level", "population", "households", "area_sq_km"))
        if missing:
            errors.append(f"census missing fields {missing}")
            continue

        area_id = map_table.get(record["source_area_id"])
        if not area_id:
            missing_areas.append(record["source_area_id"])
            continue

        suppressed = bool(record.get("suppressed_income", False))
        income = record.get("median_income")
        limited_accuracy = 1 if suppressed else 0
        if suppressed and income is None:
            income = 0
            warnings.append(f"suppressed value fallback for area {area_id}")

        population = int(record["population"])
        households = int(record["households"])
        area_sq_km = float(record["area_sq_km"])
        if population < 0 or households < 0 or area_sq_km <= 0:
            errors.append(f"invalid census values for area {area_id}")
            continue

        refined.append(
            {
                "run_id": run_id,
                "area_id": area_id,
                "geography_level": record["geography_level"],
                "population": population,
                "households": households,
                "median_income": income,
                "area_sq_km": area_sq_km,
                "population_density": population / area_sq_km,
                "limited_accuracy": limited_accuracy,
            }
        )

    coverage_percent = len(refined) / max(len(payload.records), 1)
    if missing_areas:
        warnings.append(f"unmapped areas: {sorted(set(missing_areas))}")
    if coverage_percent < CENSUS_COVERAGE_THRESHOLD:
        errors.append(f"coverage below threshold: {coverage_percent:.2%}")

    conn.execute("DELETE FROM census_staging WHERE run_id=?", (run_id,))
    conn.executemany(
        """
        INSERT INTO census_staging (
            run_id, area_id, geography_level, population, households, median_income,
            area_sq_km, population_density, limited_accuracy
        ) VALUES (
            :run_id, :area_id, :geography_level, :population, :households, :median_income,
            :area_sq_km, :population_density, :limited_accuracy
        )
        """,
        refined,
    )

    status = "failed" if errors else "succeeded"
    promotion_status = "failed"
    qa_status = "fail" if errors else "pass"

    if not errors:
        try:
            with transaction(conn):
                conn.execute("DELETE FROM census_prod")
                conn.execute(
                    """
                    INSERT INTO census_prod (
                        area_id, geography_level, population, households, median_income,
                        area_sq_km, population_density, limited_accuracy
                    )
                    SELECT area_id, geography_level, population, households, median_income,
                           area_sq_km, population_density, limited_accuracy
                    FROM census_staging WHERE run_id=?
                    """,
                    (run_id,),
                )
            promotion_status = "promoted"
            record_dataset_version(
                conn,
                dataset_type="census",
                version_id=str(payload.metadata.get("collection_year", run_id)),
                source_version=str(payload.metadata.get("collection_year")),
                provenance="municipal census",
                run_id=run_id,
            )
        except Exception as exc:
            status = "failed"
            errors.append(f"promotion failed: {exc}")
            add_alert(conn, run_id, "error", f"census promotion failed: {exc}")

    completed_at = utc_now()
    metadata = {
        "census_year": payload.metadata.get("collection_year"),
        "coverage_percent": coverage_percent,
        "qa_status": qa_status,
        "promotion_status": promotion_status,
        "row_count": len(refined),
    }
    upsert_run_log(
        conn,
        run_id=run_id,
        story="018",
        trigger_type=trigger,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        warnings=warnings,
        errors=errors,
        metadata=metadata,
    )
    conn.commit()

    return {
        "run_id": run_id,
        "status": status,
        "census_year": payload.metadata.get("collection_year"),
        "coverage_percent": coverage_percent,
        "qa_status": qa_status,
        "promotion_status": promotion_status,
        "warnings": warnings,
        "errors": errors,
        "completed_at": completed_at,
    }


def run_assessment_ingest(
    conn,
    trigger: str = "manual",
    source_overrides: dict[str, str] | None = None,
    source_key: str = "assessments.property_tax",
) -> dict[str, Any]:
    run_id = _new_run_id("assess")
    started_at = utc_now()
    warnings: list[str] = []
    errors: list[str] = []

    payload = load_payload_for_source(source_key, source_overrides)
    assessment_year = int(payload.metadata.get("assessment_year", 0))

    refined: list[dict[str, Any]] = []
    full_records: list[dict[str, Any]] = []
    quarantined = 0

    for record in payload.records:
        source_id = str(record.get("source_id") or source_key)
        record_id = str(record.get("record_id") or record.get("account_number") or f"missing-{quarantined + 1}")
        missing = require_fields(record, ("record_id", "assessment_value", "parcel_id", "lat", "lon"))
        if missing:
            quarantined += 1
            full_records.append(
                {
                    "run_id": run_id,
                    "record_id": record_id,
                    "source_id": source_id,
                    "assessment_year": assessment_year,
                    "canonical_location_id": None,
                    "assessment_value": _safe_float(record.get("assessment_value")),
                    "suite": record.get("suite"),
                    "house_number": record.get("house_number"),
                    "street_name": record.get("street_name"),
                    "neighbourhood_id": record.get("neighbourhood_id"),
                    "neighbourhood": record.get("neighbourhood"),
                    "ward": record.get("ward"),
                    "tax_class": record.get("tax_class"),
                    "garage": record.get("garage"),
                    "assessment_class_1": record.get("assessment_class_1"),
                    "assessment_class_2": record.get("assessment_class_2"),
                    "assessment_class_3": record.get("assessment_class_3"),
                    "assessment_class_pct_1": _safe_float(record.get("assessment_class_pct_1")),
                    "assessment_class_pct_2": _safe_float(record.get("assessment_class_pct_2")),
                    "assessment_class_pct_3": _safe_float(record.get("assessment_class_pct_3")),
                    "lat": _safe_float(record.get("lat")),
                    "lon": _safe_float(record.get("lon")),
                    "point_location": record.get("point_location"),
                    "link_method": "unlinked",
                    "confidence": 0.0,
                    "ambiguous": 0,
                    "quarantined": 1,
                    "reason_code": f"missing_fields:{','.join(missing)}",
                    "raw_record_json": json.dumps(record, default=str),
                }
            )
            refined.append(
                {
                    "run_id": run_id,
                    "record_id": record_id,
                    "assessment_year": assessment_year,
                    "canonical_location_id": None,
                    "assessment_value": None,
                    "link_method": "unlinked",
                    "confidence": 0.0,
                    "ambiguous": 0,
                    "quarantined": 1,
                    "reason_code": f"missing_fields:{','.join(missing)}",
                }
            )
            continue

        value = _safe_float(record.get("assessment_value"))
        if value is None or value <= 0:
            quarantined += 1
            full_records.append(
                {
                    "run_id": run_id,
                    "record_id": record_id,
                    "source_id": source_id,
                    "assessment_year": assessment_year,
                    "canonical_location_id": None,
                    "assessment_value": None,
                    "suite": record.get("suite"),
                    "house_number": record.get("house_number"),
                    "street_name": record.get("street_name"),
                    "neighbourhood_id": record.get("neighbourhood_id"),
                    "neighbourhood": record.get("neighbourhood"),
                    "ward": record.get("ward"),
                    "tax_class": record.get("tax_class"),
                    "garage": record.get("garage"),
                    "assessment_class_1": record.get("assessment_class_1"),
                    "assessment_class_2": record.get("assessment_class_2"),
                    "assessment_class_3": record.get("assessment_class_3"),
                    "assessment_class_pct_1": _safe_float(record.get("assessment_class_pct_1")),
                    "assessment_class_pct_2": _safe_float(record.get("assessment_class_pct_2")),
                    "assessment_class_pct_3": _safe_float(record.get("assessment_class_pct_3")),
                    "lat": _safe_float(record.get("lat")),
                    "lon": _safe_float(record.get("lon")),
                    "point_location": record.get("point_location"),
                    "link_method": "unlinked",
                    "confidence": 0.0,
                    "ambiguous": 0,
                    "quarantined": 1,
                    "reason_code": "invalid_value",
                    "raw_record_json": json.dumps(record, default=str),
                }
            )
            refined.append(
                {
                    "run_id": run_id,
                    "record_id": record_id,
                    "assessment_year": assessment_year,
                    "canonical_location_id": None,
                    "assessment_value": None,
                    "link_method": "unlinked",
                    "confidence": 0.0,
                    "ambiguous": 0,
                    "quarantined": 1,
                    "reason_code": "invalid_value",
                }
            )
            continue

        parcel_id = str(record["parcel_id"]).strip()
        lat = _safe_float(record.get("lat"))
        lon = _safe_float(record.get("lon"))
        if lat is None or lon is None:
            quarantined += 1
            full_records.append(
                {
                    "run_id": run_id,
                    "record_id": record_id,
                    "source_id": source_id,
                    "assessment_year": assessment_year,
                    "canonical_location_id": None,
                    "assessment_value": None,
                    "suite": record.get("suite"),
                    "house_number": record.get("house_number"),
                    "street_name": record.get("street_name"),
                    "neighbourhood_id": record.get("neighbourhood_id"),
                    "neighbourhood": record.get("neighbourhood"),
                    "ward": record.get("ward"),
                    "tax_class": record.get("tax_class"),
                    "garage": record.get("garage"),
                    "assessment_class_1": record.get("assessment_class_1"),
                    "assessment_class_2": record.get("assessment_class_2"),
                    "assessment_class_3": record.get("assessment_class_3"),
                    "assessment_class_pct_1": _safe_float(record.get("assessment_class_pct_1")),
                    "assessment_class_pct_2": _safe_float(record.get("assessment_class_pct_2")),
                    "assessment_class_pct_3": _safe_float(record.get("assessment_class_pct_3")),
                    "lat": None,
                    "lon": None,
                    "point_location": record.get("point_location"),
                    "link_method": "unlinked",
                    "confidence": 0.0,
                    "ambiguous": 0,
                    "quarantined": 1,
                    "reason_code": "invalid_coordinates",
                    "raw_record_json": json.dumps(record, default=str),
                }
            )
            refined.append(
                {
                    "run_id": run_id,
                    "record_id": record_id,
                    "assessment_year": assessment_year,
                    "canonical_location_id": None,
                    "assessment_value": None,
                    "link_method": "unlinked",
                    "confidence": 0.0,
                    "ambiguous": 0,
                    "quarantined": 1,
                    "reason_code": "invalid_coordinates",
                }
            )
            continue

        if parcel_id:
            canonical = f"loc-{parcel_id}"
            link_method = "direct"
            confidence = 0.99
        else:
            canonical = f"loc-{round(lat, 4)}-{round(lon, 4)}"
            link_method = "spatial"
            confidence = 0.75

        ambiguous = 1 if record.get("ambiguous_hint", False) else 0

        refined.append(
            {
                "run_id": run_id,
                "record_id": record_id,
                "assessment_year": assessment_year,
                "canonical_location_id": canonical,
                "assessment_value": float(value),
                "link_method": link_method,
                "confidence": confidence,
                "ambiguous": ambiguous,
                "quarantined": 0,
                "reason_code": "ambiguous" if ambiguous else None,
            }
        )
        full_records.append(
            {
                "run_id": run_id,
                "record_id": record_id,
                "source_id": source_id,
                "assessment_year": assessment_year,
                "canonical_location_id": canonical,
                "assessment_value": float(value),
                "suite": record.get("suite"),
                "house_number": record.get("house_number"),
                "street_name": record.get("street_name"),
                "neighbourhood_id": record.get("neighbourhood_id"),
                "neighbourhood": record.get("neighbourhood"),
                "ward": record.get("ward"),
                "tax_class": record.get("tax_class"),
                "garage": record.get("garage"),
                "assessment_class_1": record.get("assessment_class_1"),
                "assessment_class_2": record.get("assessment_class_2"),
                "assessment_class_3": record.get("assessment_class_3"),
                "assessment_class_pct_1": _safe_float(record.get("assessment_class_pct_1")),
                "assessment_class_pct_2": _safe_float(record.get("assessment_class_pct_2")),
                "assessment_class_pct_3": _safe_float(record.get("assessment_class_pct_3")),
                "lat": lat,
                "lon": lon,
                "point_location": record.get("point_location"),
                "link_method": link_method,
                "confidence": confidence,
                "ambiguous": ambiguous,
                "quarantined": 0,
                "reason_code": "ambiguous" if ambiguous else None,
                "raw_record_json": json.dumps(record, default=str),
            }
        )

    conn.execute("DELETE FROM assessments_staging WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM assessments_records_staging WHERE run_id=?", (run_id,))
    conn.executemany(
        """
        INSERT INTO assessments_staging (
            run_id, record_id, assessment_year, canonical_location_id, assessment_value,
            link_method, confidence, ambiguous, quarantined, reason_code
        ) VALUES (
            :run_id, :record_id, :assessment_year, :canonical_location_id, :assessment_value,
            :link_method, :confidence, :ambiguous, :quarantined, :reason_code
        )
        """,
        refined,
    )
    conn.executemany(
        """
        INSERT INTO assessments_records_staging (
            run_id, record_id, source_id, assessment_year, canonical_location_id, assessment_value,
            suite, house_number, street_name, neighbourhood_id, neighbourhood, ward, tax_class,
            garage, assessment_class_1, assessment_class_2, assessment_class_3,
            assessment_class_pct_1, assessment_class_pct_2, assessment_class_pct_3,
            lat, lon, point_location, link_method, confidence, ambiguous, quarantined,
            reason_code, raw_record_json
        ) VALUES (
            :run_id, :record_id, :source_id, :assessment_year, :canonical_location_id, :assessment_value,
            :suite, :house_number, :street_name, :neighbourhood_id, :neighbourhood, :ward, :tax_class,
            :garage, :assessment_class_1, :assessment_class_2, :assessment_class_3,
            :assessment_class_pct_1, :assessment_class_pct_2, :assessment_class_pct_3,
            :lat, :lon, :point_location, :link_method, :confidence, :ambiguous, :quarantined,
            :reason_code, :raw_record_json
        )
        """,
        full_records,
    )

    total = len(refined)
    valid = sum(1 for row in refined if row["quarantined"] == 0)
    linked = sum(1 for row in refined if row["quarantined"] == 0 and row["canonical_location_id"])
    unlinked = valid - linked
    ambiguous = sum(1 for row in refined if row["ambiguous"] == 1)

    invalid_rate = (total - valid) / max(total, 1)
    unlinked_rate = unlinked / max(valid, 1)
    ambiguous_rate = ambiguous / max(valid, 1)

    if invalid_rate > ASSESSMENT_INVALID_RATE_LIMIT:
        errors.append(f"invalid rate too high: {invalid_rate:.2%}")
    if unlinked_rate > ASSESSMENT_UNLINKED_RATE_LIMIT:
        errors.append(f"unlinked rate too high: {unlinked_rate:.2%}")
    if ambiguous_rate > ASSESSMENT_AMBIGUOUS_RATE_LIMIT:
        errors.append(f"ambiguous rate too high: {ambiguous_rate:.2%}")

    status = "failed" if errors else "succeeded"
    qa_status = "fail" if errors else "pass"
    promotion_status = "failed"

    if not errors:
        # deterministic duplicate resolution: highest confidence, then highest value
        choice_by_loc: dict[str, dict[str, Any]] = {}
        for row in refined:
            if row["quarantined"] == 1 or not row["canonical_location_id"]:
                continue
            loc = row["canonical_location_id"]
            prev = choice_by_loc.get(loc)
            if prev is None:
                choice_by_loc[loc] = row
                continue
            prev_score = (prev["confidence"], prev["assessment_value"])
            curr_score = (row["confidence"], row["assessment_value"])
            if curr_score > prev_score:
                choice_by_loc[loc] = row

        promoted_rows = [
            {
                "canonical_location_id": loc,
                "assessment_year": row["assessment_year"],
                "assessment_value": row["assessment_value"],
                "chosen_record_id": row["record_id"],
                "confidence": row["confidence"],
            }
            for loc, row in choice_by_loc.items()
        ]

        try:
            with transaction(conn):
                conn.execute("DELETE FROM assessments_prod")
                conn.execute("DELETE FROM assessments_records_prod")
                conn.executemany(
                    """
                    INSERT INTO assessments_prod (
                        canonical_location_id, assessment_year, assessment_value,
                        chosen_record_id, confidence
                    ) VALUES (
                        :canonical_location_id, :assessment_year, :assessment_value,
                        :chosen_record_id, :confidence
                    )
                    """,
                    promoted_rows,
                )
                conn.execute(
                    """
                    INSERT INTO assessments_records_prod (
                        record_id, source_id, assessment_year, canonical_location_id, assessment_value,
                        suite, house_number, street_name, neighbourhood_id, neighbourhood, ward, tax_class,
                        garage, assessment_class_1, assessment_class_2, assessment_class_3,
                        assessment_class_pct_1, assessment_class_pct_2, assessment_class_pct_3,
                        lat, lon, point_location, link_method, confidence, ambiguous, quarantined,
                        reason_code, raw_record_json
                    )
                    SELECT record_id, source_id, assessment_year, canonical_location_id, assessment_value,
                           suite, house_number, street_name, neighbourhood_id, neighbourhood, ward, tax_class,
                           garage, assessment_class_1, assessment_class_2, assessment_class_3,
                           assessment_class_pct_1, assessment_class_pct_2, assessment_class_pct_3,
                           lat, lon, point_location, link_method, confidence, ambiguous, quarantined,
                           reason_code, raw_record_json
                    FROM assessments_records_staging
                    WHERE run_id=?
                    """,
                    (run_id,),
                )
            promotion_status = "promoted"
            record_dataset_version(
                conn,
                dataset_type="assessments",
                version_id=str(assessment_year),
                source_version=str(assessment_year),
                provenance=f"property tax assessments ({source_key})",
                run_id=run_id,
            )
        except Exception as exc:
            status = "failed"
            errors.append(f"promotion failed: {exc}")
            add_alert(conn, run_id, "error", f"assessment promotion failed: {exc}")

    completed_at = utc_now()
    metadata = {
        "assessment_year": assessment_year,
        "coverage_percent": linked / max(valid, 1),
        "invalid_rate": invalid_rate,
        "qa_status": qa_status,
        "promotion_status": promotion_status,
        "counts": {
            "raw": total,
            "normalized": valid,
            "linked": linked,
            "unlinked": unlinked,
            "ambiguous": ambiguous,
        },
    }
    upsert_run_log(
        conn,
        run_id=run_id,
        story="019",
        trigger_type=trigger,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        warnings=warnings,
        errors=errors,
        metadata=metadata,
    )
    conn.commit()

    return {
        "run_id": run_id,
        "status": status,
        "assessment_year": assessment_year,
        "coverage_percent": metadata["coverage_percent"],
        "invalid_rate": invalid_rate,
        "qa_status": qa_status,
        "promotion_status": promotion_status,
        "warnings": warnings,
        "errors": errors,
        "completed_at": completed_at,
    }


def run_poi_standardization(
    conn,
    trigger: str = "manual",
    taxonomy_version: str = "v1",
    mapping_version: str = "v1",
    source_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    run_id = _new_run_id("poi")
    started_at = utc_now()
    warnings: list[str] = []
    errors: list[str] = []

    mapping_payload = load_payload_for_source("poi.mapping_rules", source_overrides)
    mappings = mapping_payload.metadata.get("mappings", {})

    raw_rows = conn.execute(
        """
        SELECT entity_id AS poi_id, source_id, raw_category
        FROM geospatial_prod
        WHERE dataset_type='pois'
        """
    ).fetchall()

    if not raw_rows:
        errors.append("no POIs found in production geospatial data; run story 17 first")

    standardized: list[dict[str, Any]] = []
    raw_to_canonical_seen: dict[tuple[str, str], set[str]] = defaultdict(set)

    for row in raw_rows:
        raw_category = (row["raw_category"] or "").strip() or "Unknown"
        mapped = mappings.get(raw_category)
        if mapped:
            canonical = mapped.get("canonical_category", "Unmapped/Other")
            subcategory = mapped.get("canonical_subcategory")
            rule_id = mapped.get("rule_id", "rule-manual")
            rationale = mapped.get("rationale", "mapping table")
            unmapped = 0
        else:
            canonical = "Unmapped/Other"
            subcategory = None
            rule_id = "rule-unmapped"
            rationale = "unrecognized label"
            unmapped = 1

        standardized.append(
            {
                "run_id": run_id,
                "poi_id": row["poi_id"],
                "source_id": row["source_id"],
                "poi_type_id": None,
                "canonical_category": canonical,
                "canonical_subcategory": subcategory,
                "raw_category": raw_category,
                "mapping_rule_id": rule_id,
                "mapping_rationale": rationale,
                "taxonomy_version": taxonomy_version,
                "mapping_version": mapping_version,
                "unmapped": unmapped,
            }
        )
        raw_to_canonical_seen[(row["source_id"], raw_category)].add(canonical)

    type_keys = {(row["canonical_category"], row["canonical_subcategory"]) for row in standardized}
    if type_keys:
        conn.executemany(
            """
            INSERT OR IGNORE INTO poi_types (
                canonical_category, canonical_subcategory, display_name, is_active
            ) VALUES (?, ?, ?, 1)
            """,
            [
                (
                    category,
                    subcategory,
                    f"{category}: {subcategory}" if subcategory else category,
                )
                for category, subcategory in sorted(type_keys, key=lambda item: (item[0], item[1] or ""))
            ],
        )
        type_rows = conn.execute(
            """
            SELECT poi_type_id, canonical_category, canonical_subcategory
            FROM poi_types
            """
        ).fetchall()
        type_lookup = {
            (row["canonical_category"], row["canonical_subcategory"]): row["poi_type_id"]
            for row in type_rows
        }
        for row in standardized:
            row["poi_type_id"] = type_lookup.get((row["canonical_category"], row["canonical_subcategory"]))

    conflict_labels = [
        f"{source}:{raw}"
        for (source, raw), canonicals in raw_to_canonical_seen.items()
        if len(canonicals) > 1
    ]
    conflict_count = len(conflict_labels)

    total = len(standardized)
    unmapped_count = sum(1 for row in standardized if row["unmapped"] == 1)
    mapped_percent = (total - unmapped_count) / max(total, 1)
    unmapped_percent = unmapped_count / max(total, 1)

    if conflict_count > 0:
        errors.append(f"conflicts found: {conflict_labels}")
    if unmapped_percent > UNMAPPED_RATE_LIMIT:
        if UNMAPPED_POLICY == "block":
            errors.append(f"unmapped percent too high: {unmapped_percent:.2%}")
        else:
            warnings.append(f"unmapped percent high: {unmapped_percent:.2%}")

    conn.execute("DELETE FROM poi_standardized_staging WHERE run_id=?", (run_id,))
    conn.executemany(
        """
        INSERT INTO poi_standardized_staging (
            run_id, poi_id, source_id, poi_type_id, canonical_category, canonical_subcategory,
            raw_category, mapping_rule_id, mapping_rationale, taxonomy_version,
            mapping_version, unmapped
        ) VALUES (
            :run_id, :poi_id, :source_id, :poi_type_id, :canonical_category, :canonical_subcategory,
            :raw_category, :mapping_rule_id, :mapping_rationale, :taxonomy_version,
            :mapping_version, :unmapped
        )
        """,
        standardized,
    )

    status = "failed" if errors else "succeeded"
    qa_status = "fail" if errors else "pass"
    promotion_status = "failed"

    if not errors:
        try:
            with transaction(conn):
                conn.execute("DELETE FROM poi_standardized_prod")
                conn.execute(
                    """
                    INSERT INTO poi_standardized_prod (
                        poi_id, source_id, poi_type_id, canonical_category, canonical_subcategory,
                        raw_category, mapping_rule_id, mapping_rationale,
                        taxonomy_version, mapping_version, unmapped
                    )
                    SELECT poi_id, source_id, poi_type_id, canonical_category, canonical_subcategory,
                           raw_category, mapping_rule_id, mapping_rationale,
                           taxonomy_version, mapping_version, unmapped
                    FROM poi_standardized_staging WHERE run_id=?
                    """,
                    (run_id,),
                )
            promotion_status = "promoted"
            record_dataset_version(
                conn,
                dataset_type="poi_standardization",
                version_id=f"{taxonomy_version}:{mapping_version}",
                source_version=mapping_version,
                provenance="poi mapping rules",
                run_id=run_id,
            )
        except Exception as exc:
            status = "failed"
            errors.append(f"promotion failed: {exc}")
            add_alert(conn, run_id, "error", f"poi standardization promotion failed: {exc}")

    completed_at = utc_now()
    metadata = {
        "taxonomy_version": taxonomy_version,
        "mapping_version": mapping_version,
        "mapped_percent": mapped_percent,
        "unmapped_percent": unmapped_percent,
        "conflict_count": conflict_count,
        "conflict_labels": conflict_labels,
        "qa_status": qa_status,
        "promotion_status": promotion_status,
    }
    upsert_run_log(
        conn,
        run_id=run_id,
        story="020",
        trigger_type=trigger,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        warnings=warnings,
        errors=errors,
        metadata=metadata,
    )
    conn.commit()

    return {
        "run_id": run_id,
        "status": status,
        "taxonomy_version": taxonomy_version,
        "mapping_version": mapping_version,
        "mapped_percent": mapped_percent,
        "unmapped_percent": unmapped_percent,
        "conflict_count": conflict_count,
        "warnings": warnings,
        "qa_status": qa_status,
        "promotion_status": promotion_status,
        "errors": errors,
        "completed_at": completed_at,
    }


def run_deduplication(conn, trigger: str = "manual") -> dict[str, Any]:
    run_id = _new_run_id("dedupe")
    started_at = utc_now()
    warnings: list[str] = []
    errors: list[str] = []

    rows = conn.execute(
        """
        SELECT p.poi_id AS entity_id, p.source_id, p.canonical_category, g.name, g.lat, g.lon
        FROM poi_standardized_prod p
        JOIN geospatial_prod g
          ON g.dataset_type='pois' AND g.entity_id=p.poi_id AND g.source_id=p.source_id
        """
    ).fetchall()

    if not rows:
        errors.append("no standardized POIs found; run stories 17 and 20 first")

    entities = [dict(row) for row in rows]

    candidates: list[dict[str, Any]] = []
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            a = entities[i]
            b = entities[j]

            if a["source_id"] == b["source_id"]:
                continue

            category_compatible = a["canonical_category"] == b["canonical_category"]
            if not category_compatible:
                continue

            dist = _distance_meters(a["lat"], a["lon"], b["lat"], b["lon"])
            an = a["name"].strip().lower()
            bn = b["name"].strip().lower()
            name_similarity = 1.0 if an == bn else (0.8 if an in bn or bn in an else 0.4)
            stable_match = a["entity_id"] == b["entity_id"]
            confidence = 0.55 * max(0.0, 1 - dist / DEDUPE_MAX_DISTANCE_METERS) + 0.35 * name_similarity + 0.10 * (1.0 if stable_match else 0.0)

            if confidence >= DEDUPE_AUTO_MERGE_THRESHOLD:
                decision = "auto_merge"
            elif confidence >= DEDUPE_REVIEW_THRESHOLD:
                decision = "review"
            else:
                decision = "reject"

            candidates.append(
                {
                    "entity_a_id": a["entity_id"],
                    "entity_b_id": b["entity_id"],
                    "distance_m": dist,
                    "name_similarity": name_similarity,
                    "confidence_score": confidence,
                    "decision": decision,
                    "category": a["canonical_category"],
                }
            )

    review_candidates = [c for c in candidates if c["decision"] == "review"]
    rejected_candidates = [c for c in candidates if c["decision"] == "reject"]
    merged_candidates = [c for c in candidates if c["decision"] == "auto_merge"]

    # Build canonical groups using auto-merge edges.
    parent: dict[str, str] = {e["entity_id"]: e["entity_id"] for e in entities}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for c in merged_candidates:
        union(c["entity_a_id"], c["entity_b_id"])

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_id = {e["entity_id"]: e for e in entities}
    for entity in entities:
        groups[find(entity["entity_id"])].append(entity)

    canonical_entities: list[dict[str, Any]] = []
    canonical_links: list[dict[str, Any]] = []

    for root, group in groups.items():
        chosen = sorted(group, key=lambda e: (e["source_id"], e["name"]))[0]
        canonical_id = f"can-{root}"
        canonical_entities.append(
            {
                "run_id": run_id,
                "canonical_id": canonical_id,
                "canonical_category": chosen["canonical_category"],
                "name": chosen["name"],
                "lon": chosen["lon"],
                "lat": chosen["lat"],
                "source_precedence": chosen["source_id"],
            }
        )
        for entity in group:
            canonical_links.append(
                {
                    "run_id": run_id,
                    "canonical_id": canonical_id,
                    "source_id": entity["source_id"],
                    "entity_id": entity["entity_id"],
                    "link_reason": "auto_merge" if len(group) > 1 else "singleton",
                }
            )

    count_reduction = (len(entities) - len(canonical_entities)) / max(len(entities), 1)
    distance_violations = sum(1 for c in merged_candidates if c["distance_m"] > DEDUPE_MAX_DISTANCE_METERS)
    overmerge_flags = [
        c for c in merged_candidates if c["name_similarity"] < 0.6 and c["distance_m"] > 80.0
    ]

    if distance_violations > 0 or overmerge_flags:
        errors.append("dedupe QA failed: suspicious merges detected")

    conn.execute("DELETE FROM canonical_entities_staging WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM canonical_links_staging WHERE run_id=?", (run_id,))
    conn.executemany(
        """
        INSERT INTO canonical_entities_staging (
            run_id, canonical_id, canonical_category, name, lon, lat, source_precedence
        ) VALUES (
            :run_id, :canonical_id, :canonical_category, :name, :lon, :lat, :source_precedence
        )
        """,
        canonical_entities,
    )
    conn.executemany(
        """
        INSERT INTO canonical_links_staging (
            run_id, canonical_id, source_id, entity_id, link_reason
        ) VALUES (
            :run_id, :canonical_id, :source_id, :entity_id, :link_reason
        )
        """,
        canonical_links,
    )

    status = "failed" if errors else "succeeded"
    qa_status = "fail" if errors else "pass"
    publication_status = "failed"

    if not errors:
        try:
            with transaction(conn):
                conn.execute("DELETE FROM canonical_links_prod")
                conn.execute("DELETE FROM canonical_entities_prod")
                conn.execute(
                    """
                    INSERT INTO canonical_entities_prod (
                        canonical_id, canonical_category, name, lon, lat, source_precedence
                    )
                    SELECT canonical_id, canonical_category, name, lon, lat, source_precedence
                    FROM canonical_entities_staging WHERE run_id=?
                    """,
                    (run_id,),
                )
                conn.execute(
                    """
                    INSERT INTO canonical_links_prod (canonical_id, source_id, entity_id, link_reason)
                    SELECT canonical_id, source_id, entity_id, link_reason
                    FROM canonical_links_staging WHERE run_id=?
                    """,
                    (run_id,),
                )
            publication_status = "published"
            record_dataset_version(
                conn,
                dataset_type="deduplication",
                version_id=run_id,
                source_version=None,
                provenance="canonical dedupe graph",
                run_id=run_id,
            )
        except Exception as exc:
            status = "failed"
            errors.append(f"publication failed: {exc}")
            add_alert(conn, run_id, "error", f"dedup publication failed: {exc}")

    completed_at = utc_now()
    metadata = {
        "count_reduction": count_reduction,
        "review_candidates": len(review_candidates),
        "rejected_candidates": len(rejected_candidates),
        "qa_status": qa_status,
        "publication_status": publication_status,
    }
    upsert_run_log(
        conn,
        run_id=run_id,
        story="021",
        trigger_type=trigger,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        warnings=warnings,
        errors=errors,
        metadata=metadata,
    )
    conn.commit()

    return {
        "run_id": run_id,
        "status": status,
        "count_reduction": count_reduction,
        "review_candidates": len(review_candidates),
        "rejected_candidates": len(rejected_candidates),
        "qa_status": qa_status,
        "publication_status": publication_status,
        "warnings": warnings,
        "errors": errors,
        "completed_at": completed_at,
    }
