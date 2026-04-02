from __future__ import annotations

from fastapi import APIRouter, Request

from backend.src.config import EDMONTON_BOUNDS
from backend.src.db.queries import get_location_by_id
from estimator import proximity

router = APIRouter()


@router.post("/locations/resolve-click")
async def resolve_click(request: Request, payload: dict):
    request_id = request.state.request_id
    click_id = payload.get("click_id")
    coords = payload.get("coordinates") or {}
    lat = coords.get("lat")
    lng = coords.get("lng")
    if lat is None or lng is None:
        return {
            "request_id": request_id,
            "status": "resolution_error",
            "click_id": click_id,
            "location": None,
            "error": {
                "code": "CLICK_RESOLUTION_FAILED",
                "message": "Location could not be determined from the click.",
                "details": {},
                "retryable": True,
            },
        }
    if not _in_bounds(lat, lng):
        return {
            "request_id": request_id,
            "status": "outside_supported_area",
            "click_id": click_id,
            "location": None,
            "error": {
                "code": "OUTSIDE_SUPPORTED_AREA",
                "message": "Location is outside the supported area.",
                "details": {},
                "retryable": False,
            },
        }
    settings = request.app.state.settings
    nearest = proximity.get_top_closest_properties(
        point=(lng, lat),
        limit=1,
        distance_mode="manhattan",
        db_path=settings.data_db_path,
    )
    if not nearest:
        return {
            "request_id": request_id,
            "status": "resolution_error",
            "click_id": click_id,
            "location": None,
            "error": {
                "code": "CLICK_RESOLUTION_FAILED",
                "message": "Location could not be determined from the click.",
                "details": {},
                "retryable": True,
            },
        }
    record = nearest[0]
    canonical_id = record.get("canonical_location_id")
    location_record = get_location_by_id(settings.data_db_path, canonical_id) if canonical_id else None
    address = _format_address(location_record) if location_record else None
    return {
        "request_id": request_id,
        "status": "resolved",
        "click_id": click_id,
        "location": {
            "canonical_location_id": canonical_id,
            "canonical_address": address,
            "coordinates": {"lat": lat, "lng": lng},
            "region": "Edmonton",
            "neighbourhood": location_record.neighbourhood if location_record else None,
            "coverage_status": "supported",
        },
    }


def _in_bounds(lat: float, lng: float) -> bool:
    return (
        EDMONTON_BOUNDS["west"] <= lng <= EDMONTON_BOUNDS["east"]
        and EDMONTON_BOUNDS["south"] <= lat <= EDMONTON_BOUNDS["north"]
    )


def _format_address(record) -> str | None:
    if not record:
        return None
    house = (record.house_number or "").strip()
    street = (record.street_name or "").strip()
    if house and street:
        return f"{house} {street}, Edmonton, AB"
    return street or None
