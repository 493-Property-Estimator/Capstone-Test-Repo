from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.db.queries import decode_geometry, fetch_geospatial_features
from backend.src.services.errors import error_response

router = APIRouter()

LAYER_LEGENDS = {
    "schools": {"title": "Schools", "items": [{"label": "School", "color": "#1f6feb", "shape": "circle"}]},
    "parks": {"title": "Parks", "items": [{"label": "Park", "color": "#2ea043", "shape": "circle"}]},
    "playgrounds": {"title": "Playgrounds", "items": [{"label": "Playground", "color": "#f0883e", "shape": "circle"}]},
    "police_stations": {"title": "Police Stations", "items": [{"label": "Police Station", "color": "#f85149", "shape": "square"}]},
    "municipal_wards": {"title": "Municipal Wards", "items": [{"label": "Ward Boundary", "color": "#b45309", "shape": "polygon"}]},
    "provincial_districts": {"title": "Provincial Districts", "items": [{"label": "Provincial District", "color": "#7c3aed", "shape": "polygon"}]},
    "federal_districts": {"title": "Federal Districts", "items": [{"label": "Federal District", "color": "#0f766e", "shape": "polygon"}]},
    "census_subdivisions": {"title": "Census Subdivisions", "items": [{"label": "Census Subdivision", "color": "#475569", "shape": "polygon"}]},
}


@router.get("/layers/{layer_id}")
async def get_layer(request: Request, layer_id: str, west: float, south: float, east: float, north: float, zoom: float):
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
    settings = request.app.state.settings
    rows = fetch_geospatial_features(settings.data_db_path, layer_id, west, south, east, north)
    features = [
        {
            "type": "Feature",
            "geometry": decode_geometry(row),
            "properties": {
                "id": row["entity_id"],
                "name": row["name"],
                "category": row["raw_category"],
                "source_id": row["source_id"],
                "address": None,
            },
        }
        for row in rows
    ]
    return {
        "request_id": request_id,
        "layer_id": layer_id,
        "status": "ok",
        "coverage_status": "complete" if rows else "partial",
        "legend": LAYER_LEGENDS.get(layer_id, {"title": layer_id, "items": []}),
        "features": features,
        "warnings": [] if rows else [{"code": "NO_DATA", "message": "No features available."}],
    }
