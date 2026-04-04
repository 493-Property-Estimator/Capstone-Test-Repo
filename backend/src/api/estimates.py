from __future__ import annotations

import time
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.config import EDMONTON_BOUNDS
from backend.src.db.queries import get_location_by_id, resolve_address, get_latest_dataset_version
from backend.src.services.validation import validate_location_payload, coords_in_bounds
from backend.src.services.errors import validation_error_response, error_response
from backend.src.services.features import compute_proximity_factors, compute_comparable_adjustment
from backend.src.services.warnings import build_missing_data_warning, build_routing_warning
from backend.src.services.routing import compute_distance

router = APIRouter()


@router.post("/estimates")
async def create_estimate(request: Request, payload: dict):
    request_id = request.state.request_id
    issues = validate_location_payload(payload)
    if issues:
        status = 422 if any(i.reason in {"out_of_range", "not_numeric"} for i in issues) else 400
        body, status_code = validation_error_response(request_id, issues, status)
        return JSONResponse(status_code=status_code, content=body)

    location = payload.get("location") or {}
    options = payload.get("options") or {}
    strict = options.get("strict") if options.get("strict") is not None else request.app.state.settings.enable_strict_mode_default
    required_factors = options.get("required_factors") or []

    settings = request.app.state.settings
    cache = request.app.state.cache
    metrics = request.app.state.metrics

    canonical = None
    coords = None
    if location.get("canonical_location_id"):
        canonical = get_location_by_id(settings.data_db_path, location["canonical_location_id"])
    if location.get("address"):
        matches = resolve_address(settings.data_db_path, location["address"], limit=1)
        canonical = matches[0] if matches else None
    if location.get("coordinates"):
        coords = location.get("coordinates")
    elif canonical and canonical.lat is not None and canonical.lon is not None:
        coords = {"lat": canonical.lat, "lng": canonical.lon}

    if coords is None:
        return JSONResponse(
            status_code=422,
            content=error_response(
                request_id,
                code="UNRESOLVABLE_LOCATION",
                message="Location could not be resolved.",
                details={},
                retryable=False,
            ),
        )

    if not coords_in_bounds(coords):
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

    dataset_version = get_latest_dataset_version(settings.data_db_path)
    cache_key = _cache_key(coords, location, options)
    cached, cache_status = cache.get(cache_key, dataset_version)
    if cached:
        metrics.cache_hit_ratio = cache.ratio()
        response = cached
        response["request_id"] = request_id
        headers = {"X-Cache-Status": cache_status.upper()}
        return JSONResponse(status_code=200, content=response, headers=headers)

    valuation_start = time.time()
    baseline_value = None
    canonical_id = canonical.canonical_location_id if canonical else None
    if canonical and canonical.assessment_value is not None:
        baseline_value = canonical.assessment_value
    if baseline_value is None:
        return JSONResponse(
            status_code=424,
            content=error_response(
                request_id,
                code="BASELINE_MISSING",
                message="Baseline assessment value unavailable.",
                details={"canonical_location_id": canonical_id},
                retryable=False,
            ),
        )

    point = (coords["lng"], coords["lat"])
    factor_results, missing = compute_proximity_factors(point, settings.data_db_path)

    approximations = []
    routing_warning = None
    if factor_results:
        # treat routing as approximated for proximity distances
        routing = compute_distance(
            origin=(coords["lat"], coords["lng"]),
            target=(coords["lat"], coords["lng"]),
            routing_enabled=settings.enable_routing,
            metrics=metrics,
        )
        if routing.fallback_used:
            approximations.append("commute_accessibility")
            routing_warning = build_routing_warning(["commute_accessibility"], routing.reason)

    if strict and required_factors:
        missing_required = [f for f in required_factors if f in missing]
        if missing_required:
            return JSONResponse(
                status_code=424,
                content={
                    "request_id": request_id,
                    "error": {
                        "code": "REQUIRED_FACTOR_MISSING",
                        "message": "Required factor unavailable.",
                        "details": {"missing_required_datasets": missing_required},
                        "retryable": False,
                    },
                },
            )

    adjustments_sum = sum(fr.value for fr in factor_results)
    comp_adjustment = compute_comparable_adjustment(point, baseline_value, settings.data_db_path)
    final_estimate = max(0.0, baseline_value + adjustments_sum + comp_adjustment)
    range_low = max(0.0, final_estimate * 0.93)
    range_high = final_estimate * 1.07

    confidence = _confidence_from_missing(len(missing), total=max(len(factor_results), 1))

    warnings = build_missing_data_warning(missing)
    if routing_warning:
        warnings.append(routing_warning)

    response = {
        "request_id": request_id,
        "estimate_id": f"est_{canonical_id or 'coords'}",
        "status": "partial" if missing else "ok",
        "location": {
            "canonical_location_id": canonical_id,
            "canonical_address": _format_address(canonical),
            "coordinates": coords,
            "region": "Edmonton",
            "neighbourhood": canonical.neighbourhood if canonical else None,
            "coverage_status": "supported",
        },
        "baseline_value": baseline_value,
        "final_estimate": final_estimate,
        "range": {"low": range_low, "high": range_high},
        "factor_breakdown": [
            {
                "factor_id": fr.factor_id,
                "label": fr.label,
                "value": fr.value,
                "status": fr.status,
                "summary": fr.summary,
            }
            for fr in factor_results
        ],
        "confidence": confidence,
        "warnings": warnings,
        "missing_factors": missing,
        "approximations": approximations,
    }

    metrics.record_valuation((time.time() - valuation_start) * 1000)
    cache.set(cache_key, response, dataset_version)
    metrics.cache_hit_ratio = cache.ratio()
    headers = {"X-Cache-Status": cache_status.upper()}
    return JSONResponse(status_code=200, content=response, headers=headers)


def _cache_key(coords: dict, location: dict, options: dict) -> str:
    key_parts = [
        f"lat={coords.get('lat')}",
        f"lng={coords.get('lng')}",
        f"id={location.get('canonical_location_id')}",
        f"addr={location.get('address')}",
        f"options={sorted(options.items())}",
    ]
    return "|".join(key_parts)


def _confidence_from_missing(missing_count: int, total: int) -> dict:
    completeness_ratio = max(0.0, 1.0 - missing_count / max(total, 1))
    score = round(0.6 + 0.4 * completeness_ratio, 2)
    percentage = int(score * 100)
    if score >= 0.85:
        label = "high"
    elif score >= 0.7:
        label = "medium"
    else:
        label = "low"
    return {
        "score": score,
        "percentage": percentage,
        "label": label,
        "completeness": "complete" if missing_count == 0 else "partial",
    }


def _format_address(record) -> str | None:
    if not record:
        return None
    house = (record.house_number or "").strip()
    street = (record.street_name or "").strip()
    if house and street:
        return f"{house} {street}, Edmonton, AB"
    return street or None
