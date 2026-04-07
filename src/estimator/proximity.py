"""Proximity queries for properties and amenities stored in the local SQLite DB."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
import heapq
import json
import math
from pathlib import Path
import sqlite3
from typing import Any

from src.data_sourcing.config import DEFAULT_DB_PATH
from src.data_sourcing.database import connect

Point = tuple[float, float]
DistanceMode = str

EARTH_RADIUS_M = 6_371_000.0
SCHOOL_QUERY = {
    "source_ids": {"geospatial.school_locations"},
    "raw_categories": {"school"},
}
POLICE_QUERY = {
    "source_ids": {"geospatial.police_stations"},
    "raw_categories": {"police", "police_station"},
}
PLAYGROUND_QUERY = {
    "source_ids": {"geospatial.playgrounds"},
    "raw_categories": {"playground"},
}
PARK_QUERY = {
    "source_ids": {"geospatial.parks"},
    "raw_categories": {"park", "dog_park"},
}
LIBRARY_QUERY = {
    "source_ids": set(),
    "raw_categories": {"library", "public library", "virtual library"},
}
ROAD_MODE_CANDIDATE_MULTIPLIER = 25
ROAD_MODE_MIN_CANDIDATES = 200
ROAD_NODE_PRECISION = 6
ROAD_GRID_SIZE_DEGREES = 0.01
ROAD_GRID_SEARCH_STEPS = 4


class RoadNetworkError(RuntimeError):
    """Raised when road-distance routing cannot be computed."""


def get_top_closest_properties(
    point: Point,
    limit: int = 5,
    distance_mode: DistanceMode = "manhattan",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return the closest properties to a point."""

    lon, lat = _validate_point(point)
    limit = _validate_limit(limit)
    mode = _normalize_distance_mode(distance_mode)

    rows = _fetch_properties(
        db_path=db_path,
        limit=_candidate_limit(limit) if mode == "road" else limit,
        center=(lon, lat),
    )
    return _rank_rows(rows, center=(lon, lat), limit=limit, mode=mode, db_path=db_path)


def get_properties_on_same_street(
    point: Point,
    distance_mode: DistanceMode = "manhattan",
    street_name: str | None = None,
    limit: int | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """
    Return properties on the same street as the point.

    If ``street_name`` is omitted, the function infers it from the closest property
    to the given point using Manhattan distance.
    """

    lon, lat = _validate_point(point)
    mode = _normalize_distance_mode(distance_mode)
    resolved_street = (street_name or _infer_street_name((lon, lat), db_path)).strip()
    if not resolved_street:
        return []

    resolved_limit = _validate_limit(limit) if limit is not None else None
    rows = _fetch_properties_by_street(db_path=db_path, street_name=resolved_street)
    ranked = _rank_rows(rows, center=(lon, lat), limit=resolved_limit, mode=mode, db_path=db_path)
    for row in ranked:
        row["matched_street_name"] = resolved_street
    return ranked


def get_nearest_schools(
    point: Point,
    limit: int = 5,
    distance_mode: DistanceMode = "manhattan",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return the nearest schools to a point."""

    return _get_nearest_geospatial_rows(point, SCHOOL_QUERY, limit, distance_mode, db_path)


def get_nearest_police_stations(
    point: Point,
    limit: int = 5,
    distance_mode: DistanceMode = "manhattan",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return the nearest police stations to a point."""

    return _get_nearest_geospatial_rows(point, POLICE_QUERY, limit, distance_mode, db_path)


def get_nearest_playgrounds(
    point: Point,
    limit: int = 5,
    distance_mode: DistanceMode = "manhattan",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return the nearest playgrounds to a point."""

    return _get_nearest_geospatial_rows(point, PLAYGROUND_QUERY, limit, distance_mode, db_path)


def get_nearest_parks(
    point: Point,
    limit: int = 5,
    distance_mode: DistanceMode = "manhattan",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return the nearest parks to a point."""

    return _get_nearest_geospatial_rows(point, PARK_QUERY, limit, distance_mode, db_path)


def get_nearest_libraries(
    point: Point,
    limit: int = 5,
    distance_mode: DistanceMode = "manhattan",
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return the nearest libraries to a point using POI data."""

    lon, lat = _validate_point(point)
    resolved_limit = _validate_limit(limit)
    mode = _normalize_distance_mode(distance_mode)
    rows = _fetch_library_rows(
        db_path=db_path,
        limit=_candidate_limit(resolved_limit) if mode == "road" else resolved_limit,
        center=(lon, lat),
    )
    return _rank_rows(rows, center=(lon, lat), limit=resolved_limit, mode=mode, db_path=db_path)


def get_neighbourhood_context(
    point: Point,
    other_limit: int = 4,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Return primary and nearby neighbourhood aggregates using property centroids."""

    lon, lat = _validate_point(point)
    resolved_limit = _validate_limit(other_limit)
    rows = _fetch_neighbourhood_aggregates(db_path)
    if not rows:
        return {
            "primary_neighbourhood": None,
            "primary_average_assessment": None,
            "other_neighbourhoods": [],
            "resolution_method": "unavailable",
        }

    ranked = []
    for row in rows:
        centroid = (float(row["centroid_lon"]), float(row["centroid_lat"]))
        ranked.append(
            {
                **row,
                "distance_m": round(_geodesic_distance_m((lon, lat), centroid), 2),
            }
        )
    ranked.sort(
        key=lambda item: (
            item["distance_m"],
            str(item["neighbourhood"]).upper(),
        )
    )
    primary = ranked[0]
    others = [item for item in ranked[1:] if item["neighbourhood"] != primary["neighbourhood"]]
    return {
        "primary_neighbourhood": primary["neighbourhood"],
        "primary_average_assessment": primary["average_assessment"],
        "primary_property_count": primary["property_count"],
        "primary_centroid": {
            "lat": primary["centroid_lat"],
            "lon": primary["centroid_lon"],
        },
        "other_neighbourhoods": others[:resolved_limit],
        "resolution_method": "nearest_neighbourhood_centroid",
    }


def get_downtown_accessibility(
    point: Point,
    downtown_point: Point = (-113.4938, 53.5461),
) -> dict[str, Any]:
    """Return straight-line accessibility to the default downtown Edmonton point."""

    lon, lat = _validate_point(point)
    downtown_lon, downtown_lat = _validate_point(downtown_point)
    return {
        "target": {
            "name": "Downtown Edmonton",
            "lat": downtown_lat,
            "lon": downtown_lon,
        },
        "straight_line_m": round(
            _geodesic_distance_m((lon, lat), (downtown_lon, downtown_lat)),
            2,
        ),
        "distance_mode": "straight_line",
    }


def group_comparables_by_attributes(
    point: Point,
    attributes: dict[str, Any] | None,
    limit: int = 20,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> dict[str, list[dict[str, Any]]]:
    """Return nearby property comparables split by whether they match supplied attributes."""

    lon, lat = _validate_point(point)
    resolved_limit = _validate_limit(limit)
    rows = _fetch_properties(
        db_path=db_path,
        limit=max(resolved_limit * 4, 60),
        center=(lon, lat),
    )
    ranked = _rank_rows(rows, center=(lon, lat), limit=None, mode="manhattan", db_path=db_path)
    normalized_attributes = _normalize_comparable_attributes(attributes or {})

    matching: list[dict[str, Any]] = []
    non_matching: list[dict[str, Any]] = []
    for row in ranked:
        candidate = dict(row)
        candidate["attribute_match"] = _matches_comparable_attributes(candidate, normalized_attributes)
        if normalized_attributes and candidate["attribute_match"]:
            matching.append(candidate)
        else:
            non_matching.append(candidate)

    return {
        "matching": matching[:resolved_limit],
        "non_matching": non_matching[:resolved_limit],
    }


def _get_nearest_geospatial_rows(
    point: Point,
    query_spec: dict[str, set[str]],
    limit: int,
    distance_mode: DistanceMode,
    db_path: Path | str,
) -> list[dict[str, Any]]:
    lon, lat = _validate_point(point)
    resolved_limit = _validate_limit(limit)
    mode = _normalize_distance_mode(distance_mode)

    rows = _fetch_geospatial_rows(
        db_path=db_path,
        source_ids=query_spec["source_ids"],
        raw_categories=query_spec["raw_categories"],
        limit=_candidate_limit(resolved_limit) if mode == "road" else resolved_limit,
        center=(lon, lat),
    )
    return _rank_rows(rows, center=(lon, lat), limit=resolved_limit, mode=mode, db_path=db_path)


def _infer_street_name(point: Point, db_path: Path | str) -> str:
    nearest = get_top_closest_properties(
        point=point,
        limit=1,
        distance_mode="manhattan",
        db_path=db_path,
    )
    if not nearest:
        return ""
    return str(nearest[0].get("street_name") or "")


def _fetch_properties(
    db_path: Path | str,
    limit: int | None,
    center: Point,
) -> list[dict[str, Any]]:
    _require_table(db_path, "property_locations_prod")
    sql = """
        SELECT
            pl.canonical_location_id,
            pl.suite,
            pl.house_number,
            pl.street_name,
            pl.neighbourhood,
            pl.ward,
            pl.assessment_value,
            pl.lat,
            pl.lon,
            pl.point_location,
            pl.zoning,
            pl.lot_size,
            pl.total_gross_area,
            pl.year_built,
            pl.garage,
            pl.tax_class,
            pl.assessment_class_1,
            pl.assessment_class_2,
            pl.assessment_class_3,
            COALESCE(pa.bedrooms, pa.bedrooms_estimated) AS bedrooms,
            COALESCE(pa.bathrooms, pa.bathrooms_estimated) AS bathrooms
        FROM property_locations_prod pl
        LEFT JOIN property_attributes_prod pa
          ON pa.canonical_location_id = pl.canonical_location_id
        WHERE lon IS NOT NULL
          AND lat IS NOT NULL
    """
    params: list[Any] = []
    if limit is not None:
        sql += " ORDER BY ABS(lon - ?) + ABS(lat - ?) LIMIT ?"
        params.extend([center[0], center[1], limit])
    return _query_rows(db_path, sql, params)


def _fetch_properties_by_street(db_path: Path | str, street_name: str) -> list[dict[str, Any]]:
    _require_table(db_path, "property_locations_prod")
    sql = """
        SELECT
            pl.canonical_location_id,
            pl.suite,
            pl.house_number,
            pl.street_name,
            pl.neighbourhood,
            pl.ward,
            pl.assessment_value,
            pl.lat,
            pl.lon,
            pl.point_location,
            pl.zoning,
            pl.lot_size,
            pl.total_gross_area,
            pl.year_built,
            pl.garage,
            pl.tax_class,
            pl.assessment_class_1,
            pl.assessment_class_2,
            pl.assessment_class_3,
            COALESCE(pa.bedrooms, pa.bedrooms_estimated) AS bedrooms,
            COALESCE(pa.bathrooms, pa.bathrooms_estimated) AS bathrooms
        FROM property_locations_prod pl
        LEFT JOIN property_attributes_prod pa
          ON pa.canonical_location_id = pl.canonical_location_id
        WHERE lon IS NOT NULL
          AND lat IS NOT NULL
          AND TRIM(COALESCE(street_name, '')) = TRIM(?)
    """
    return _query_rows(db_path, sql, [street_name])


def _fetch_geospatial_rows(
    db_path: Path | str,
    source_ids: set[str],
    raw_categories: set[str],
    limit: int | None,
    center: Point,
) -> list[dict[str, Any]]:
    _require_table(db_path, "geospatial_prod")
    source_placeholders = ", ".join("?" for _ in source_ids)
    source_sql = f"""
        SELECT
            entity_id,
            source_id,
            name,
            raw_category,
            canonical_geom_type,
            lat,
            lon
        FROM geospatial_prod
        WHERE dataset_type = 'pois'
          AND lon IS NOT NULL
          AND lat IS NOT NULL
          AND source_id IN ({source_placeholders})
    """
    source_params: list[Any] = list(source_ids)
    if limit is not None:
        source_sql += " ORDER BY ABS(lon - ?) + ABS(lat - ?) LIMIT ?"
        source_params.extend([center[0], center[1], limit])

    preferred_rows = _query_rows(db_path, source_sql, source_params)
    if preferred_rows:
        return preferred_rows

    category_placeholders = ", ".join("?" for _ in raw_categories)
    fallback_sql = f"""
        SELECT
            entity_id,
            source_id,
            name,
            raw_category,
            canonical_geom_type,
            lat,
            lon
        FROM geospatial_prod
        WHERE dataset_type = 'pois'
          AND lon IS NOT NULL
          AND lat IS NOT NULL
          AND LOWER(COALESCE(raw_category, '')) IN ({category_placeholders})
    """
    fallback_params: list[Any] = [value.lower() for value in raw_categories]
    if limit is not None:
        fallback_sql += " ORDER BY ABS(lon - ?) + ABS(lat - ?) LIMIT ?"
        fallback_params.extend([center[0], center[1], limit])
    return _query_rows(db_path, fallback_sql, fallback_params)


def _fetch_library_rows(
    db_path: Path | str,
    limit: int | None,
    center: Point,
) -> list[dict[str, Any]]:
    _require_table(db_path, "poi_prod")
    sql = """
        SELECT
            canonical_poi_id AS entity_id,
            source_dataset AS source_id,
            name,
            COALESCE(raw_subcategory, raw_category) AS raw_category,
            'point' AS canonical_geom_type,
            lat,
            lon
        FROM poi_prod
        WHERE lon IS NOT NULL
          AND lat IS NOT NULL
          AND (
            LOWER(COALESCE(raw_category, '')) = 'library'
            OR LOWER(COALESCE(raw_subcategory, '')) LIKE '%library%'
          )
    """
    params: list[Any] = []
    if limit is not None:
        sql += " ORDER BY ABS(lon - ?) + ABS(lat - ?) LIMIT ?"
        params.extend([center[0], center[1], limit])
    return _query_rows(db_path, sql, params)


def _fetch_neighbourhood_aggregates(db_path: Path | str) -> list[dict[str, Any]]:
    _require_table(db_path, "property_locations_prod")
    sql = """
        SELECT
            neighbourhood,
            AVG(assessment_value) AS average_assessment,
            COUNT(*) AS property_count,
            AVG(lat) AS centroid_lat,
            AVG(lon) AS centroid_lon
        FROM property_locations_prod
        WHERE neighbourhood IS NOT NULL
          AND TRIM(neighbourhood) <> ''
          AND assessment_value IS NOT NULL
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        GROUP BY neighbourhood
    """
    return _query_rows(db_path, sql, [])


def _query_rows(db_path: Path | str, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    conn = connect(Path(db_path))
    try:
        try:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        except sqlite3.OperationalError as exc:
            raise RuntimeError(f"query failed for database '{db_path}': {exc}") from exc
    finally:
        conn.close()


@lru_cache(maxsize=32)
def _table_exists(db_path: str, table_name: str) -> bool:
    conn = connect(Path(db_path))
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _require_table(db_path: Path | str, table_name: str) -> None:
    resolved_db_path = str(Path(db_path).resolve())
    if _table_exists(resolved_db_path, table_name):
        return
    raise RuntimeError(
        f"required table '{table_name}' was not found in database '{db_path}'. "
        "Run the ingestion/refinement workflow that materializes this table before calling this helper."
    )


def _rank_rows(
    rows: list[dict[str, Any]],
    center: Point,
    limit: int | None,
    mode: DistanceMode,
    db_path: Path | str,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    if mode == "road":
        road_graph = _load_road_graph(Path(db_path))
        best_from_origin = _road_distances_from_origin(center, road_graph)
        ranked: list[dict[str, Any]] = []
        for row in rows:
            target = (float(row["lon"]), float(row["lat"]))
            try:
                distance_m = _road_distance_to_target(target, road_graph, best_from_origin)
            except RoadNetworkError:
                continue
            enriched = dict(row)
            enriched["distance_m"] = distance_m
            enriched["distance_mode"] = mode
            ranked.append(enriched)
    else:
        ranked = []
        for row in rows:
            target = (float(row["lon"]), float(row["lat"]))
            enriched = dict(row)
            enriched["distance_m"] = _manhattan_distance_m(center, target)
            enriched["distance_mode"] = mode
            ranked.append(enriched)

    if mode == "road" and not ranked:
        raise RoadNetworkError("could not route to any matching rows on the current road graph")

    ranked.sort(
        key=lambda item: (
            item["distance_m"],
            str(item.get("canonical_location_id") or item.get("entity_id") or item.get("name") or ""),
        )
    )
    return ranked[:limit] if limit is not None else ranked


def _normalize_comparable_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in (
        "year_built",
        "lot_size",
        "total_gross_area",
        "bedrooms",
        "bathrooms",
        "garage",
        "tax_class",
        "assessment_class_1",
        "assessment_class_2",
        "assessment_class_3",
        "zoning",
    ):
        if key not in attributes:
            continue
        value = attributes[key]
        if key in {"year_built", "lot_size", "total_gross_area", "bedrooms", "bathrooms"}:
            if value in (None, ""):
                continue
            normalized[key] = float(value)
        else:
            text = str(value).strip()
            if text:
                normalized[key] = text.upper()
    return normalized


def _matches_comparable_attributes(
    candidate: dict[str, Any],
    normalized_attributes: dict[str, Any],
) -> bool:
    if not normalized_attributes:
        return False

    for key, expected in normalized_attributes.items():
        actual = candidate.get(key)
        if key == "year_built":
            if actual is None:
                return False
            if abs(float(actual) - float(expected)) > 5:
                return False
        elif key == "bedrooms":
            if actual in (None, ""):
                return False
            if abs(float(actual) - float(expected)) > 1.0:
                return False
        elif key == "bathrooms":
            if actual in (None, ""):
                return False
            if abs(float(actual) - float(expected)) > 0.5:
                return False
        elif key in {"lot_size", "total_gross_area"}:
            if actual in (None, ""):
                return False
            actual_value = float(actual)
            lower_bound = float(expected) * 0.8
            upper_bound = float(expected) * 1.2
            if not lower_bound <= actual_value <= upper_bound:
                return False
        else:
            actual_text = str(actual or "").strip().upper()
            if actual_text != expected:
                return False
    return True


def _validate_point(point: Point) -> Point:
    if len(point) != 2:
        raise ValueError("point must contain exactly two values: (lon, lat)")
    lon = float(point[0])
    lat = float(point[1])
    if not -180.0 <= lon <= 180.0:
        raise ValueError("longitude must be between -180 and 180")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("latitude must be between -90 and 90")
    return lon, lat


def _validate_limit(limit: int | None) -> int:
    if limit is None:
        raise ValueError("limit cannot be None for this operation")
    resolved = int(limit)
    if resolved <= 0:
        raise ValueError("limit must be greater than zero")
    return resolved


def _normalize_distance_mode(distance_mode: str) -> DistanceMode:
    normalized = distance_mode.strip().lower().replace("-", "_")
    aliases = {
        "manhattan": "manhattan",
        "straight_line": "manhattan",
        "road": "road",
        "road_network": "road",
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError("distance_mode must be one of: manhattan, straight_line, road") from exc


def _candidate_limit(limit: int) -> int:
    return max(limit * ROAD_MODE_CANDIDATE_MULTIPLIER, ROAD_MODE_MIN_CANDIDATES)


def _manhattan_distance_m(a: Point, b: Point) -> float:
    lon_a, lat_a = a
    lon_b, lat_b = b
    return _geodesic_distance_m((lon_a, lat_a), (lon_b, lat_a)) + _geodesic_distance_m((lon_b, lat_a), (lon_b, lat_b))


def _geodesic_distance_m(a: Point, b: Point) -> float:
    lon_a, lat_a = map(math.radians, a)
    lon_b, lat_b = map(math.radians, b)
    dlon = lon_b - lon_a
    dlat = lat_b - lat_a
    hav = math.sin(dlat / 2.0) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(dlon / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_M * math.asin(math.sqrt(hav))


@lru_cache(maxsize=2)
def _load_road_graph(db_path: Path) -> dict[str, Any]:
    _require_table(db_path, "road_segments_prod")
    conn = connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT geometry_json, start_lon, start_lat, end_lon, end_lat, length_m
            FROM road_segments_prod
            WHERE start_lon IS NOT NULL
              AND start_lat IS NOT NULL
              AND end_lon IS NOT NULL
              AND end_lat IS NOT NULL
            """,
        ).fetchall()
    finally:
        conn.close()

    adjacency: dict[Point, list[tuple[Point, float]]] = defaultdict(list)
    polylines: list[list[Point]] = []
    segments: list[tuple[Point, Point]] = []
    segment_grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    if not rows:
        raise RoadNetworkError(f"no road segments found in {db_path}")

    for row in rows:
        points = _parse_geometry_points(row["geometry_json"])
        if len(points) < 2:
            start = (float(row["start_lon"]), float(row["start_lat"]))
            end = (float(row["end_lon"]), float(row["end_lat"]))
            points = [start, end]
        points = [_normalize_node(point) for point in points]

        polylines.append(points)
        for start, end in zip(points, points[1:]):
            weight = _geodesic_distance_m(start, end)
            adjacency[start].append((end, weight))
            adjacency[end].append((start, weight))
            segment_index = len(segments)
            segments.append((start, end))
            cell = _road_grid_cell(
                ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0),
            )
            segment_grid[cell].append(segment_index)

    return {
        "adjacency": dict(adjacency),
        "polylines": polylines,
        "segments": segments,
        "segment_grid": dict(segment_grid),
    }


def _parse_geometry_points(geometry_json: str) -> list[Point]:
    try:
        raw_points = json.loads(geometry_json)
    except json.JSONDecodeError:
        return []

    points: list[Point] = []
    for raw_point in raw_points:
        if not isinstance(raw_point, (list, tuple)) or len(raw_point) < 2:
            continue
        points.append((float(raw_point[0]), float(raw_point[1])))
    return points


def _normalize_node(point: Point) -> Point:
    return (round(point[0], ROAD_NODE_PRECISION), round(point[1], ROAD_NODE_PRECISION))


def _road_grid_cell(point: Point) -> tuple[int, int]:
    return (
        math.floor(point[0] / ROAD_GRID_SIZE_DEGREES),
        math.floor(point[1] / ROAD_GRID_SIZE_DEGREES),
    )


def _road_distances_from_origin(origin: Point, road_graph: dict[str, Any]) -> dict[Point, float]:
    adjacency: dict[Point, list[tuple[Point, float]]] = road_graph["adjacency"]
    if not adjacency:
        raise RoadNetworkError("road graph is empty")

    origin_attachments = _snap_point_to_network(origin, road_graph)

    initial_distances: dict[Point, float] = {}
    for node, offset in origin_attachments:
        initial_distances[node] = min(initial_distances.get(node, math.inf), offset)

    queue: list[tuple[float, Point]] = [(distance, node) for node, distance in initial_distances.items()]
    heapq.heapify(queue)
    best = dict(initial_distances)

    while queue:
        current_distance, node = heapq.heappop(queue)
        if current_distance > best.get(node, math.inf):
            continue
        for neighbor, weight in adjacency.get(node, []):
            candidate = current_distance + weight
            if candidate < best.get(neighbor, math.inf):
                best[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))

    return best


def _road_distance_to_target(
    destination: Point,
    road_graph: dict[str, Any],
    best_from_origin: dict[Point, float],
) -> float:
    destination_attachments = _snap_point_to_network(destination, road_graph)
    answer = math.inf
    for node, offset in destination_attachments:
        answer = min(answer, best_from_origin.get(node, math.inf) + offset)

    if math.isinf(answer):
        raise RoadNetworkError("could not route between the requested points on the road graph")
    return answer


def _snap_point_to_network(point: Point, road_graph: dict[str, Any]) -> list[tuple[Point, float]]:
    segments = road_graph["segments"]
    segment_grid = road_graph["segment_grid"]
    candidate_segments = _candidate_segments_for_point(point, segments, segment_grid)
    best: tuple[list[tuple[Point, float]], float] | None = None
    for start, end in candidate_segments:
        attachments, total_offset = _segment_attachments(point, start, end)
        if best is None or total_offset < best[1]:
            best = (attachments, total_offset)

    if best is None:
        raise RoadNetworkError("could not snap point to road network")
    return best[0]


def _candidate_segments_for_point(
    point: Point,
    segments: list[tuple[Point, Point]],
    segment_grid: dict[tuple[int, int], list[int]],
) -> list[tuple[Point, Point]]:
    origin_cell = _road_grid_cell(point)
    seen: set[int] = set()
    candidates: list[tuple[Point, Point]] = []

    for radius in range(ROAD_GRID_SEARCH_STEPS + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cell = (origin_cell[0] + dx, origin_cell[1] + dy)
                for segment_index in segment_grid.get(cell, []):
                    if segment_index in seen:
                        continue
                    seen.add(segment_index)
                    candidates.append(segments[segment_index])
        if candidates:
            return candidates

    return segments


def _segment_attachments(point: Point, start: Point, end: Point) -> tuple[list[tuple[Point, float]], float]:
    px, py = _project_local_xy(point, point)
    ax, ay = _project_local_xy(start, point)
    bx, by = _project_local_xy(end, point)
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy

    if length_sq == 0.0:
        offset = math.hypot(px - ax, py - ay)
        return ([(start, offset)], offset)

    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = min(1.0, max(0.0, t))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    off_road = math.hypot(px - proj_x, py - proj_y)

    if t <= 0.0:
        return ([(start, off_road)], off_road)
    if t >= 1.0:
        return ([(end, off_road)], off_road)

    segment_length = _geodesic_distance_m(start, end)
    return (
        [
            (start, off_road + (t * segment_length)),
            (end, off_road + ((1.0 - t) * segment_length)),
        ],
        off_road,
    )


def _project_local_xy(point: Point, origin: Point) -> tuple[float, float]:
    lon, lat = point
    origin_lon, origin_lat = origin
    lat_scale = math.radians(lat - origin_lat) * EARTH_RADIUS_M
    lon_scale = (
        math.radians(lon - origin_lon)
        * EARTH_RADIUS_M
        * math.cos(math.radians((lat + origin_lat) / 2.0))
    )
    return lon_scale, lat_scale
