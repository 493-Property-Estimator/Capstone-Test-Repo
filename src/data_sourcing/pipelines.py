"""Pipelines for stories 17-21: sourcing, refinement, and DB insertion."""

from __future__ import annotations

import json
import math
import uuid
import hashlib
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
    TRANSIT_DATASETS,
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


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return " ".join(text.split())


def _slug_text(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    return "".join(ch.lower() for ch in text if ch.isalnum())


def _display_text(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    parts = [part for part in text.replace("_", " ").split(" ") if part]
    if not parts:
        return None
    return " ".join(part.capitalize() for part in parts)


def _resolve_feature_name(record: dict[str, Any], fallback_id: str) -> str:
    for field in (
        "name",
        "road_name",
        "official_n",
        "common_nam",
        "branch",
        "school_nam",
        "stop_name",
        "business_n",
        "code_descr",
    ):
        text = _normalize_text(record.get(field))
        if text:
            return text

    raw_category = _display_text(record.get("raw_category") or record.get("fclass"))
    address = _normalize_text(record.get("address") or record.get("sch_addres") or record.get("business_a"))
    if raw_category and address:
        return f"{raw_category} at {address}"
    if raw_category:
        return raw_category
    return fallback_id


def _resolve_source_entity_id(record: dict[str, Any], source_id: str) -> str:
    entity_id = _normalize_text(record.get("entity_id"))
    if entity_id:
        return entity_id

    name = _resolve_feature_name(record, "")
    address = _normalize_text(record.get("address") or record.get("sch_addres") or record.get("business_a"))
    lat = _safe_float(record.get("lat"))
    lon = _safe_float(record.get("lon"))
    raw_category = _display_text(record.get("raw_category") or record.get("fclass")) or "feature"

    return _stable_id(
        "entity",
        source_id,
        raw_category,
        name,
        address,
        round(lat, 6) if lat is not None else None,
        round(lon, 6) if lon is not None else None,
    )


def _stable_id(prefix: str, *parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _nonnull(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _coalesce(existing: Any, new_value: Any) -> Any:
    return existing if _nonnull(existing) else new_value


def _coalesce_prefer_new(existing: Any, new_value: Any) -> Any:
    return new_value if _nonnull(new_value) else existing


def _merge_json_lists(existing_json: str | None, new_values: list[str]) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for source in (existing_json,):
        if not source:
            continue
        try:
            items = json.loads(source)
        except json.JSONDecodeError:
            items = []
        for item in items:
            text = str(item)
            if text not in seen:
                seen.add(text)
                merged.append(text)
    for item in new_values:
        text = str(item)
        if text not in seen:
            seen.add(text)
            merged.append(text)
    return json.dumps(merged)


def _load_json_object(raw_json: str | None) -> dict[str, Any]:
    if not raw_json:
        return {}
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _merge_json_object(existing_json: str | None, updates: dict[str, Any]) -> str:
    merged = _load_json_object(existing_json)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return json.dumps(merged, sort_keys=True, default=str)


def _property_location_key(record: dict[str, Any]) -> tuple[str, str]:
    suite = _slug_text(record.get("suite"))
    house = _slug_text(record.get("house_number"))
    street = _slug_text(record.get("street_name"))
    if house and street:
        return "address", "|".join(part for part in (suite, house, street) if part)

    lat = _safe_float(record.get("lat"))
    lon = _safe_float(record.get("lon"))
    if lat is not None and lon is not None:
        return "spatial", f"{round(lat, 5)}|{round(lon, 5)}"

    record_id = _normalize_text(record.get("record_id")) or _normalize_text(record.get("account_number")) or "unknown"
    return "record", record_id


def _canonical_location_id(record: dict[str, Any]) -> str:
    key_type, key_value = _property_location_key(record)
    return _stable_id("loc", key_type, key_value)


def _poi_merge_key(row: dict[str, Any]) -> str:
    address = _slug_text(row.get("address"))
    name = _slug_text(row.get("name"))
    if address and name:
        return _stable_id("poi", "address_name", address, name)
    if name and _nonnull(row.get("lat")) and _nonnull(row.get("lon")):
        return _stable_id("poi", "name_coord", name, round(float(row["lat"]), 4), round(float(row["lon"]), 4))
    if _nonnull(row.get("lat")) and _nonnull(row.get("lon")):
        return _stable_id("poi", "coord", round(float(row["lat"]), 5), round(float(row["lon"]), 5))
    return _stable_id("poi", "entity", row.get("source_id"), row.get("entity_id"))


def _merge_property_rows(existing: dict[str, Any] | None, new_row: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return dict(new_row)

    merged = dict(existing)
    for field in (
        "suite",
        "house_number",
        "street_name",
        "legal_description",
        "zoning",
        "lot_size",
        "total_gross_area",
        "year_built",
        "neighbourhood_id",
        "neighbourhood",
        "ward",
        "tax_class",
        "garage",
        "assessment_class_1",
        "assessment_class_2",
        "assessment_class_3",
        "assessment_class_pct_1",
        "assessment_class_pct_2",
        "assessment_class_pct_3",
        "lat",
        "lon",
        "point_location",
    ):
        merged[field] = _coalesce(merged.get(field), new_row.get(field))

    if _nonnull(new_row.get("assessment_value")):
        current_year = _safe_int(merged.get("assessment_year")) or 0
        new_year = _safe_int(new_row.get("assessment_year")) or 0
        if not _nonnull(merged.get("assessment_value")) or new_year >= current_year:
            merged["assessment_year"] = new_row.get("assessment_year")
            merged["assessment_value"] = new_row.get("assessment_value")

    if (_safe_float(new_row.get("confidence")) or 0.0) >= (_safe_float(merged.get("confidence")) or 0.0):
        merged["link_method"] = new_row.get("link_method")
        merged["confidence"] = new_row.get("confidence")

    merged["source_ids_json"] = _merge_json_lists(
        merged.get("source_ids_json"),
        json.loads(new_row["source_ids_json"]) if isinstance(new_row.get("source_ids_json"), str) else [],
    )
    merged["record_ids_json"] = _merge_json_lists(
        merged.get("record_ids_json"),
        json.loads(new_row["record_ids_json"]) if isinstance(new_row.get("record_ids_json"), str) else [],
    )
    merged["updated_at"] = max(
        [value for value in (merged.get("updated_at"), new_row.get("updated_at")) if value],
        default=None,
    )
    return merged


def _merge_poi_rows(existing: dict[str, Any] | None, new_row: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return dict(new_row)

    merged = dict(existing)
    for field in (
        "name",
        "raw_category",
        "raw_subcategory",
        "address",
        "lon",
        "lat",
        "neighbourhood",
        "source_dataset",
        "source_provider",
    ):
        merged[field] = _coalesce(merged.get(field), new_row.get(field))

    merged["source_ids_json"] = _merge_json_lists(
        merged.get("source_ids_json"),
        json.loads(new_row["source_ids_json"]) if isinstance(new_row.get("source_ids_json"), str) else [],
    )
    merged["source_entity_ids_json"] = _merge_json_lists(
        merged.get("source_entity_ids_json"),
        json.loads(new_row["source_entity_ids_json"]) if isinstance(new_row.get("source_entity_ids_json"), str) else [],
    )
    existing_metadata = json.loads(merged.get("metadata_json") or "{}") if merged.get("metadata_json") else {}
    new_metadata = json.loads(new_row.get("metadata_json") or "{}") if new_row.get("metadata_json") else {}
    if not isinstance(existing_metadata, dict):
        existing_metadata = {}
    if not isinstance(new_metadata, dict):
        new_metadata = {}
    merged_sources = dict(existing_metadata.get("sources", {}))
    merged_sources.update(new_metadata.get("sources", {}))
    combined_metadata = dict(existing_metadata)
    combined_metadata.update({k: v for k, v in new_metadata.items() if k != "sources"})
    combined_metadata["sources"] = merged_sources
    merged["metadata_json"] = json.dumps(combined_metadata, sort_keys=True)
    merged["source_version"] = _coalesce(merged.get("source_version"), new_row.get("source_version"))
    merged["updated_at"] = max(
        [value for value in (merged.get("updated_at"), new_row.get("updated_at")) if value],
        default=None,
    )
    return merged


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


def _build_geometry_payload(
    record: dict[str, Any],
    dataset: str,
    points: list[tuple[float, float]],
) -> dict[str, Any]:
    raw_geometry = record.get("geometry_payload")
    if isinstance(raw_geometry, dict) and raw_geometry.get("type") and raw_geometry.get("coordinates") is not None:
        return raw_geometry

    if dataset == "roads":
        return {
            "type": "MultiLineString",
            "coordinates": [[[lon, lat] for lon, lat in points]],
        }
    if dataset == "boundaries":
        return {
            "type": "Polygon",
            "coordinates": [[[lon, lat] for lon, lat in points]],
        }
    if points:
        lon, lat = points[0]
        return {"type": "Point", "coordinates": [lon, lat]}
    return {"type": "Point", "coordinates": [0.0, 0.0]}


def _polyline_length_m(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for idx in range(len(points) - 1):
        lon1, lat1 = points[idx]
        lon2, lat2 = points[idx + 1]
        total += _distance_meters(lat1, lon1, lat2, lon2)
    return total


def _normalize_road_name(value: Any) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    canonical = f" {text.upper().replace('.', ' ').replace('-', ' ')} "
    replacements = {
        " AVENUE ": " AVE ",
        " STREET ": " ST ",
        " ROAD ": " RD ",
        " DRIVE ": " DR ",
        " BOULEVARD ": " BLVD ",
        " COURT ": " CT ",
        " PLACE ": " PL ",
        " TERRACE ": " TER ",
        " CRESCENT ": " CRES ",
        " LANE ": " LN ",
        " TRAIL ": " TRL ",
        " PARKWAY ": " PKWY ",
        " HIGHWAY ": " HWY ",
    }
    for source, target in replacements.items():
        canonical = canonical.replace(source, target)
    canonical = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in canonical)
    canonical = " ".join(canonical.split())
    return canonical or None


def _road_name_candidates(record: dict[str, Any], fallback_name: str | None = None) -> list[str]:
    candidates: list[str] = []
    for value in (
        record.get("official_road_name"),
        record.get("road_name"),
        record.get("segment_name"),
        record.get("name"),
        fallback_name,
    ):
        normalized = _normalize_road_name(value)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def _is_placeholder_road_name(name: Any, road_id: Any | None = None) -> bool:
    text = _normalize_text(name)
    if text is None:
        return True
    if road_id is not None and text == str(road_id).strip():
        return True
    return not any(ch.isalpha() for ch in text)


def _choose_common_value(values: list[Any]) -> Any:
    counts: dict[Any, int] = defaultdict(int)
    for value in values:
        normalized = _normalize_text(value)
        if normalized is None:
            continue
        counts[normalized] += 1
    if not counts:
        return None
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def _road_attributes_from_record(record: dict[str, Any]) -> dict[str, Any]:
    official_road_name = _normalize_text(
        record.get("official_road_name")
        or record.get("street_nam")
        or record.get("road_name")
        or record.get("name")
    )
    return {
        "municipal_segment_id": _normalize_text(record.get("municipal_segment_id") or record.get("centerline")),
        "official_road_name": official_road_name,
        "roadway_category": _normalize_text(record.get("roadway_category") or record.get("centerli_2")),
        "surface_type": _normalize_text(record.get("surface_type") or record.get("road_segme")),
        "jurisdiction": _normalize_text(record.get("jurisdiction") or record.get("responsibl")),
        "functional_class": _normalize_text(record.get("functional_class") or record.get("functional")),
        "travel_direction": _normalize_text(record.get("travel_direction") or record.get("digitizing")),
        "quadrant": _normalize_text(record.get("quadrant")),
        "from_intersection_id": _normalize_text(record.get("from_intersection_id") or record.get("from_inter")),
        "to_intersection_id": _normalize_text(record.get("to_intersection_id") or record.get("to_interse")),
    }


def _build_road_segment_index(conn) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows = conn.execute(
        """
        SELECT
            rs.segment_id,
            rs.road_id,
            rs.source_id,
            rs.segment_name,
            rs.length_m,
            rs.center_lon,
            rs.center_lat,
            r.road_name,
            r.official_road_name
        FROM road_segments_prod rs
        JOIN roads_prod r
          ON r.road_id = rs.road_id
         AND r.source_id = rs.source_id
        """
    ).fetchall()

    for row in rows:
        candidate = dict(row)
        names = _road_name_candidates(
            candidate,
            fallback_name=candidate.get("official_road_name") or candidate.get("road_name"),
        )
        for name in names:
            index[name].append(candidate)
    return index


def _apply_edmonton_road_enrichment(
    conn,
    payload,
    source_key: str,
) -> dict[str, Any]:
    candidate_index = _build_road_segment_index(conn)
    if not candidate_index:
        return {
            "city_record_count": len(payload.records),
            "named_city_record_count": 0,
            "matched_city_record_count": 0,
            "updated_segment_count": 0,
            "updated_road_count": 0,
            "unmatched_named_city_record_count": 0,
        }

    assignments: dict[tuple[str, str], dict[str, Any]] = {}
    named_city_record_count = 0
    matched_city_record_count = 0

    for record in payload.records:
        attrs = _road_attributes_from_record(record)
        official_name = attrs["official_road_name"]
        points = _extract_geometry_points(record)
        if official_name is None or len(points) < 2:
            continue

        normalized_name = _normalize_road_name(official_name)
        if normalized_name is None:
            continue
        named_city_record_count += 1

        city_center_lon = sum(point[0] for point in points) / len(points)
        city_center_lat = sum(point[1] for point in points) / len(points)
        city_length_m = _polyline_length_m(points)

        best_candidate: dict[str, Any] | None = None
        best_score: tuple[float, float] | None = None
        for candidate in candidate_index.get(normalized_name, []):
            distance_m = _distance_meters(
                city_center_lat,
                city_center_lon,
                float(candidate["center_lat"]),
                float(candidate["center_lon"]),
            )
            if distance_m > 35.0:
                continue
            length_delta_m = abs((candidate["length_m"] or 0.0) - city_length_m)
            score = (distance_m, length_delta_m)
            if best_score is None or score < best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate is None or best_score is None:
            continue

        matched_city_record_count += 1
        match_key = (str(best_candidate["segment_id"]), str(best_candidate["source_id"]))
        payload_update = {
            **attrs,
            "road_id": str(best_candidate["road_id"]),
            "source_id": str(best_candidate["source_id"]),
            "segment_name": _normalize_text(best_candidate["segment_name"]),
            "road_name": _normalize_text(best_candidate["road_name"]),
            "match_distance_m": round(best_score[0], 2),
        }
        current = assignments.get(match_key)
        if current is None or payload_update["match_distance_m"] < current["match_distance_m"]:
            assignments[match_key] = payload_update

    road_updates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    with transaction(conn):
        for (segment_id, source_id), attrs in assignments.items():
            existing_row = conn.execute(
                """
                SELECT road_id, segment_name, metadata_json
                FROM road_segments_prod
                WHERE segment_id=? AND source_id=?
                """,
                (segment_id, source_id),
            ).fetchone()
            if existing_row is None:
                continue

            new_segment_name = (
                attrs["official_road_name"]
                if _is_placeholder_road_name(existing_row["segment_name"], segment_id)
                else existing_row["segment_name"]
            )
            segment_metadata = _merge_json_object(
                existing_row["metadata_json"],
                {
                    "edmonton": {
                        "match_distance_m": attrs["match_distance_m"],
                        "match_strategy": "normalized_name_plus_centroid",
                        "source_key": source_key,
                    }
                },
            )

            conn.execute(
                """
                UPDATE road_segments_prod
                SET
                    segment_name=?,
                    municipal_segment_id=?,
                    official_road_name=?,
                    roadway_category=?,
                    surface_type=?,
                    jurisdiction=?,
                    functional_class=?,
                    travel_direction=?,
                    quadrant=?,
                    from_intersection_id=?,
                    to_intersection_id=?,
                    metadata_json=?
                WHERE segment_id=? AND source_id=?
                """,
                (
                    new_segment_name,
                    attrs["municipal_segment_id"],
                    attrs["official_road_name"],
                    attrs["roadway_category"],
                    attrs["surface_type"],
                    attrs["jurisdiction"],
                    attrs["functional_class"],
                    attrs["travel_direction"],
                    attrs["quadrant"],
                    attrs["from_intersection_id"],
                    attrs["to_intersection_id"],
                    segment_metadata,
                    segment_id,
                    source_id,
                ),
            )
            road_updates[(str(existing_row["road_id"]), source_id)].append(attrs)

        for (road_id, source_id), values in road_updates.items():
            road_row = conn.execute(
                """
                SELECT road_name, metadata_json
                FROM roads_prod
                WHERE road_id=? AND source_id=?
                """,
                (road_id, source_id),
            ).fetchone()
            if road_row is None:
                continue

            official_name = _choose_common_value([value.get("official_road_name") for value in values])
            jurisdiction = _choose_common_value([value.get("jurisdiction") for value in values])
            functional_class = _choose_common_value([value.get("functional_class") for value in values])
            quadrant = _choose_common_value([value.get("quadrant") for value in values])
            road_name = (
                official_name
                if _is_placeholder_road_name(road_row["road_name"], road_id) and official_name is not None
                else road_row["road_name"]
            )
            road_metadata = _merge_json_object(
                road_row["metadata_json"],
                {
                    "edmonton": {
                        "matched_segment_count": len(values),
                        "source_key": source_key,
                    }
                },
            )

            conn.execute(
                """
                UPDATE roads_prod
                SET
                    road_name=?,
                    official_road_name=?,
                    jurisdiction=?,
                    functional_class=?,
                    quadrant=?,
                    metadata_json=?
                WHERE road_id=? AND source_id=?
                """,
                (
                    road_name,
                    official_name,
                    jurisdiction,
                    functional_class,
                    quadrant,
                    road_metadata,
                    road_id,
                    source_id,
                ),
            )

    return {
        "city_record_count": len(payload.records),
        "named_city_record_count": named_city_record_count,
        "matched_city_record_count": matched_city_record_count,
        "updated_segment_count": len(assignments),
        "updated_road_count": len(road_updates),
        "unmatched_named_city_record_count": max(named_city_record_count - matched_city_record_count, 0),
    }


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
    poi_merged_by_id: dict[str, dict[str, Any]] = {}
    entity_key_counts: dict[tuple[str, str], int] = defaultdict(int)

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

        if spec.get("promotion_mode") == "enrich_existing":
            if dataset != "roads":
                errors.append(f"{source_key} uses enrich_existing for unsupported dataset '{dataset}'")
                continue
            summary = _apply_edmonton_road_enrichment(conn, payload, source_key)
            results.append(
                {
                    "type": "roads",
                    "version": payload.metadata.get("version"),
                    "row_count": 0,
                    "qa_status": "pass",
                    "promotion_status": "promoted",
                    "warnings": [],
                    "enrichment_mode": "update_existing",
                    **summary,
                }
            )
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
            base_entity_id = _resolve_source_entity_id(record, source_id)
            scoped_entity_id = f"{source_id}:{base_entity_id}"
            raw_category = record.get("raw_category")
            if raw_category in (None, "") and dataset in {"roads", "pois"}:
                raw_category = record.get("fclass")
            entity_key = (dataset, scoped_entity_id)
            entity_key_counts[entity_key] += 1
            dup_index = entity_key_counts[entity_key]
            entity_id = scoped_entity_id if dup_index == 1 else f"{scoped_entity_id}__dup{dup_index}"
            if dup_index > 1:
                warnings.append(
                    f"{source_key}: duplicate entity_id '{base_entity_id}' for source '{source_id}'"
                    f" disambiguated as '{entity_id}'"
                )

            name = _resolve_feature_name(record, entity_id)

            points = _extract_geometry_points(record)
            if not points:
                errors.append(f"{source_key} missing geometry for {entity_id}")
                continue

            center_lon = sum(p[0] for p in points) / len(points)
            center_lat = sum(p[1] for p in points) / len(points)
            lon = center_lon
            lat = center_lat
            geometry_payload = _build_geometry_payload(record, dataset, points)
            canonical_geom_type = str(geometry_payload.get("type") or "Point")

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
                    "canonical_geom_type": canonical_geom_type,
                    "lon": float(lon),
                    "lat": float(lat),
                    "geometry_json": json.dumps(geometry_payload),
                    "source_version": payload.metadata.get("version"),
                    "updated_at": payload.metadata.get("publish_date"),
                }
            )

            if dataset == "pois":
                address = _normalize_text(record.get("address") or record.get("sch_addres") or record.get("business_a"))
                raw_subcategory = _normalize_text(
                    record.get("raw_subcategory")
                    or record.get("facility_type")
                    or record.get("subsectors")
                    or record.get("industry_group")
                    or record.get("naics_description")
                )
                neighbourhood = _normalize_text(
                    record.get("neighbourhood")
                    or record.get("neighbourhood_name")
                )
                source_dataset = spec.get("dataset")
                source_provider = spec.get("provider") or "City of Edmonton Open Data"
                poi_row = {
                    "run_id": run_id,
                    "canonical_poi_id": _poi_merge_key(
                        {
                            "source_id": source_id,
                            "entity_id": entity_id,
                            "name": name,
                            "address": address,
                            "lat": float(lat),
                            "lon": float(lon),
                        }
                    ),
                    "name": name,
                    "raw_category": raw_category,
                    "raw_subcategory": raw_subcategory,
                    "address": address,
                    "lon": float(lon),
                    "lat": float(lat),
                    "neighbourhood": neighbourhood,
                    "source_dataset": source_dataset,
                    "source_provider": source_provider,
                    "source_ids_json": json.dumps([source_id]),
                    "source_entity_ids_json": json.dumps([f"{source_id}:{entity_id}"]),
                    "metadata_json": json.dumps(
                        {
                            "dataset": source_dataset,
                            "provider": source_provider,
                            "sources": {
                                source_id: {
                                    "entity_id": entity_id,
                                    "record": record,
                                }
                            },
                        },
                        sort_keys=True,
                        default=str,
                    ),
                    "source_version": payload.metadata.get("version"),
                    "updated_at": payload.metadata.get("publish_date"),
                }
                poi_merged_by_id[poi_row["canonical_poi_id"]] = _merge_poi_rows(
                    poi_merged_by_id.get(poi_row["canonical_poi_id"]),
                    poi_row,
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
                        "official_road_name": _normalize_text(
                            record.get("official_road_name") or record.get("street_nam") or road_name
                        ),
                        "jurisdiction": _normalize_text(record.get("jurisdiction") or record.get("responsibl")),
                        "functional_class": _normalize_text(record.get("functional_class") or record.get("functional")),
                        "quadrant": _normalize_text(record.get("quadrant")),
                        "source_version": payload.metadata.get("version"),
                        "updated_at": payload.metadata.get("publish_date"),
                        "metadata_json": json.dumps({}),
                    }
                else:
                    roads_by_key[road_key]["official_road_name"] = _coalesce_prefer_new(
                        roads_by_key[road_key].get("official_road_name"),
                        _normalize_text(record.get("official_road_name") or record.get("street_nam")),
                    )
                    roads_by_key[road_key]["jurisdiction"] = _coalesce_prefer_new(
                        roads_by_key[road_key].get("jurisdiction"),
                        _normalize_text(record.get("jurisdiction") or record.get("responsibl")),
                    )
                    roads_by_key[road_key]["functional_class"] = _coalesce_prefer_new(
                        roads_by_key[road_key].get("functional_class"),
                        _normalize_text(record.get("functional_class") or record.get("functional")),
                    )
                    roads_by_key[road_key]["quadrant"] = _coalesce_prefer_new(
                        roads_by_key[road_key].get("quadrant"),
                        _normalize_text(record.get("quadrant")),
                    )

                start_lon, start_lat = points[0]
                end_lon, end_lat = points[-1]
                segment_center_lon = sum(p[0] for p in points) / len(points)
                segment_center_lat = sum(p[1] for p in points) / len(points)
                lane_count = _safe_int(record.get("lane_count") or record.get("lanes"))
                sequence_no = _safe_int(record.get("sequence_no") or record.get("segment_sequence"))
                road_attrs = _road_attributes_from_record(record)

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
                        "municipal_segment_id": road_attrs["municipal_segment_id"],
                        "official_road_name": road_attrs["official_road_name"],
                        "roadway_category": road_attrs["roadway_category"],
                        "surface_type": road_attrs["surface_type"],
                        "jurisdiction": road_attrs["jurisdiction"],
                        "functional_class": road_attrs["functional_class"],
                        "travel_direction": road_attrs["travel_direction"],
                        "quadrant": road_attrs["quadrant"],
                        "from_intersection_id": road_attrs["from_intersection_id"],
                        "to_intersection_id": road_attrs["to_intersection_id"],
                        "start_lon": start_lon,
                        "start_lat": start_lat,
                        "end_lon": end_lon,
                        "end_lat": end_lat,
                        "center_lon": segment_center_lon,
                        "center_lat": segment_center_lat,
                        "length_m": _polyline_length_m(points),
                        "geometry_json": json.dumps([[p[0], p[1]] for p in points]),
                        "metadata_json": json.dumps({}),
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
                canonical_geom_type, lon, lat, geometry_json, source_version, updated_at
            ) VALUES (
                :run_id, :dataset_type, :entity_id, :source_id, :name, :raw_category,
                :canonical_geom_type, :lon, :lat, :geometry_json, :source_version, :updated_at
            )
            """,
            refined,
        )

        if dataset == "pois":
            conn.execute("DELETE FROM poi_staging WHERE run_id=?", (run_id,))
            conn.executemany(
                """
                INSERT INTO poi_staging (
                    run_id, canonical_poi_id, name, raw_category, raw_subcategory, address, lon, lat,
                    neighbourhood, source_dataset, source_provider, source_ids_json,
                    source_entity_ids_json, metadata_json, source_version, updated_at
                ) VALUES (
                    :run_id, :canonical_poi_id, :name, :raw_category, :raw_subcategory, :address, :lon, :lat,
                    :neighbourhood, :source_dataset, :source_provider, :source_ids_json,
                    :source_entity_ids_json, :metadata_json, :source_version, :updated_at
                )
                """,
                list(poi_merged_by_id.values()),
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
                run_id, road_id, source_id, road_name, road_type, official_road_name,
                jurisdiction, functional_class, quadrant, source_version, updated_at, metadata_json
            ) VALUES (
                :run_id, :road_id, :source_id, :road_name, :road_type, :official_road_name,
                :jurisdiction, :functional_class, :quadrant, :source_version, :updated_at, :metadata_json
            )
            """,
            list(roads_by_key.values()),
        )
    if road_segments:
        conn.executemany(
            """
            INSERT INTO road_segments_staging (
                run_id, segment_id, road_id, source_id, sequence_no, segment_name,
                segment_type, lane_count, municipal_segment_id, official_road_name, roadway_category,
                surface_type, jurisdiction, functional_class, travel_direction, quadrant,
                from_intersection_id, to_intersection_id, start_lon, start_lat, end_lon, end_lat,
                center_lon, center_lat, length_m, geometry_json, metadata_json, source_version, updated_at
            ) VALUES (
                :run_id, :segment_id, :road_id, :source_id, :sequence_no, :segment_name,
                :segment_type, :lane_count, :municipal_segment_id, :official_road_name, :roadway_category,
                :surface_type, :jurisdiction, :functional_class, :travel_direction, :quadrant,
                :from_intersection_id, :to_intersection_id, :start_lon, :start_lat, :end_lon, :end_lat,
                :center_lon, :center_lat, :length_m, :geometry_json, :metadata_json, :source_version, :updated_at
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
                    source_ids = sorted({row["source_id"] for row in refined_by_dataset[dataset]})
                    if source_ids:
                        placeholders = ",".join("?" for _ in source_ids)
                        conn.execute(
                            f"DELETE FROM geospatial_prod WHERE dataset_type=? AND source_id IN ({placeholders})",
                            [dataset, *source_ids],
                        )
                    conn.execute(
                        """
                        INSERT INTO geospatial_prod (
                            dataset_type, entity_id, source_id, name, raw_category,
                            canonical_geom_type, lon, lat, geometry_json, source_version, updated_at
                        )
                        SELECT dataset_type, entity_id, source_id, name, raw_category,
                               canonical_geom_type, lon, lat, geometry_json, source_version, updated_at
                        FROM geospatial_staging
                        WHERE run_id=? AND dataset_type=?
                        """,
                        (run_id, dataset),
                    )
                if "roads" in dataset_types:
                    road_source_ids = sorted({row["source_id"] for row in roads_by_key.values()})
                    if road_source_ids:
                        placeholders = ",".join("?" for _ in road_source_ids)
                        conn.execute(
                            f"DELETE FROM road_segments_prod WHERE source_id IN ({placeholders})",
                            road_source_ids,
                        )
                        conn.execute(
                            f"DELETE FROM roads_prod WHERE source_id IN ({placeholders})",
                            road_source_ids,
                        )
                    conn.execute(
                        """
                        INSERT INTO roads_prod (
                            road_id, source_id, road_name, road_type, official_road_name,
                            jurisdiction, functional_class, quadrant, source_version, updated_at, metadata_json
                        )
                        SELECT road_id, source_id, road_name, road_type, official_road_name,
                               jurisdiction, functional_class, quadrant, source_version, updated_at, metadata_json
                        FROM roads_staging
                        WHERE run_id=?
                        """,
                        (run_id,),
                    )
                    conn.execute(
                        """
                        INSERT INTO road_segments_prod (
                            segment_id, road_id, source_id, sequence_no, segment_name, segment_type, lane_count,
                            municipal_segment_id, official_road_name, roadway_category, surface_type,
                            jurisdiction, functional_class, travel_direction, quadrant,
                            from_intersection_id, to_intersection_id, start_lon, start_lat, end_lon, end_lat,
                            center_lon, center_lat, length_m, geometry_json, metadata_json, source_version, updated_at
                        )
                        SELECT segment_id, road_id, source_id, sequence_no, segment_name, segment_type, lane_count,
                               municipal_segment_id, official_road_name, roadway_category, surface_type,
                               jurisdiction, functional_class, travel_direction, quadrant,
                               from_intersection_id, to_intersection_id, start_lon, start_lat, end_lon, end_lat,
                               center_lon, center_lat, length_m, geometry_json, metadata_json, source_version, updated_at
                        FROM road_segments_staging
                        WHERE run_id=?
                        """,
                        (run_id,),
                    )
                if poi_merged_by_id:
                    existing_pois = {
                        row["canonical_poi_id"]: dict(row)
                        for row in conn.execute("SELECT * FROM poi_prod").fetchall()
                    }
                    merged_pois = dict(existing_pois)
                    for canonical_id, row in poi_merged_by_id.items():
                        merged_pois[canonical_id] = _merge_poi_rows(existing_pois.get(canonical_id), row)
                    conn.executemany(
                        """
                        INSERT INTO poi_prod (
                            canonical_poi_id, name, raw_category, raw_subcategory, address, lon, lat,
                            neighbourhood, source_dataset, source_provider, source_ids_json,
                            source_entity_ids_json, metadata_json, source_version, updated_at
                        ) VALUES (
                            :canonical_poi_id, :name, :raw_category, :raw_subcategory, :address, :lon, :lat,
                            :neighbourhood, :source_dataset, :source_provider, :source_ids_json,
                            :source_entity_ids_json, :metadata_json, :source_version, :updated_at
                        )
                        ON CONFLICT(canonical_poi_id) DO UPDATE SET
                            name=excluded.name,
                            raw_category=excluded.raw_category,
                            raw_subcategory=excluded.raw_subcategory,
                            address=excluded.address,
                            lon=excluded.lon,
                            lat=excluded.lat,
                            neighbourhood=excluded.neighbourhood,
                            source_dataset=excluded.source_dataset,
                            source_provider=excluded.source_provider,
                            source_ids_json=excluded.source_ids_json,
                            source_entity_ids_json=excluded.source_entity_ids_json,
                            metadata_json=excluded.metadata_json,
                            source_version=excluded.source_version,
                            updated_at=excluded.updated_at
                        """,
                        list(merged_pois.values()),
                    )
            for result in results:
                result["promotion_status"] = "promoted"
                if result["type"] == "roads" and not result.get("enrichment_mode"):
                    result["road_count"] = len(roads_by_key)
                    result["segment_count"] = len(road_segments)
                record_dataset_version(
                    conn,
                    dataset_type=f"geospatial:{result['type']}",
                    version_id=result.get("version") or run_id,
                    source_version=result.get("version"),
                    provenance=(
                        "Edmonton road network enrichment"
                        if result.get("enrichment_mode")
                        else "open geospatial source"
                    ),
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


def _crime_count_key(row: dict[str, Any]) -> tuple[str, str, str, int]:
    year = _safe_int(row.get("year")) or 0
    return (
        str(row.get("source_id") or ""),
        str(row.get("neighbourhood") or ""),
        str(row.get("crime_type") or ""),
        year,
    )


def _normalize_crime_metric_name(record: dict[str, Any]) -> str | None:
    return _normalize_text(
        record.get("crime_type")
        or record.get("metric_name")
        or record.get("statistics")
        or record.get("indicator")
        or record.get("violation")
    )


def _normalize_crime_geography(record: dict[str, Any]) -> str | None:
    return _normalize_text(
        record.get("neighbourhood")
        or record.get("region_name")
        or record.get("geo")
        or record.get("geography")
        or record.get("police_service")
    )


def _normalize_crime_year(record: dict[str, Any]) -> int | None:
    raw = record.get("year") or record.get("ref_date") or record.get("reference_period")
    text = _normalize_text(raw)
    if not text:
        return None
    leading = text.split("-")[0].split("/")[0]
    return _safe_int(leading)


def run_crime_ingest(
    conn,
    trigger: str = "manual",
    source_overrides: dict[str, str] | None = None,
    source_keys: list[str] | None = None,
) -> dict[str, Any]:
    run_id = _new_run_id("crime")
    started_at = utc_now()
    warnings: list[str] = []
    errors: list[str] = []
    selected_source_keys = source_keys[:] if source_keys else ["crime.statscan_police_service"]

    refined: list[dict[str, Any]] = []
    latest_year = 0
    missing_value_rows = 0
    malformed_rows = 0

    for source_key in selected_source_keys:
        payload = load_payload_for_source(source_key, source_overrides)
        source_spec = get_source_spec(source_key)
        include_rates = bool(source_spec.get("include_rates", True))
        include_counts = bool(source_spec.get("include_counts", True))
        geography_filter = {
            value.upper()
            for value in source_spec.get("target_geographies", [])
            if _normalize_text(value)
        }

        raw_rows: list[dict[str, Any]] = []
        dropped_rows = 0
        for record in payload.records:
            geography = _normalize_crime_geography(record)
            metric_name = _normalize_crime_metric_name(record)
            year = _normalize_crime_year(record)
            value = _safe_float(record.get("incident_count") or record.get("value"))
            geography_upper = (geography or "").upper()
            if geography_filter and not any(
                geography_upper == target or geography_upper.startswith(target) or target in geography_upper
                for target in geography_filter
            ):
                dropped_rows += 1
                continue
            missing = []
            if geography is None:
                missing.append("neighbourhood/region_name")
            if metric_name is None:
                missing.append("crime_type/statistics")
            if year is None:
                missing.append("year/ref_date")
            if value is None:
                missing.append("incident_count/value")
            if missing:
                if missing == ["incident_count/value"]:
                    missing_value_rows += 1
                else:
                    malformed_rows += 1
                continue

            unit = _normalize_text(record.get("unit") or record.get("uom") or record.get("value_unit")) or ""
            lowered_metric = metric_name.lower()
            lowered_unit = unit.lower()
            is_rate_metric = "rate" in lowered_metric or "/100,000" in lowered_metric or "per 100,000" in lowered_metric
            is_rate_unit = "100,000" in lowered_unit or "rate" in lowered_unit
            rate_value = value if (is_rate_metric or is_rate_unit) else None
            incident_count = int(round(value)) if rate_value is None else None

            if rate_value is not None and not include_rates:
                dropped_rows += 1
                continue
            if incident_count is not None and not include_counts:
                dropped_rows += 1
                continue

            geography_level = _normalize_text(record.get("geography_level")) or "police_service"
            raw_rows.append(
                {
                    "source_id": source_key,
                    "neighbourhood": geography,
                    "crime_type": metric_name,
                    "incident_count": incident_count,
                    "rate_per_100k": rate_value,
                    "year": year,
                    "geography_level": geography_level,
                    "raw_metric_name": metric_name,
                    "source_version": _normalize_text(payload.metadata.get("source_name"))
                    or _normalize_text(payload.metadata.get("version"))
                    or str(year),
                    "updated_at": utc_now(),
                    "raw_record_json": json.dumps(record, sort_keys=True),
                }
            )
            latest_year = max(latest_year, year)

        if dropped_rows:
            warnings.append(f"{source_key} dropped {dropped_rows} non-target rows")

        counts_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
        rates_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
        for row in raw_rows:
            key = _crime_count_key(row)
            if row["incident_count"] is not None:
                current = counts_by_key.get(key)
                if current is None or (
                    int(row["incident_count"]) > int(current["incident_count"])
                    or (
                        int(row["incident_count"]) == int(current["incident_count"])
                        and str(row["crime_type"]).upper() < str(current["crime_type"]).upper()
                    )
                ):
                    counts_by_key[key] = row
            elif row["rate_per_100k"] is not None:
                current = rates_by_key.get(key)
                if current is None or (
                    float(row["rate_per_100k"]) > float(current["rate_per_100k"])
                    or (
                        float(row["rate_per_100k"]) == float(current["rate_per_100k"])
                        and str(row["crime_type"]).upper() < str(current["crime_type"]).upper()
                    )
                ):
                    rates_by_key[key] = row

        if not counts_by_key and not rates_by_key:
            warnings.append(f"{source_key} produced no valid crime summary rows")
            continue

        merged_keys = sorted(set(counts_by_key) | set(rates_by_key))
        for key in merged_keys:
            count_row = counts_by_key.get(key)
            rate_row = rates_by_key.get(key)
            base_row = count_row or rate_row
            assert base_row is not None
            refined.append(
                {
                    "run_id": run_id,
                    "source_id": source_key,
                    "neighbourhood": base_row["neighbourhood"],
                    "crime_type": base_row["crime_type"],
                    "incident_count": count_row["incident_count"] if count_row else None,
                    "rate_per_100k": rate_row["rate_per_100k"] if rate_row else None,
                    "year": base_row["year"],
                    "geography_level": base_row["geography_level"],
                    "raw_metric_name": base_row["raw_metric_name"],
                    "source_version": base_row["source_version"],
                    "updated_at": base_row["updated_at"],
                }
            )

    if missing_value_rows:
        warnings.append(f"skipped {missing_value_rows} crime rows with blank VALUE fields")
    if malformed_rows:
        warnings.append(f"skipped {malformed_rows} malformed crime rows missing required dimensions")

    conn.execute("DELETE FROM crime_summary_staging WHERE run_id=?", (run_id,))
    if refined:
        conn.executemany(
            """
            INSERT INTO crime_summary_staging (
                run_id, source_id, neighbourhood, crime_type, incident_count, rate_per_100k,
                year, geography_level, raw_metric_name, source_version, updated_at
            ) VALUES (
                :run_id, :source_id, :neighbourhood, :crime_type, :incident_count, :rate_per_100k,
                :year, :geography_level, :raw_metric_name, :source_version, :updated_at
            )
            """,
            refined,
        )

    status = "failed" if errors or not refined else "succeeded"
    promotion_status = "failed"
    if refined and not errors:
        try:
            with transaction(conn):
                touched_sources = sorted({row["source_id"] for row in refined})
                placeholders = ",".join("?" for _ in touched_sources)
                conn.execute(
                    f"DELETE FROM crime_summary_prod WHERE source_id IN ({placeholders})",
                    touched_sources,
                )
                conn.execute(
                    """
                    INSERT INTO crime_summary_prod (
                        source_id, neighbourhood, crime_type, incident_count, rate_per_100k,
                        year, geography_level, raw_metric_name, source_version, updated_at
                    )
                    SELECT source_id, neighbourhood, crime_type, incident_count, rate_per_100k,
                           year, geography_level, raw_metric_name, source_version, updated_at
                    FROM crime_summary_staging
                    WHERE run_id=?
                    """,
                    (run_id,),
                )
            promotion_status = "promoted"
            record_dataset_version(
                conn,
                dataset_type="crime",
                version_id=str(latest_year or run_id),
                source_version=str(latest_year or ""),
                provenance=f"crime summary ({', '.join(selected_source_keys)})",
                run_id=run_id,
            )
        except Exception as exc:
            status = "failed"
            errors.append(f"promotion failed: {exc}")
            add_alert(conn, run_id, "error", f"crime promotion failed: {exc}")

    completed_at = utc_now()
    metadata = {
        "row_count": len(refined),
        "source_keys": selected_source_keys,
        "latest_year": latest_year or None,
        "promotion_status": promotion_status,
    }
    upsert_run_log(
        conn,
        run_id=run_id,
        story="crime",
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
        "row_count": len(refined),
        "latest_year": latest_year or None,
        "promotion_status": promotion_status,
        "warnings": warnings,
        "errors": errors,
        "completed_at": completed_at,
    }


def run_assessment_ingest(
    conn,
    trigger: str = "manual",
    source_overrides: dict[str, str] | None = None,
    source_keys: list[str] | None = None,
) -> dict[str, Any]:
    run_id = _new_run_id("assess")
    started_at = utc_now()
    warnings: list[str] = []
    errors: list[str] = []

    refined: list[dict[str, Any]] = []
    full_records: list[dict[str, Any]] = []
    property_rows_by_location: dict[str, dict[str, Any]] = {}
    quarantined = 0
    run_record_id_counts: dict[str, int] = defaultdict(int)
    selected_source_keys = source_keys[:] if source_keys else ["assessments.property_tax"]
    assessment_year = 0

    for source_key in selected_source_keys:
        payload = load_payload_for_source(source_key, source_overrides)
        source_assessment_year = int(payload.metadata.get("assessment_year", 0))
        assessment_year = max(assessment_year, source_assessment_year)
        source_updated_at = payload.metadata.get("publication_date") or payload.metadata.get("publish_date")
        requires_value = source_key != "assessments.property_information"

        for record in payload.records:
            source_id = str(record.get("source_id") or source_key)
            base_record_id = str(record.get("record_id") or record.get("account_number") or f"missing-{quarantined + 1}")
            run_record_id_counts[base_record_id] += 1
            record_id = (
                base_record_id
                if run_record_id_counts[base_record_id] == 1
                else f"{base_record_id}__{source_id}"
            )
            lat = _safe_float(record.get("lat"))
            lon = _safe_float(record.get("lon"))
            value = _safe_float(record.get("assessment_value"))

            missing = require_fields(record, ("record_id",))
            if lat is None:
                missing.append("lat")
            if lon is None:
                missing.append("lon")
            if requires_value and value is None:
                missing.append("assessment_value")

            if missing:
                quarantined += 1
                full_records.append(
                    {
                        "run_id": run_id,
                        "record_id": record_id,
                        "source_id": source_id,
                        "assessment_year": source_assessment_year,
                        "canonical_location_id": None,
                        "assessment_value": value,
                        "suite": record.get("suite"),
                        "house_number": record.get("house_number"),
                        "street_name": record.get("street_name"),
                        "legal_description": record.get("legal_description"),
                        "zoning": record.get("zoning"),
                        "lot_size": _safe_float(record.get("lot_size")),
                        "total_gross_area": record.get("total_gross_area"),
                        "year_built": _safe_int(record.get("year_built")),
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
                        "link_method": "unlinked",
                        "confidence": 0.0,
                        "ambiguous": 0,
                        "quarantined": 1,
                        "reason_code": f"missing_fields:{','.join(sorted(set(missing)))}",
                        "raw_record_json": json.dumps(record, default=str),
                    }
                )
                refined.append(
                    {
                        "run_id": run_id,
                        "record_id": record_id,
                        "assessment_year": source_assessment_year,
                        "canonical_location_id": None,
                        "assessment_value": None,
                        "link_method": "unlinked",
                        "confidence": 0.0,
                        "ambiguous": 0,
                        "quarantined": 1,
                        "reason_code": f"missing_fields:{','.join(sorted(set(missing)))}",
                    }
                )
                continue

            if requires_value and value is not None and value <= 0:
                quarantined += 1
                full_records.append(
                    {
                        "run_id": run_id,
                        "record_id": record_id,
                        "source_id": source_id,
                        "assessment_year": source_assessment_year,
                        "canonical_location_id": None,
                        "assessment_value": None,
                        "suite": record.get("suite"),
                        "house_number": record.get("house_number"),
                        "street_name": record.get("street_name"),
                        "legal_description": record.get("legal_description"),
                        "zoning": record.get("zoning"),
                        "lot_size": _safe_float(record.get("lot_size")),
                        "total_gross_area": record.get("total_gross_area"),
                        "year_built": _safe_int(record.get("year_built")),
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
                        "assessment_year": source_assessment_year,
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

            canonical = _canonical_location_id(record)
            link_key_type, _ = _property_location_key(record)
            link_method = "address" if link_key_type == "address" else ("spatial" if link_key_type == "spatial" else "record")
            confidence = 0.98 if link_method == "address" else (0.75 if link_method == "spatial" else 0.5)
            ambiguous = 1 if record.get("ambiguous_hint", False) else 0
            normalized_value = float(value) if value is not None else None

            refined.append(
                {
                    "run_id": run_id,
                    "record_id": record_id,
                    "assessment_year": source_assessment_year,
                    "canonical_location_id": canonical,
                    "assessment_value": normalized_value,
                    "link_method": link_method,
                    "confidence": confidence,
                    "ambiguous": ambiguous,
                    "quarantined": 0,
                    "reason_code": "ambiguous" if ambiguous else None,
                }
            )

            full_row = {
                "run_id": run_id,
                "record_id": record_id,
                "source_id": source_id,
                "assessment_year": source_assessment_year,
                "canonical_location_id": canonical,
                "assessment_value": normalized_value,
                "suite": record.get("suite"),
                "house_number": record.get("house_number"),
                "street_name": record.get("street_name"),
                "legal_description": record.get("legal_description"),
                "zoning": record.get("zoning"),
                "lot_size": _safe_float(record.get("lot_size")),
                "total_gross_area": record.get("total_gross_area"),
                "year_built": _safe_int(record.get("year_built")),
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
            full_records.append(full_row)

            property_row = {
                "run_id": run_id,
                "canonical_location_id": canonical,
                "assessment_year": source_assessment_year or None,
                "assessment_value": normalized_value,
                "suite": record.get("suite"),
                "house_number": record.get("house_number"),
                "street_name": record.get("street_name"),
                "legal_description": record.get("legal_description"),
                "zoning": record.get("zoning"),
                "lot_size": _safe_float(record.get("lot_size")),
                "total_gross_area": record.get("total_gross_area"),
                "year_built": _safe_int(record.get("year_built")),
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
                "source_ids_json": json.dumps([source_id]),
                "record_ids_json": json.dumps([record_id]),
                "link_method": link_method,
                "confidence": confidence,
                "updated_at": source_updated_at,
            }
            property_rows_by_location[canonical] = _merge_property_rows(
                property_rows_by_location.get(canonical),
                property_row,
            )

    conn.execute("DELETE FROM assessments_staging WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM assessments_records_staging WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM property_locations_staging WHERE run_id=?", (run_id,))
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
            garage, legal_description, zoning, lot_size, total_gross_area, year_built,
            assessment_class_1, assessment_class_2, assessment_class_3,
            assessment_class_pct_1, assessment_class_pct_2, assessment_class_pct_3,
            lat, lon, point_location, link_method, confidence, ambiguous, quarantined,
            reason_code, raw_record_json
        ) VALUES (
            :run_id, :record_id, :source_id, :assessment_year, :canonical_location_id, :assessment_value,
            :suite, :house_number, :street_name, :neighbourhood_id, :neighbourhood, :ward, :tax_class,
            :garage, :legal_description, :zoning, :lot_size, :total_gross_area, :year_built,
            :assessment_class_1, :assessment_class_2, :assessment_class_3,
            :assessment_class_pct_1, :assessment_class_pct_2, :assessment_class_pct_3,
            :lat, :lon, :point_location, :link_method, :confidence, :ambiguous, :quarantined,
            :reason_code, :raw_record_json
        )
        """,
        full_records,
    )
    conn.executemany(
        """
        INSERT INTO property_locations_staging (
            run_id, canonical_location_id, assessment_year, assessment_value, suite, house_number,
            street_name, legal_description, zoning, lot_size, total_gross_area, year_built,
            neighbourhood_id, neighbourhood, ward, tax_class, garage, assessment_class_1,
            assessment_class_2, assessment_class_3, assessment_class_pct_1, assessment_class_pct_2,
            assessment_class_pct_3, lat, lon, point_location, source_ids_json, record_ids_json,
            link_method, confidence, updated_at
        ) VALUES (
            :run_id, :canonical_location_id, :assessment_year, :assessment_value, :suite, :house_number,
            :street_name, :legal_description, :zoning, :lot_size, :total_gross_area, :year_built,
            :neighbourhood_id, :neighbourhood, :ward, :tax_class, :garage, :assessment_class_1,
            :assessment_class_2, :assessment_class_3, :assessment_class_pct_1, :assessment_class_pct_2,
            :assessment_class_pct_3, :lat, :lon, :point_location, :source_ids_json, :record_ids_json,
            :link_method, :confidence, :updated_at
        )
        """,
        list(property_rows_by_location.values()),
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
            prev_score = (prev["confidence"], _safe_float(prev["assessment_value"]) or -1.0)
            curr_score = (row["confidence"], _safe_float(row["assessment_value"]) or -1.0)
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
            if row["assessment_value"] is not None
        ]

        try:
            with transaction(conn):
                touched_source_ids = sorted({row["source_id"] for row in full_records})
                if touched_source_ids:
                    placeholders = ",".join("?" for _ in touched_source_ids)
                    conn.execute(
                        f"DELETE FROM assessments_records_prod WHERE source_id IN ({placeholders})",
                        touched_source_ids,
                    )
                conn.executemany(
                    """
                    INSERT INTO assessments_prod (
                        canonical_location_id, assessment_year, assessment_value,
                        chosen_record_id, confidence
                    ) VALUES (
                        :canonical_location_id, :assessment_year, :assessment_value,
                        :chosen_record_id, :confidence
                    )
                    ON CONFLICT(canonical_location_id) DO UPDATE SET
                        assessment_year=excluded.assessment_year,
                        assessment_value=excluded.assessment_value,
                        chosen_record_id=excluded.chosen_record_id,
                        confidence=excluded.confidence
                    """,
                    promoted_rows,
                )
                conn.execute(
                    """
                    INSERT INTO assessments_records_prod (
                        record_id, source_id, assessment_year, canonical_location_id, assessment_value,
                        suite, house_number, street_name, neighbourhood_id, neighbourhood, ward, tax_class,
                        garage, legal_description, zoning, lot_size, total_gross_area, year_built,
                        assessment_class_1, assessment_class_2, assessment_class_3,
                        assessment_class_pct_1, assessment_class_pct_2, assessment_class_pct_3,
                        lat, lon, point_location, link_method, confidence, ambiguous, quarantined,
                        reason_code, raw_record_json
                    )
                    SELECT record_id, source_id, assessment_year, canonical_location_id, assessment_value,
                           suite, house_number, street_name, neighbourhood_id, neighbourhood, ward, tax_class,
                           garage, legal_description, zoning, lot_size, total_gross_area, year_built,
                           assessment_class_1, assessment_class_2, assessment_class_3,
                           assessment_class_pct_1, assessment_class_pct_2, assessment_class_pct_3,
                           lat, lon, point_location, link_method, confidence, ambiguous, quarantined,
                           reason_code, raw_record_json
                    FROM assessments_records_staging
                    WHERE run_id=?
                    """,
                    (run_id,),
                )
                existing_properties = {
                    row["canonical_location_id"]: dict(row)
                    for row in conn.execute("SELECT * FROM property_locations_prod").fetchall()
                }
                merged_properties = dict(existing_properties)
                for canonical_id, row in property_rows_by_location.items():
                    merged_properties[canonical_id] = _merge_property_rows(existing_properties.get(canonical_id), row)
                conn.executemany(
                    """
                    INSERT INTO property_locations_prod (
                        canonical_location_id, assessment_year, assessment_value, suite, house_number,
                        street_name, legal_description, zoning, lot_size, total_gross_area, year_built,
                        neighbourhood_id, neighbourhood, ward, tax_class, garage, assessment_class_1,
                        assessment_class_2, assessment_class_3, assessment_class_pct_1, assessment_class_pct_2,
                        assessment_class_pct_3, lat, lon, point_location, source_ids_json, record_ids_json,
                        link_method, confidence, updated_at
                    ) VALUES (
                        :canonical_location_id, :assessment_year, :assessment_value, :suite, :house_number,
                        :street_name, :legal_description, :zoning, :lot_size, :total_gross_area, :year_built,
                        :neighbourhood_id, :neighbourhood, :ward, :tax_class, :garage, :assessment_class_1,
                        :assessment_class_2, :assessment_class_3, :assessment_class_pct_1, :assessment_class_pct_2,
                        :assessment_class_pct_3, :lat, :lon, :point_location, :source_ids_json, :record_ids_json,
                        :link_method, :confidence, :updated_at
                    )
                    ON CONFLICT(canonical_location_id) DO UPDATE SET
                        assessment_year=excluded.assessment_year,
                        assessment_value=excluded.assessment_value,
                        suite=excluded.suite,
                        house_number=excluded.house_number,
                        street_name=excluded.street_name,
                        legal_description=excluded.legal_description,
                        zoning=excluded.zoning,
                        lot_size=excluded.lot_size,
                        total_gross_area=excluded.total_gross_area,
                        year_built=excluded.year_built,
                        neighbourhood_id=excluded.neighbourhood_id,
                        neighbourhood=excluded.neighbourhood,
                        ward=excluded.ward,
                        tax_class=excluded.tax_class,
                        garage=excluded.garage,
                        assessment_class_1=excluded.assessment_class_1,
                        assessment_class_2=excluded.assessment_class_2,
                        assessment_class_3=excluded.assessment_class_3,
                        assessment_class_pct_1=excluded.assessment_class_pct_1,
                        assessment_class_pct_2=excluded.assessment_class_pct_2,
                        assessment_class_pct_3=excluded.assessment_class_pct_3,
                        lat=excluded.lat,
                        lon=excluded.lon,
                        point_location=excluded.point_location,
                        source_ids_json=excluded.source_ids_json,
                        record_ids_json=excluded.record_ids_json,
                        link_method=excluded.link_method,
                        confidence=excluded.confidence,
                        updated_at=excluded.updated_at
                    """,
                    list(merged_properties.values()),
                )
            promotion_status = "promoted"
            record_dataset_version(
                conn,
                dataset_type="assessments",
                version_id=str(assessment_year),
                source_version=str(assessment_year),
                provenance=f"property assessments ({', '.join(selected_source_keys)})",
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
            "merged_properties": len(property_rows_by_location),
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


def run_transit_ingest(
    conn,
    trigger: str = "manual",
    source_keys: list[str] | None = None,
    source_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    run_id = _new_run_id("transit")
    started_at = utc_now()
    warnings: list[str] = []
    errors: list[str] = []
    selected_source_keys = source_keys[:] if source_keys else []
    if not selected_source_keys:
        errors.append("no transit sources selected")

    rows: list[dict[str, Any]] = []
    source_versions: dict[str, str | None] = {}

    for source_key in selected_source_keys:
        spec = get_source_spec(source_key)
        payload = load_payload_for_source(source_key, source_overrides)
        transit_type = spec.get("target_dataset")
        if transit_type not in TRANSIT_DATASETS:
            errors.append(f"{source_key} missing supported transit target_dataset")
            continue
        source_versions[source_key] = payload.metadata.get("version")

        for record in payload.records:
            entity_id = str(record.get("entity_id") or record.get("trip_id") or record.get("stop_id") or "")
            if not entity_id:
                errors.append(f"{source_key} missing entity id")
                continue
            source_id = str(record.get("source_id") or source_key)
            name = _normalize_text(record.get("name") or record.get("stop_name") or record.get("trip_headsign") or record.get("route_id") or entity_id) or entity_id
            points = _extract_geometry_points(record)
            lon = _safe_float(record.get("stop_lon") or record.get("lon"))
            lat = _safe_float(record.get("stop_lat") or record.get("lat"))
            if (lon is None or lat is None) and points:
                lon = sum(point[0] for point in points) / len(points)
                lat = sum(point[1] for point in points) / len(points)

            rows.append(
                {
                    "run_id": run_id,
                    "transit_type": transit_type,
                    "entity_id": entity_id,
                    "source_id": source_id,
                    "name": name,
                    "route_id": record.get("route_id"),
                    "service_id": record.get("service_id"),
                    "trip_id": record.get("trip_id"),
                    "trip_headsign": record.get("trip_headsign"),
                    "direction_id": _safe_int(record.get("direction_id")),
                    "block_id": record.get("block_id"),
                    "shape_id": record.get("shape_id"),
                    "wheelchair_accessible": record.get("wheelchair_accessible"),
                    "bikes_allowed": record.get("bikes_allowed"),
                    "line_length": _safe_float(record.get("line_length")),
                    "stop_id": record.get("stop_id"),
                    "stop_code": record.get("stop_code"),
                    "stop_name": record.get("stop_name"),
                    "stop_desc": record.get("stop_desc"),
                    "stop_lat": _safe_float(record.get("stop_lat")),
                    "stop_lon": _safe_float(record.get("stop_lon")),
                    "zone_id": record.get("zone_id"),
                    "stop_url": record.get("stop_url"),
                    "location_type": _safe_int(record.get("location_type")),
                    "parent_station": record.get("parent_station"),
                    "level_name": record.get("level_name"),
                    "lon": lon,
                    "lat": lat,
                    "geometry_json": json.dumps([[point[0], point[1]] for point in points]),
                    "raw_record_json": json.dumps(record, default=str),
                    "source_version": payload.metadata.get("version"),
                    "updated_at": payload.metadata.get("publish_date"),
                }
            )

    conn.execute("DELETE FROM transit_staging WHERE run_id=?", (run_id,))
    if rows:
        conn.executemany(
            """
            INSERT INTO transit_staging (
                run_id, transit_type, entity_id, source_id, name, route_id, service_id,
                trip_id, trip_headsign, direction_id, block_id, shape_id, wheelchair_accessible,
                bikes_allowed, line_length, stop_id, stop_code, stop_name, stop_desc, stop_lat,
                stop_lon, zone_id, stop_url, location_type, parent_station, level_name, lon, lat,
                geometry_json, raw_record_json, source_version, updated_at
            ) VALUES (
                :run_id, :transit_type, :entity_id, :source_id, :name, :route_id, :service_id,
                :trip_id, :trip_headsign, :direction_id, :block_id, :shape_id, :wheelchair_accessible,
                :bikes_allowed, :line_length, :stop_id, :stop_code, :stop_name, :stop_desc, :stop_lat,
                :stop_lon, :zone_id, :stop_url, :location_type, :parent_station, :level_name, :lon, :lat,
                :geometry_json, :raw_record_json, :source_version, :updated_at
            )
            """,
            rows,
        )

    status = "failed" if errors else "succeeded"
    promotion_status = "failed"
    qa_status = "fail" if errors else "pass"
    if not errors:
        try:
            with transaction(conn):
                touched = sorted({(row["transit_type"], row["source_id"]) for row in rows})
                for transit_type, source_id in touched:
                    conn.execute(
                        "DELETE FROM transit_prod WHERE transit_type=? AND source_id=?",
                        (transit_type, source_id),
                    )
                conn.execute(
                    """
                    INSERT INTO transit_prod (
                        transit_type, entity_id, source_id, name, route_id, service_id,
                        trip_id, trip_headsign, direction_id, block_id, shape_id, wheelchair_accessible,
                        bikes_allowed, line_length, stop_id, stop_code, stop_name, stop_desc, stop_lat,
                        stop_lon, zone_id, stop_url, location_type, parent_station, level_name, lon, lat,
                        geometry_json, raw_record_json, source_version, updated_at
                    )
                    SELECT transit_type, entity_id, source_id, name, route_id, service_id,
                           trip_id, trip_headsign, direction_id, block_id, shape_id, wheelchair_accessible,
                           bikes_allowed, line_length, stop_id, stop_code, stop_name, stop_desc, stop_lat,
                           stop_lon, zone_id, stop_url, location_type, parent_station, level_name, lon, lat,
                           geometry_json, raw_record_json, source_version, updated_at
                    FROM transit_staging
                    WHERE run_id=?
                    """,
                    (run_id,),
                )
            promotion_status = "promoted"
            for source_key in selected_source_keys:
                record_dataset_version(
                    conn,
                    dataset_type=f"transit:{get_source_spec(source_key).get('target_dataset')}",
                    version_id=source_versions.get(source_key) or run_id,
                    source_version=source_versions.get(source_key),
                    provenance=source_key,
                    run_id=run_id,
                )
        except Exception as exc:
            status = "failed"
            errors.append(f"promotion failed: {exc}")
            add_alert(conn, run_id, "error", f"transit promotion failed: {exc}")

    completed_at = utc_now()
    metadata = {
        "row_count": len(rows),
        "qa_status": qa_status,
        "promotion_status": promotion_status,
        "source_keys": selected_source_keys,
    }
    upsert_run_log(
        conn,
        run_id=run_id,
        story="transit",
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
        "row_count": len(rows),
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
