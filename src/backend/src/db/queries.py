from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

from backend.src.db.connection import connect


@dataclass(frozen=True)
class LocationRecord:
    canonical_location_id: str
    house_number: str | None
    street_name: str | None
    neighbourhood: str | None
    ward: str | None
    assessment_value: float | None
    lat: float | None
    lon: float | None


def _format_address(row: dict[str, Any]) -> str:
    house = (row.get("house_number") or "").strip()
    street = (row.get("street_name") or "").strip()
    if house and street:
        return f"{house} {street}, Edmonton, AB"
    return row.get("street_name") or ""


def _normalize_search_text(query: str) -> str:
    # Keep only the street-address portion and normalize punctuation/spacing.
    base = (query or "").split(",", 1)[0].upper()
    base = re.sub(r"[^A-Z0-9 ]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base


def search_address_suggestions(db_path: Path, query: str, limit: int) -> list[dict[str, Any]]:
    normalized = _normalize_search_text(query)
    if not normalized:
        return []
    like = f"%{normalized}%"
    sql = """
        SELECT canonical_location_id, house_number, street_name, neighbourhood, lat, lon
        FROM property_locations_prod
        WHERE UPPER(COALESCE(house_number, '') || ' ' || COALESCE(street_name, '')) LIKE ?
        LIMIT ?
    """
    with connect(db_path) as conn:
        rows = conn.execute(sql, (like, limit)).fetchall()
    suggestions = []
    for idx, row in enumerate(rows, start=1):
        row = dict(row)
        suggestions.append(
            {
                "id": f"sug_{row.get('canonical_location_id', idx)}",
                "display_text": _format_address(row),
                "secondary_text": row.get("neighbourhood"),
                "rank": idx,
                "confidence": "high" if idx == 1 else "medium",
            }
        )
    return suggestions


def resolve_address(db_path: Path, query: str, limit: int = 5) -> list[LocationRecord]:
    normalized = _normalize_search_text(query)
    if not normalized:
        return []
    like = f"%{normalized}%"
    sql = """
        SELECT canonical_location_id, house_number, street_name, neighbourhood, ward,
               assessment_value, lat, lon
        FROM property_locations_prod
        WHERE UPPER(COALESCE(house_number, '') || ' ' || COALESCE(street_name, '')) LIKE ?
        LIMIT ?
    """
    with connect(db_path) as conn:
        rows = conn.execute(sql, (like, limit)).fetchall()
    return [
        LocationRecord(
            canonical_location_id=row["canonical_location_id"],
            house_number=row["house_number"],
            street_name=row["street_name"],
            neighbourhood=row["neighbourhood"],
            ward=row["ward"],
            assessment_value=row["assessment_value"],
            lat=row["lat"],
            lon=row["lon"],
        )
        for row in rows
    ]


def get_location_by_id(db_path: Path, canonical_location_id: str) -> LocationRecord | None:
    sql = """
        SELECT canonical_location_id, house_number, street_name, neighbourhood, ward,
               assessment_value, lat, lon
        FROM property_locations_prod
        WHERE canonical_location_id = ?
    """
    with connect(db_path) as conn:
        row = conn.execute(sql, (canonical_location_id,)).fetchone()
    if not row:
        return None
    return LocationRecord(
        canonical_location_id=row["canonical_location_id"],
        house_number=row["house_number"],
        street_name=row["street_name"],
        neighbourhood=row["neighbourhood"],
        ward=row["ward"],
        assessment_value=row["assessment_value"],
        lat=row["lat"],
        lon=row["lon"],
    )


def resolve_coordinates_to_location(db_path: Path, lat: float, lon: float) -> LocationRecord | None:
    sql = """
        SELECT canonical_location_id, house_number, street_name, neighbourhood, ward,
               assessment_value, lat, lon
        FROM property_locations_prod
        WHERE lat IS NOT NULL
          AND lon IS NOT NULL
        ORDER BY
          ((lat - ?) * (lat - ?))
          + ((lon - ?) * (lon - ?)),
          canonical_location_id
        LIMIT 1
    """
    with connect(db_path) as conn:
        row = conn.execute(sql, (lat, lat, lon, lon)).fetchone()
    if not row:
        return None
    return LocationRecord(
        canonical_location_id=row["canonical_location_id"],
        house_number=row["house_number"],
        street_name=row["street_name"],
        neighbourhood=row["neighbourhood"],
        ward=row["ward"],
        assessment_value=row["assessment_value"],
        lat=row["lat"],
        lon=row["lon"],
    )


def fetch_geospatial_features(
    db_path: Path,
    layer_id: str,
    west: float,
    south: float,
    east: float,
    north: float,
) -> list[dict[str, Any]]:
    boundary_layers = {
        "municipal_wards",
        "provincial_districts",
        "federal_districts",
        "census_subdivisions",
        "census_boundaries",
    }
    if layer_id.lower() in boundary_layers:
        sql = """
            SELECT dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat, geometry_json
            FROM geospatial_prod
        """
        params: tuple[float, ...] = ()
    else:
        sql = """
            SELECT dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat, geometry_json
            FROM geospatial_prod
            WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?
        """
        params = (west, east, south, north)
    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    features = []
    for row in rows:
        row = dict(row)
        if not _matches_layer(layer_id, row):
            continue
        features.append(row)
    return features


def _matches_layer(layer_id: str, row: dict[str, Any]) -> bool:
    dataset_type = (row.get("dataset_type") or "").lower()
    raw_category = (row.get("raw_category") or "").lower()
    source_id = (row.get("source_id") or "").lower()
    layer = layer_id.lower()
    aliases = {
        "schools": {"source_ids": {"geospatial.school_locations"}, "raw_categories": {"school"}},
        "parks": {"source_ids": {"geospatial.parks"}, "raw_categories": {"park", "dog_park"}},
        "playgrounds": {"source_ids": {"geospatial.playgrounds"}, "raw_categories": {"playground"}},
        "police_stations": {"source_ids": {"geospatial.police_stations"}, "raw_categories": {"police"}},
        "municipal_wards": {"source_ids": {"geospatial.municipal_wards"}},
        "provincial_districts": {"source_ids": {"geospatial.provincial_districts"}},
        "federal_districts": {"source_ids": {"geospatial.federal_districts"}},
        "census_subdivisions": {"source_ids": {"geospatial.census_subdivisions"}},
        "census_boundaries": {
            "source_ids": {
                "geospatial.municipal_wards",
                "geospatial.provincial_districts",
                "geospatial.federal_districts",
                "geospatial.census_subdivisions",
            }
        },
    }
    config = aliases.get(layer)
    if config:
        if source_id in config.get("source_ids", set()):
            return True
        if raw_category in config.get("raw_categories", set()):
            return True
        return False
    return layer in dataset_type or layer in raw_category


def decode_geometry(row: dict[str, Any]) -> dict[str, Any]:
    raw_geometry = row.get("geometry_json")
    if raw_geometry:
        try:
            geometry = json.loads(raw_geometry)
        except json.JSONDecodeError:
            geometry = None
        if isinstance(geometry, dict) and geometry.get("type") and geometry.get("coordinates") is not None:
            return geometry
    return {
        "type": "Point",
        "coordinates": [row["lon"], row["lat"]],
    }


def get_latest_dataset_version(db_path: Path) -> str | None:
    sql = """
        SELECT version_id
        FROM dataset_versions
        ORDER BY promoted_at DESC
        LIMIT 1
    """
    with connect(db_path) as conn:
        row = conn.execute(sql).fetchone()
    if not row:
        return None
    return row["version_id"]


def fetch_property_locations_bbox(
    db_path: Path,
    west: float,
    south: float,
    east: float,
    north: float,
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = """
        SELECT
            canonical_location_id,
            house_number,
            street_name,
            neighbourhood,
            ward,
            assessment_value,
            tax_class,
            lat,
            lon
        FROM property_locations_prod
        WHERE lat IS NOT NULL
          AND lon IS NOT NULL
          AND lon BETWEEN ? AND ?
          AND lat BETWEEN ? AND ?
        ORDER BY canonical_location_id
        LIMIT ?
        OFFSET ?
    """
    with connect(db_path) as conn:
        rows = conn.execute(sql, (west, east, south, north, limit, offset)).fetchall()
    return [dict(row) for row in rows]
