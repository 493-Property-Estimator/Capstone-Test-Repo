from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.db.queries import search_address_suggestions, resolve_address
from backend.src.services.errors import error_response
from backend.src.config import EDMONTON_BOUNDS

router = APIRouter()


@router.get("/search/suggestions")
async def search_suggestions(request: Request, q: str, limit: int | None = None):
    request_id = request.state.request_id
    settings = request.app.state.settings
    min_chars = max(1, int(settings.search_query_min_chars))
    if len(q.strip()) < min_chars:
        return JSONResponse(
            status_code=400,
            content=error_response(
                request_id,
                code="INVALID_QUERY",
                message=f"Search query must contain at least {min_chars} characters.",
                details={"field": "q", "reason": "too_short"},
                retryable=False,
            ),
        )
    default_limit = max(1, int(settings.search_suggestions_default_limit))
    min_limit = max(1, int(settings.search_suggestions_limit_min))
    max_limit = max(min_limit, int(settings.search_suggestions_limit_max))
    requested_limit = default_limit if limit is None else limit
    bounded_limit = max(min_limit, min(requested_limit, max_limit))
    suggestions = search_address_suggestions(settings.data_db_path, q, bounded_limit)
    return {
        "request_id": request_id,
        "query": q,
        "suggestions": suggestions,
    }


@router.get("/search/resolve")
async def resolve_search(request: Request, q: str):
    request_id = request.state.request_id
    settings = request.app.state.settings
    min_chars = max(1, int(settings.search_query_min_chars))
    if len(q.strip()) < min_chars:
        return JSONResponse(
            status_code=400,
            content=error_response(
                request_id,
                code="INVALID_QUERY",
                message=f"Search query must contain at least {min_chars} characters.",
                details={"field": "q", "reason": "too_short"},
                retryable=False,
            ),
        )
    match_limit = max(1, int(settings.search_resolve_match_limit))
    matches = resolve_address(settings.data_db_path, q, limit=match_limit)
    if not matches:
        return {
            "request_id": request_id,
            "status": "not_found",
            "location": None,
            "candidates": [],
        }
    if len(matches) > 1:
        candidates = [
            {
                "candidate_id": row.canonical_location_id,
                "canonical_location_id": row.canonical_location_id,
                "display_text": _format_address(row),
                "coordinates": {"lat": row.lat, "lng": row.lon},
                "coverage_status": "supported" if _in_bounds(row.lat, row.lon) else "unsupported",
            }
            for row in matches
        ]
        return {
            "request_id": request_id,
            "status": "ambiguous",
            "location": None,
            "candidates": candidates,
        }
    record = matches[0]
    location = {
        "canonical_location_id": record.canonical_location_id,
        "canonical_address": _format_address(record),
        "coordinates": {"lat": record.lat, "lng": record.lon},
        "region": "Edmonton",
        "neighbourhood": record.neighbourhood,
        "coverage_status": "supported" if _in_bounds(record.lat, record.lon) else "unsupported",
    }
    if location["coverage_status"] == "unsupported":
        return {
            "request_id": request_id,
            "status": "unsupported_region",
            "location": location,
            "candidates": [],
        }
    return {
        "request_id": request_id,
        "status": "resolved",
        "location": location,
        "candidates": [],
    }


def _format_address(record) -> str:
    house = (record.house_number or "").strip() if hasattr(record, "house_number") else ""
    street = (record.street_name or "").strip() if hasattr(record, "street_name") else ""
    if house and street:
        return f"{house} {street}, Edmonton, AB"
    return street or ""


def _in_bounds(lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None:
        return False
    return (
        EDMONTON_BOUNDS["west"] <= lng <= EDMONTON_BOUNDS["east"]
        and EDMONTON_BOUNDS["south"] <= lat <= EDMONTON_BOUNDS["north"]
    )
