from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.src.db.queries import fetch_property_locations_bbox
from backend.src.services.errors import error_response

router = APIRouter()


def _parse_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    if not cursor.startswith("offset:"):
        return 0
    try:
        value = int(cursor.split(":", 1)[1])
    except ValueError:
        return 0
    return max(0, value)


def _format_property_description(row: dict) -> str:
    assessment_value = row.get("assessment_value")
    assessment_text = (
        f"${int(round(float(assessment_value))):,}"
        if assessment_value is not None
        else "--"
    )
    neighbourhood = row.get("neighbourhood") or "--"
    ward = row.get("ward") or "--"
    tax_class = row.get("tax_class") or "--"
    return (
        f"Assessment: {assessment_text} | "
        f"Neighbourhood: {neighbourhood} | "
        f"Ward: {ward} | "
        f"Tax class: {tax_class}"
    )


def _property_details(row: dict) -> dict:
    return {
        "assessment_year": row.get("assessment_year"),
        "assessment_value": row.get("assessment_value"),
        "suite": row.get("suite"),
        "house_number": row.get("house_number"),
        "street_name": row.get("street_name"),
        "legal_description": row.get("legal_description"),
        "zoning": row.get("zoning"),
        "lot_size": row.get("lot_size"),
        "total_gross_area": row.get("total_gross_area"),
        "year_built": row.get("year_built"),
        "neighbourhood_id": row.get("neighbourhood_id"),
        "neighbourhood": row.get("neighbourhood"),
        "ward": row.get("ward"),
        "tax_class": row.get("tax_class"),
        "garage": row.get("garage"),
        "assessment_class_1": row.get("assessment_class_1"),
        "assessment_class_2": row.get("assessment_class_2"),
        "assessment_class_3": row.get("assessment_class_3"),
        "assessment_class_pct_1": row.get("assessment_class_pct_1"),
        "assessment_class_pct_2": row.get("assessment_class_pct_2"),
        "assessment_class_pct_3": row.get("assessment_class_pct_3"),
        "bedrooms": row.get("bedrooms"),
        "bathrooms": row.get("bathrooms"),
        "bedrooms_estimated": row.get("bedrooms_estimated"),
        "bathrooms_estimated": row.get("bathrooms_estimated"),
        "attribute_source_type": row.get("attribute_source_type"),
        "attribute_source_name": row.get("attribute_source_name"),
        "attribute_confidence": row.get("attribute_confidence"),
        "location_confidence": row.get("location_confidence"),
        "point_location": row.get("point_location"),
        "source_ids_json": row.get("source_ids_json"),
        "record_ids_json": row.get("record_ids_json"),
        "link_method": row.get("link_method"),
    }


def _cluster_properties(properties: list[dict], zoom: float) -> list[dict]:
    bucket_size = (
        0.03
        if zoom <= 11
        else 0.024
        if zoom <= 12
        else 0.018
        if zoom <= 13
        else 0.012
        if zoom <= 14
        else 0.008
        if zoom <= 15
        else 0.005
        if zoom <= 16
        else 0.003
    )

    buckets: dict[tuple[int, int], list[dict]] = {}
    for item in properties:
        lat = float(item["coordinates"]["lat"])
        lng = float(item["coordinates"]["lng"])
        key = (int(lng / bucket_size), int(lat / bucket_size))
        buckets.setdefault(key, []).append(item)

    clusters: list[dict] = []
    for idx, bucket in enumerate(buckets.values()):
        count = len(bucket)
        lng_values = [float(entry["coordinates"]["lng"]) for entry in bucket]
        lat_values = [float(entry["coordinates"]["lat"]) for entry in bucket]
        clusters.append(
            {
                "cluster_id": f"cluster-{int(round(zoom * 100))}-{idx}",
                "center": {
                    "lat": sum(lat_values) / count,
                    "lng": sum(lng_values) / count,
                },
                "count": count,
                "bounds": {
                    "west": min(lng_values),
                    "south": min(lat_values),
                    "east": max(lng_values),
                    "north": max(lat_values),
                },
                "sample_properties": [
                    {
                        "canonical_location_id": entry["canonical_location_id"],
                        "canonical_address": entry["canonical_address"],
                        "assessment_value": entry["assessment_value"],
                    }
                    for entry in bucket[:3]
                ],
            }
        )
    return clusters


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
    settings = request.app.state.settings
    if "assessment_properties" not in settings.enabled_layers:
        return JSONResponse(
            status_code=404,
            content=error_response(
                request_id,
                code="LAYER_DISABLED",
                message="Layer 'assessment_properties' is disabled by configuration.",
                details={"layer_id": "assessment_properties"},
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

    bounded_limit = max(1, min(limit, 5000))
    offset = _parse_cursor(cursor)

    rows = fetch_property_locations_bbox(
        settings.data_db_path,
        west=west,
        south=south,
        east=east,
        north=north,
        limit=bounded_limit + 1,
        offset=offset,
    )

    has_more = len(rows) > bounded_limit
    rows = rows[:bounded_limit]

    properties = []
    for row in rows:
        house = (row.get("house_number") or "").strip()
        street = (row.get("street_name") or "").strip()
        canonical_address = (
            f"{house} {street}, Edmonton, AB".strip().replace("  ", " ")
            if house or street
            else "Edmonton property"
        )
        properties.append(
            {
                "canonical_location_id": row["canonical_location_id"],
                "canonical_address": canonical_address,
                "coordinates": {"lat": row["lat"], "lng": row["lon"]},
                "neighbourhood": row.get("neighbourhood"),
                "ward": row.get("ward"),
                "assessment_value": row.get("assessment_value"),
                "tax_class": row.get("tax_class"),
                "name": canonical_address,
                "description": _format_property_description(row),
                "details": _property_details(row),
            }
        )

    render_mode = "cluster" if zoom < 17 else "property"
    clusters = _cluster_properties(properties, zoom) if render_mode == "cluster" else []
    response_properties = properties if render_mode == "property" else []

    return {
        "request_id": request_id,
        "status": "partial" if has_more else "ok",
        "coverage_status": "partial" if has_more else "complete",
        "viewport": {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
            "zoom": zoom,
        },
        "render_mode": render_mode,
        "legend": {
            "title": "Assessment Properties",
            "items": [
                {"label": "Cluster", "color": "#a43434", "shape": "circle"}
                if render_mode == "cluster"
                else {"label": "Property", "color": "#a43434", "shape": "circle"}
            ],
        },
        "clusters": clusters,
        "properties": response_properties,
        "page": {
            "has_more": has_more,
            "next_cursor": f"offset:{offset + bounded_limit}" if has_more else None,
        },
        "warnings": [],
    }
