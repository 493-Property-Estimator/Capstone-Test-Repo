from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import hashlib
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.config import EDMONTON_BOUNDS
from backend.src.db.queries import (
    get_latest_dataset_version,
    get_location_by_id,
    resolve_address,
    resolve_coordinates_to_location,
)
from backend.src.services.errors import error_response, validation_error_response
from backend.src.services.validation import (
    coords_in_bounds,
    validate_location_payload,
    validate_property_details,
)
from estimator import estimate_property_value

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/estimates")
async def create_estimate(request: Request, payload: Any = None):
    request_id = request.state.request_id
    raw_body = await request.body()
    if (payload is None or payload == {} or not isinstance(payload, (dict, str))) and raw_body:
        try:
            parsed_body = json.loads(raw_body.decode("utf-8"))
            payload = parsed_body
        except Exception:
            pass
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}

    location_issues = validate_location_payload(payload)
    detail_issues = validate_property_details(payload)
    issues = [*location_issues, *detail_issues]
    if issues:
        logger.warning(
            "estimate_validation_failed request_id=%s issues=%s payload=%s",
            request_id,
            [
                {
                    "field": issue.field,
                    "reason": issue.reason,
                    "correction": issue.correction,
                }
                for issue in issues
            ],
            payload,
        )
        status = 422 if any(issue.reason in {"out_of_range", "not_numeric"} for issue in issues) else 400
        body, status_code = validation_error_response(request_id, issues, status)
        return JSONResponse(status_code=status_code, content=body)

    settings = request.app.state.settings
    metrics = request.app.state.metrics
    cache = request.app.state.cache
    location = payload.get("location") or {}
    canonical = None

    if location.get("canonical_location_id"):
        canonical = get_location_by_id(settings.data_db_path, location["canonical_location_id"])
    if canonical is None and location.get("property_id"):
        canonical = get_location_by_id(settings.data_db_path, location["property_id"])
    if canonical is None and location.get("address"):
        matches = resolve_address(settings.data_db_path, location["address"], limit=5)
        if len(matches) > 1:
            return JSONResponse(
                status_code=422,
                content=error_response(
                    request_id,
                    code="UNRESOLVABLE_LOCATION",
                    message="Address is ambiguous. Select one of the candidate locations.",
                    details={
                        "candidates": [
                            {
                                "canonical_location_id": item.canonical_location_id,
                                "display_text": _format_address(item),
                                "coordinates": {"lat": item.lat, "lng": item.lon},
                            }
                            for item in matches
                        ]
                    },
                    retryable=False,
                ),
            )
        canonical = matches[0] if matches else None

    coords = location.get("coordinates")
    if coords is None and location.get("polygon"):
        coords = _polygon_centroid(location["polygon"])
    if coords is None and canonical and canonical.lat is not None and canonical.lon is not None:
        coords = {"lat": float(canonical.lat), "lng": float(canonical.lon)}
    if coords is not None and canonical is None:
        canonical = resolve_coordinates_to_location(
            settings.data_db_path,
            lat=float(coords["lat"]),
            lon=float(coords["lng"]),
        )

    if coords is None:
        return JSONResponse(
            status_code=422,
            content=error_response(
                request_id,
                code="UNRESOLVABLE_LOCATION",
                message="Location could not be resolved.",
                details={
                    "guidance": "Provide a more specific address, use map click, or provide coordinates inside Edmonton.",
                },
                retryable=False,
            ),
        )

    if not coords_in_bounds({"lat": float(coords["lat"]), "lng": float(coords["lng"])}):
        return JSONResponse(
            status_code=422,
            content=error_response(
                request_id,
                code="OUTSIDE_SUPPORTED_AREA",
                message="Coordinates must be within the supported Edmonton area.",
                details={},
                retryable=False,
            ),
        )

    normalized_attributes, attribute_usage = _normalize_property_details(payload.get("property_details") or {})
    dataset_version = get_latest_dataset_version(settings.data_db_path)
    cache_key = _build_cache_key(location, coords, canonical, normalized_attributes, dataset_version)
    cached_value = None
    cache_status = "MISS"
    try:
        cached_value, cache_status_raw = cache.get(cache_key, dataset_version)
        cache_status = cache_status_raw.upper()
    except Exception:
        cache_status = "MISS"
        cached_value = None

    if cached_value is not None:
        return JSONResponse(
            status_code=200,
            content=cached_value,
            headers={"X-Cache-Status": "HIT"},
        )

    started = time.perf_counter()
    try:
        estimate = await asyncio.wait_for(
            asyncio.to_thread(
                estimate_property_value,
                settings.data_db_path,
                lat=float(coords["lat"]),
                lon=float(coords["lng"]),
                property_attributes=normalized_attributes,
            ),
            timeout=max(settings.estimate_time_budget_seconds, 0.1),
        )
    except TimeoutError:
        return JSONResponse(
            status_code=503,
            content=error_response(
                request_id,
                code="TIME_BUDGET_EXCEEDED",
                message="Estimate request exceeded the valuation time budget.",
                details={"budget_seconds": settings.estimate_time_budget_seconds},
                retryable=True,
            ),
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=424,
            content=error_response(
                request_id,
                code="ESTIMATE_UNAVAILABLE",
                message=str(exc),
                details={},
                retryable=False,
            ),
        )
    metrics.record_valuation((time.perf_counter() - started) * 1000)

    response_payload = _adapt_estimator_response(
        estimate=estimate,
        canonical=canonical,
        request_id=request_id,
        attribute_usage=attribute_usage,
        cache_status=cache_status,
    )

    try:
        cache.set(cache_key, response_payload, dataset_version)
    except Exception:
        pass
    metrics.cache_hit_ratio = cache.ratio()
    return JSONResponse(
        status_code=200,
        content=response_payload,
        headers={"X-Cache-Status": cache_status if cache_status in {"MISS", "STALE"} else "MISS"},
    )


def _adapt_estimator_response(
    *,
    estimate: dict[str, Any],
    canonical,
    request_id: str,
    attribute_usage: dict[str, Any],
    cache_status: str,
) -> dict[str, Any]:
    matched_property = estimate.get("matched_property") or {}
    query_point = estimate.get("query_point") or {}
    missing_factors = list(estimate.get("missing_factors", []))
    warnings = [_adapt_warning(item) for item in estimate.get("warnings", [])]
    factor_breakdown = _adapt_factors(estimate, missing_factors)
    confidence_score = float(estimate.get("confidence_score") or 0.0)
    completeness_score = float(estimate.get("completeness_score") or 0.0)
    baseline = estimate.get("baseline") or {}

    return {
        "request_id": request_id,
        "estimate_id": estimate.get("request_id"),
        "status": "partial" if warnings or missing_factors else "ok",
        "estimated_at": datetime.now(UTC).isoformat(),
        "location": {
            "canonical_location_id": matched_property.get("canonical_location_id")
            or baseline.get("canonical_location_id")
            or getattr(canonical, "canonical_location_id", None),
            "canonical_address": matched_property.get("address")
            or baseline.get("address")
            or _format_address(canonical),
            "coordinates": {
                "lat": query_point.get("lat"),
                "lng": query_point.get("lon"),
            },
            "region": "Edmonton",
            "neighbourhood": matched_property.get("neighbourhood") or getattr(canonical, "neighbourhood", None),
            "coverage_status": "supported"
            if _in_bounds(query_point.get("lat"), query_point.get("lon"))
            else "unsupported",
        },
        "baseline_value": baseline.get("assessment_value"),
        "baseline": {
            "type": baseline.get("baseline_type"),
            "source": baseline.get("source_table"),
            "assessment_year": baseline.get("assessment_year"),
            "distance_to_query_m": baseline.get("distance_to_query_m"),
        },
        "final_estimate": estimate.get("final_estimate"),
        "range": {
            "low": estimate.get("low_estimate"),
            "high": estimate.get("high_estimate"),
        },
        "factor_breakdown": factor_breakdown,
        "top_positive_factors": [_adapt_factor(item) for item in estimate.get("top_positive_factors", [])],
        "top_negative_factors": [_adapt_factor(item) for item in estimate.get("top_negative_factors", [])],
        "confidence": {
            "score": round(confidence_score, 2),
            "percentage": int(round(confidence_score)),
            "label": str(estimate.get("confidence_label") or "unknown"),
            "completeness": "complete" if completeness_score >= 99.0 else "partial",
        },
        "property_details_incorporation": attribute_usage,
        "warnings": warnings,
        "missing_factors": missing_factors,
        "approximations": estimate.get("fallback_flags", []),
        "cache": {"status": cache_status},
    }


def _adapt_factors(estimate: dict[str, Any], missing_factors: list[str]) -> list[dict[str, Any]]:
    factors = [
        _adapt_factor(item) for item in estimate.get("feature_breakdown", {}).get("valuation_adjustments", [])
    ]
    known_ids = {item.get("factor_id") for item in factors}
    for code in missing_factors:
        if code in known_ids:
            continue
        factors.append(
            {
                "factor_id": code,
                "label": code.replace("_", " ").title(),
                "value": None,
                "status": "missing",
                "summary": "Unavailable in the current dataset/version for this query.",
            }
        )
    return factors


def _adapt_factor(item: dict) -> dict:
    metadata = item.get("metadata") or {}
    summary_bits = [f"{key.replace('_', ' ')}: {value}" for key, value in metadata.items()]
    return {
        "factor_id": item.get("code"),
        "label": item.get("label"),
        "value": item.get("value"),
        "status": item.get("status") or "available",
        "summary": "; ".join(summary_bits) if summary_bits else "Derived from the estimator feature model.",
    }


def _adapt_warning(item: dict) -> dict:
    severity = item.get("severity") or "warning"
    code = item.get("code")
    title = str(code or "estimator_warning").replace("_", " ").title()
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": item.get("message") or "Estimator warning.",
        "affected_factors": _derive_affected_factors(code),
        "dismissible": False,
    }


def _derive_affected_factors(code: str | None) -> list[str]:
    if not code:
        return []
    lowered = code.lower()
    if "park" in lowered:
        return ["park_access"]
    if "playground" in lowered:
        return ["playground_access"]
    if "school" in lowered:
        return ["school_access"]
    if "library" in lowered:
        return ["library_access"]
    if "crime" in lowered:
        return ["crime_statistics"]
    return []


def _format_address(record) -> str | None:
    if not record:
        return None
    house = (record.house_number or "").strip()
    street = (record.street_name or "").strip()
    if house and street:
        return f"{house} {street}, Edmonton, AB"
    return street or None


def _in_bounds(lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None:
        return False
    return (
        EDMONTON_BOUNDS["west"] <= lng <= EDMONTON_BOUNDS["east"]
        and EDMONTON_BOUNDS["south"] <= lat <= EDMONTON_BOUNDS["north"]
    )


def _build_cache_key(
    location: dict[str, Any],
    coords: dict[str, Any],
    canonical,
    normalized_attributes: dict[str, Any],
    dataset_version: str | None,
) -> str:
    signature = {
        "coords": {
            "lat": round(float(coords["lat"]), 6),
            "lng": round(float(coords["lng"]), 6),
        },
        "canonical_location_id": (
            getattr(canonical, "canonical_location_id", None)
            or (location.get("canonical_location_id") or None)
        ),
        "address": (location.get("address") or "").strip().upper(),
        "property_details": normalized_attributes,
        "dataset_version": dataset_version,
    }
    digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode("utf-8")).hexdigest()
    return f"estimate:{digest}"


def _normalize_property_details(details: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized: dict[str, Any] = {}
    accepted_fields: list[str] = []
    rejected_fields: list[str] = []
    aliases = {"floor_area_sqft": "total_gross_area"}

    for key in sorted(details.keys()):
        value = details.get(key)
        if value in (None, ""):
            continue
        output_key = aliases.get(key, key)
        try:
            normalized[output_key] = float(value)
            accepted_fields.append(key)
        except Exception:
            rejected_fields.append(key)

    usage = {
        "provided_count": len([k for k, v in details.items() if v not in (None, "")]),
        "accepted_count": len(accepted_fields),
        "accepted_fields": accepted_fields,
        "rejected_fields": rejected_fields,
        "mode": "full"
        if accepted_fields and not rejected_fields
        else ("partial" if accepted_fields else "none"),
    }
    return normalized, usage


def _polygon_centroid(polygon: dict[str, Any]) -> dict[str, float] | None:
    try:
        ring = (polygon.get("coordinates") or [])[0]
        if not ring:
            return None
        points = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
        if not points:
            return None
        lng = sum(float(p[0]) for p in points) / len(points)
        lat = sum(float(p[1]) for p in points) / len(points)
        return {"lat": lat, "lng": lng}
    except Exception:
        return None
