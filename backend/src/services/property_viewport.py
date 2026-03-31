from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.src.db.connection import connect


@dataclass(frozen=True)
class PropertyViewportRecord:
    canonical_location_id: str
    house_number: str | None
    street_name: str | None
    neighbourhood: str | None
    ward: str | None
    tax_class: str | None
    assessment_value: float | None
    lat: float
    lon: float


def fetch_property_viewport(
    db_path: Path,
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: float,
    limit: int = 5000,
    cursor: str | None = None,
) -> dict[str, Any]:
    rows = _fetch_property_rows(
        db_path,
        west=west,
        south=south,
        east=east,
        north=north,
    )

    if zoom < 17:
      return _build_cluster_response(
            rows,
            west=west,
            south=south,
            east=east,
            north=north,
            zoom=zoom,
        )

    return _build_property_response(
        rows,
        west=west,
        south=south,
        east=east,
        north=north,
        zoom=zoom,
        limit=limit,
        cursor=cursor,
    )


def _fetch_property_rows(
    db_path: Path,
    *,
    west: float,
    south: float,
    east: float,
    north: float,
) -> list[PropertyViewportRecord]:
    sql = """
        SELECT
            canonical_location_id,
            house_number,
            street_name,
            neighbourhood,
            ward,
            tax_class,
            assessment_value,
            lat,
            lon
        FROM property_locations_prod
        WHERE lon BETWEEN ? AND ?
          AND lat BETWEEN ? AND ?
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        ORDER BY lat ASC, lon ASC, canonical_location_id ASC
    """

    with connect(db_path) as conn:
        rows = conn.execute(sql, (west, east, south, north)).fetchall()

    return [
        PropertyViewportRecord(
            canonical_location_id=row["canonical_location_id"],
            house_number=row["house_number"],
            street_name=row["street_name"],
            neighbourhood=row["neighbourhood"],
            ward=row["ward"],
            tax_class=row["tax_class"],
            assessment_value=row["assessment_value"],
            lat=float(row["lat"]),
            lon=float(row["lon"]),
        )
        for row in rows
    ]


def _build_cluster_response(
    rows: list[PropertyViewportRecord],
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: float,
) -> dict[str, Any]:
    bucket_size = _cluster_bucket_size(zoom)
    buckets: dict[tuple[int, int], list[PropertyViewportRecord]] = {}

    for row in rows:
        key = (
            int((row.lon - west) / bucket_size),
            int((row.lat - south) / bucket_size),
        )
        buckets.setdefault(key, []).append(row)

    clusters = []
    for index, bucket_rows in enumerate(buckets.values(), start=1):
        lngs = [row.lon for row in bucket_rows]
        lats = [row.lat for row in bucket_rows]
        clusters.append(
            {
                "cluster_id": f"cluster-z{int(zoom)}-{index}",
                "center": {
                    "lat": sum(lats) / len(lats),
                    "lng": sum(lngs) / len(lngs),
                },
                "count": len(bucket_rows),
                "bounds": {
                    "west": min(lngs),
                    "south": min(lats),
                    "east": max(lngs),
                    "north": max(lats),
                },
                "sample_properties": [
                    {
                        "canonical_location_id": row.canonical_location_id,
                        "canonical_address": _format_address(row),
                        "assessment_value": row.assessment_value,
                    }
                    for row in bucket_rows[:3]
                ],
            }
        )

    return {
        "status": "ok",
        "coverage_status": "complete",
        "viewport": {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
            "zoom": zoom,
        },
        "render_mode": "cluster",
        "legend": {
            "title": "Assessment Properties",
            "items": [{"label": "Cluster", "color": "#a43434", "shape": "circle"}],
        },
        "clusters": clusters,
        "properties": [],
        "page": {
            "has_more": False,
            "next_cursor": None,
        },
        "warnings": [],
    }


def _build_property_response(
    rows: list[PropertyViewportRecord],
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: float,
    limit: int,
    cursor: str | None,
) -> dict[str, Any]:
    offset = _parse_cursor(cursor)
    sliced = rows[offset : offset + limit]
    has_more = offset + limit < len(rows)

    return {
        "status": "partial" if has_more else "ok",
        "coverage_status": "partial" if has_more else "complete",
        "viewport": {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
            "zoom": zoom,
        },
        "render_mode": "property",
        "legend": {
            "title": "Assessment Properties",
            "items": [{"label": "Property", "color": "#a43434", "shape": "circle"}],
        },
        "clusters": [],
        "properties": [
            {
                "canonical_location_id": row.canonical_location_id,
                "canonical_address": _format_address(row),
                "coordinates": {
                    "lat": row.lat,
                    "lng": row.lon,
                },
                "neighbourhood": row.neighbourhood,
                "ward": row.ward,
                "assessment_value": row.assessment_value,
                "tax_class": row.tax_class,
                "source_meta": {
                    "provider": "city_of_edmonton",
                    "dataset_id": "q7d6-ambg",
                    "record_id": row.canonical_location_id,
                    "license": "Open Government Licence",
                    "attribution": "City of Edmonton Open Data",
                },
            }
            for row in sliced
        ],
        "page": {
            "has_more": has_more,
            "next_cursor": f"offset:{offset + limit}" if has_more else None,
        },
        "warnings": (
            [
                {
                    "code": "RESULT_TRUNCATED",
                    "severity": "info",
                    "title": "Viewport results paginated",
                    "message": "Only part of the visible property set was returned in this response.",
                    "affected_factors": [],
                    "dismissible": True,
                }
            ]
            if has_more
            else []
        ),
    }


def _format_address(row: PropertyViewportRecord) -> str:
    house = (row.house_number or "").strip()
    street = (row.street_name or "").strip()

    if house and street:
        return f"{house} {street}, Edmonton, AB"

    return street or "Edmonton, AB"


def _parse_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0

    if not cursor.startswith("offset:"):
        return 0

    try:
        return max(0, int(cursor.split(":", 1)[1]))
    except ValueError:
        return 0


def _cluster_bucket_size(zoom: float) -> float:
    if zoom <= 11:
        return 0.03
    if zoom <= 12:
        return 0.024
    if zoom <= 13:
        return 0.018
    if zoom <= 14:
        return 0.012
    if zoom <= 15:
        return 0.008
    if zoom <= 16:
        return 0.005
    return 0.003
