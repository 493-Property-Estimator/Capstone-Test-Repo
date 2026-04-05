from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.config import EDMONTON_BOUNDS
from backend.src.db.queries import get_location_by_id, resolve_address
from backend.src.services.errors import error_response, validation_error_response
from backend.src.services.validation import coords_in_bounds, validate_location_payload
from estimator import estimate_property_value

router = APIRouter()


@router.post("/estimates")
async def create_estimate(request: Request, payload: dict):
    request_id = request.state.request_id
    issues = validate_location_payload(payload)
    if issues:
        status = 422 if any(issue.reason in {"out_of_range", "not_numeric"} for issue in issues) else 400
        body, status_code = validation_error_response(request_id, issues, status)
        return JSONResponse(status_code=status_code, content=body)

    location = payload.get("location") if isinstance(payload.get("location"), dict) else {}
    property_details = payload.get("property_details") or {}
    settings = request.app.state.settings

    canonical = None
    if location.get("canonical_location_id"):
        canonical = get_location_by_id(settings.data_db_path, location["canonical_location_id"])
    if canonical is None and location.get("address"):
        matches = resolve_address(settings.data_db_path, location["address"], limit=1)
        canonical = matches[0] if matches else None

    coords = location.get("coordinates") if isinstance(location.get("coordinates"), dict) else None
    if coords is None and canonical and canonical.lat is not None and canonical.lon is not None:
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

    try:
        estimate = estimate_property_value(
            settings.data_db_path,
            lat=float(coords["lat"]),
            lon=float(coords["lng"]),
            property_attributes=property_details,
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

    return _adapt_estimator_response(estimate, canonical, request_id)


def _adapt_estimator_response(estimate: dict, canonical, request_id: str) -> dict:
    matched_property = estimate.get("matched_property") or {}
    query_point = estimate.get("query_point") or {}
    warnings = [_adapt_warning(item) for item in estimate.get("warnings", [])]
    factor_breakdown = [_adapt_factor(item) for item in estimate.get("feature_breakdown", {}).get("valuation_adjustments", [])]
    confidence_score = float(estimate.get("confidence_score") or 0.0)
    completeness_score = float(estimate.get("completeness_score") or 0.0)

    return {
        "request_id": request_id,
        "estimate_id": estimate.get("request_id"),
        "status": "partial" if warnings or estimate.get("missing_factors") else "ok",
        "location": {
            "canonical_location_id": matched_property.get("canonical_location_id")
            or getattr(canonical, "canonical_location_id", None),
            "canonical_address": matched_property.get("address") or _format_address(canonical),
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
        "baseline_value": estimate.get("baseline", {}).get("assessment_value"),
        "final_estimate": estimate.get("final_estimate"),
        "range": {
            "low": estimate.get("low_estimate"),
            "high": estimate.get("high_estimate"),
        },
        "factor_breakdown": factor_breakdown,
        "confidence": {
            "score": round(confidence_score, 2),
            "percentage": int(round(confidence_score * 100)),
            "label": str(estimate.get("confidence_label") or "unknown"),
            "completeness": "complete" if completeness_score >= 0.99 else "partial",
        },
        "warnings": warnings,
        "missing_factors": estimate.get("missing_factors", []),
        "approximations": estimate.get("fallback_flags", []),
    }


def _adapt_factor(item: dict) -> dict:
    metadata = item.get("metadata") or {}
    summary_bits = [f"{key.replace('_', ' ')}: {value}" for key, value in metadata.items()]
    return {
        "factor_id": item.get("code"),
        "label": item.get("label"),
        "value": item.get("value"),
        "status": "available",
        "summary": "; ".join(summary_bits) if summary_bits else "Derived from the estimator feature model.",
    }


def _adapt_warning(item: dict) -> dict:
    severity = item.get("severity") or "warning"
    title = str(item.get("code") or "estimator_warning").replace("_", " ").title()
    return {
        "code": item.get("code"),
        "severity": severity,
        "title": title,
        "message": item.get("message") or "Estimator warning.",
        "affected_factors": [],
        "dismissible": False,
    }


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
