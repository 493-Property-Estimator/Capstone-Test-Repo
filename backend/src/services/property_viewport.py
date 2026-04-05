from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.src.db.connection import connect

_INDEXES_READY = False


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
    ensure_property_indexes(db_path)

    if zoom < 17:
        return _build_cluster_response(
            db_path,
            west=west,
            south=south,
            east=east,
            north=north,
            zoom=zoom,
        )

    return _build_property_response(
        db_path,
        west=west,
        south=south,
        east=east,
        north=north,
        zoom=zoom,
        limit=limit,
        cursor=cursor,
    )


def ensure_property_indexes(db_path: Path) -> None:
    global _INDEXES_READY

    if _INDEXES_READY:
        return

    statements = [
        """
        CREATE INDEX IF NOT EXISTS idx_property_locations_prod_lon_lat
        ON property_locations_prod (lon, lat)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_property_locations_prod_canonical_location_id
        ON property_locations_prod (canonical_location_id)
        """,
    ]

    with connect(db_path) as conn:
        for statement in statements:
            conn.execute(statement)
        conn.commit()

    _INDEXES_READY = True


def _build_cluster_response(
    db_path: Path,
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: float,
) -> dict[str, Any]:
    bucket_size = _cluster_bucket_size(zoom)
    sql = """
        SELECT
            CAST((lon - ?) / ? AS INTEGER) AS bucket_x,
            CAST((lat - ?) / ? AS INTEGER) AS bucket_y,
            COUNT(*) AS point_count,
            AVG(lat) AS center_lat,
            AVG(lon) AS center_lng,
            MIN(lon) AS min_lng,
            MIN(lat) AS min_lat,
            MAX(lon) AS max_lng,
            MAX(lat) AS max_lat,
            MIN(canonical_location_id) AS sample_id,
            MIN(house_number) AS sample_house_number,
            MIN(street_name) AS sample_street_name,
            MAX(assessment_value) AS sample_assessment_value
        FROM property_locations_prod
        WHERE lon BETWEEN ? AND ?
          AND lat BETWEEN ? AND ?
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        GROUP BY bucket_x, bucket_y
        ORDER BY point_count DESC, bucket_y ASC, bucket_x ASC
    """

    with connect(db_path) as conn:
        rows = conn.execute(
            sql,
            (
                west,
                bucket_size,
                south,
                bucket_size,
                west,
                east,
                south,
                north,
            ),
        ).fetchall()

    clusters = [
        {
            "cluster_id": f"cluster-z{int(zoom)}-{index}",
            "center": {
                "lat": row["center_lat"],
                "lng": row["center_lng"],
            },
            "count": row["point_count"],
            "bounds": {
                "west": row["min_lng"],
                "south": row["min_lat"],
                "east": row["max_lng"],
                "north": row["max_lat"],
            },
            "sample_properties": [
                {
                    "canonical_location_id": row["sample_id"],
                    "canonical_address": _format_address_from_values(
                        row["sample_house_number"], row["sample_street_name"]
                    ),
                    "assessment_value": row["sample_assessment_value"],
                }
            ],
        }
        for index, row in enumerate(rows, start=1)
    ]

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
    db_path: Path,
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
        LIMIT ? OFFSET ?
    """

    with connect(db_path) as conn:
        rows = conn.execute(
            sql,
            (
                west,
                east,
                south,
                north,
                limit + 1,
                offset,
            ),
        ).fetchall()

    records = [
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
        for row in rows[:limit]
    ]
    has_more = len(rows) > limit

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
            for row in records
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


def build_property_cache_key(
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: float,
    limit: int,
    cursor: str | None,
) -> str:
    return "|".join(
        [
            f"properties",
            f"w={west:.4f}",
            f"s={south:.4f}",
            f"e={east:.4f}",
            f"n={north:.4f}",
            f"z={zoom:.2f}",
            f"limit={limit}",
            f"cursor={cursor or ''}",
        ]
    )


def _format_address(row: PropertyViewportRecord) -> str:
    return _format_address_from_values(row.house_number, row.street_name)


def _format_address_from_values(house_number: str | None, street_name: str | None) -> str:
    house = (house_number or "").strip()
    street = (street_name or "").strip()

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
