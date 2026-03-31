from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.services.errors import error_response
from backend.src.services.property_viewport import fetch_property_viewport

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
    payload["request_id"] = request_id
    return payload
