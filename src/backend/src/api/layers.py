from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.backend.src.db.queries import decode_geometry, fetch_geospatial_features
from src.backend.src.services.errors import error_response

router = APIRouter()

LAYER_LEGENDS = {
    "schools": {"title": "Schools", "items": [{"label": "School", "color": "#1d4ed8", "shape": "circle"}]},
    "parks": {"title": "Parks", "items": [{"label": "Park", "color": "#15803d", "shape": "circle"}]},
    "playgrounds": {"title": "Playgrounds", "items": [{"label": "Playground", "color": "#ea580c", "shape": "circle"}]},
    "police_stations": {"title": "Police Stations", "items": [{"label": "Police Station", "color": "#f85149", "shape": "square"}]},
    "businesses": {"title": "Businesses", "items": [{"label": "Commerce", "color": "#9333ea", "shape": "circle"}]},
    "green_space": {"title": "Green Space", "items": [{"label": "Green Space", "color": "#0f766e", "shape": "circle"}]},
    "transit_stops": {"title": "Transit Stops", "items": [{"label": "ETS Stop", "color": "#0891b2", "shape": "circle"}]},
    "roads": {"title": "Roads", "items": [{"label": "Road Segment", "color": "#4b5563", "shape": "line"}]},
    "municipal_wards": {"title": "Municipal Wards", "items": [{"label": "Ward Boundary", "color": "#d97706", "shape": "polygon"}]},
    "provincial_districts": {"title": "Provincial Districts", "items": [{"label": "Provincial District", "color": "#7c3aed", "shape": "polygon"}]},
    "federal_districts": {"title": "Federal Districts", "items": [{"label": "Federal District", "color": "#be123c", "shape": "polygon"}]},
    "census_subdivisions": {"title": "Census Subdivisions", "items": [{"label": "Census Subdivision", "color": "#334155", "shape": "polygon"}]},
    "census_boundaries": {"title": "Census Boundaries", "items": [{"label": "Census Boundary", "color": "#475569", "shape": "polygon"}]},
}


@router.get("/layers/{layer_id}")
async def get_layer(request: Request, layer_id: str, west: float, south: float, east: float, north: float, zoom: float):
    request_id = request.state.request_id
    settings = request.app.state.settings
    if layer_id not in settings.enabled_layers:
        return JSONResponse(
            status_code=404,
            content=error_response(
                request_id,
                code="LAYER_DISABLED",
                message=f"Layer '{layer_id}' is disabled by configuration.",
                details={"layer_id": layer_id},
                retryable=False,
            ),
        )
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
                "address": row.get("address"),
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
