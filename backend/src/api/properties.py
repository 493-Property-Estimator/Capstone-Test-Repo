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
    limit: int = 5000,
    cursor: str | None = None,
):
    request_id = request.state.request_id

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

    if zoom < 0 or zoom > 25:
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

    settings = request.app.state.settings
    cache = request.app.state.cache
    dataset_version = get_latest_dataset_version(settings.data_db_path)
    cache_key = build_property_cache_key(
        west=west,
        south=south,
        east=east,
        north=north,
        zoom=zoom,
        limit=max(100, min(limit, 10000)),
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
        limit=max(100, min(limit, 10000)),
        cursor=cursor,
    )
    cache.set(cache_key, payload, dataset_version)
    payload["request_id"] = request_id
    return payload
