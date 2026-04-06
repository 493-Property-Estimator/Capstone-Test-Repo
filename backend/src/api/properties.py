from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.db.queries import get_latest_dataset_version
from backend.src.services.errors import error_response
from backend.src.services.property_viewport import (
    build_property_cache_key,
    fetch_property_viewport,
)

router = APIRouter()


@router.get("/properties")
async def get_properties(
    request: Request,
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: float,
    limit: int | None = None,
    cursor: str | None = None,
):
    request_id = request.state.request_id

    settings = request.app.state.settings

    if west >= east or south >= north:
        return JSONResponse(
            status_code=400,
            content=error_response(
                request_id,
                code="INVALID_BBOX",
                message="Bounding box is invalid.",
                details={},
                retryable=False,
            ),
        )

    if zoom < settings.properties_zoom_min or zoom > settings.properties_zoom_max:
        return JSONResponse(
            status_code=400,
            content=error_response(
                request_id,
                code="INVALID_ZOOM",
                message="Zoom level is invalid.",
                details={},
                retryable=False,
            ),
        )

    cache = request.app.state.cache
    default_limit = max(1, int(settings.properties_default_limit))
    min_limit = max(1, int(settings.properties_limit_min))
    max_limit = max(min_limit, int(settings.properties_limit_max))
    requested_limit = default_limit if limit is None else limit
    bounded_limit = max(min_limit, min(requested_limit, max_limit))
    dataset_version = get_latest_dataset_version(settings.data_db_path)
    cache_key = build_property_cache_key(
        west=west,
        south=south,
        east=east,
        north=north,
        zoom=zoom,
        limit=bounded_limit,
        cursor=cursor,
    )
    cached, _ = cache.get(cache_key, dataset_version)

    if cached:
        response = dict(cached)
        response["request_id"] = request_id
        return response

    payload = fetch_property_viewport(
        settings.data_db_path,
        west=west,
        south=south,
        east=east,
        north=north,
        zoom=zoom,
        limit=bounded_limit,
        cursor=cursor,
    )
    cache.set(cache_key, payload, dataset_version)
    payload["request_id"] = request_id
    return payload
