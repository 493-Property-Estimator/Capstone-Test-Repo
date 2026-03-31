from __future__ import annotations

import heapq
import json
import math
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.data_sourcing.database import connect as connect_db
from src.data_sourcing.database import init_db as init_open_data_db
from src.estimator.property_estimator import PropertyEstimator
from src.estimator.simple_estimator import summarize_property_cluster


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a_value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c_value = 2 * math.atan2(math.sqrt(a_value), math.sqrt(1 - a_value))
    return earth_radius_m * c_value


def round_coord(value: float) -> float:
    return round(float(value), 6)


def make_node_key(lat: float, lon: float) -> str:
    return f"{round_coord(lat):.6f},{round_coord(lon):.6f}"


def safe_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def safe_json_loads(raw_value: object, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        return json.loads(str(raw_value))
    except json.JSONDecodeError:
        return fallback


def merge_json_objects(existing_raw: object, new_raw: object) -> str:
    existing = safe_json_loads(existing_raw, {})
    new_value = safe_json_loads(new_raw, {})
    if not isinstance(existing, dict):
        existing = {}
    if not isinstance(new_value, dict):
        new_value = {}

    merged = dict(existing)
    for key, value in new_value.items():
        if key == "sources" and isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged_sources = dict(merged[key])
            merged_sources.update(value)
            merged[key] = merged_sources
        elif key not in merged or merged[key] in (None, "", [], {}):
            merged[key] = value
    return json.dumps(merged, sort_keys=True)


def extract_property_bed_bath(row: sqlite3.Row) -> tuple[float | None, float | None]:
    raw_record = safe_json_loads(row["raw_record_json"], {})
    if not isinstance(raw_record, dict):
        raw_record = {}

    bed_value = None
    bath_value = None
    for field_name in (
        "beds",
        "bedrooms",
        "bedroom_count",
        "number_of_bedrooms",
        "Beds",
        "Bedrooms",
    ):
        if field_name in raw_record and raw_record[field_name] not in (None, ""):
            bed_value = safe_float(raw_record[field_name])
            break

    for field_name in (
        "baths",
        "bathrooms",
        "bathroom_count",
        "number_of_bathrooms",
        "Baths",
        "Bathrooms",
    ):
        if field_name in raw_record and raw_record[field_name] not in (None, ""):
            bath_value = safe_float(raw_record[field_name])
            break

    return bed_value, bath_value


@dataclass
class RoadSnap:
    node_key: str
    lat: float
    lon: float
    access_distance_m: float


@dataclass(frozen=True)
class TransitStop:
    stop_id: str
    name: str
    lat: float
    lon: float
    code: str | None
    description: str | None


@dataclass(frozen=True)
class TransitEdge:
    from_stop_id: str
    to_stop_id: str
    route_id: str
    trip_id: str
    headsign: str | None
    distance_m: float
    stop_count: int


class RoadGraph:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._loaded = False
        self._adjacency: dict[str, list[tuple[str, float]]] = {}
        self._node_coords: dict[str, tuple[float, float]] = {}

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def ensure_loaded(self) -> None:
        if self._loaded:
            return

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT start_lat, start_lon, end_lat, end_lon, length_m
                FROM road_segments_prod
                WHERE start_lat IS NOT NULL
                  AND start_lon IS NOT NULL
                  AND end_lat IS NOT NULL
                  AND end_lon IS NOT NULL
                """
            )

            for row in rows:
                start_lat = float(row["start_lat"])
                start_lon = float(row["start_lon"])
                end_lat = float(row["end_lat"])
                end_lon = float(row["end_lon"])
                distance_m = (
                    float(row["length_m"])
                    if row["length_m"] is not None
                    else haversine_meters(start_lat, start_lon, end_lat, end_lon)
                )

                start_key = make_node_key(start_lat, start_lon)
                end_key = make_node_key(end_lat, end_lon)
                self._node_coords.setdefault(
                    start_key, (round_coord(start_lat), round_coord(start_lon))
                )
                self._node_coords.setdefault(
                    end_key, (round_coord(end_lat), round_coord(end_lon))
                )
                self._adjacency.setdefault(start_key, []).append((end_key, distance_m))
                self._adjacency.setdefault(end_key, []).append((start_key, distance_m))

        self._loaded = True

    def snap_point(self, lat: float, lon: float) -> RoadSnap | None:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT start_lat, start_lon, end_lat, end_lon, center_lat, center_lon
                FROM road_segments_prod
                WHERE center_lat IS NOT NULL
                  AND center_lon IS NOT NULL
                ORDER BY
                  ((center_lat - ?) * (center_lat - ?))
                  + ((center_lon - ?) * (center_lon - ?))
                LIMIT 40
                """,
                (lat, lat, lon, lon),
            ).fetchall()

        best_snap: RoadSnap | None = None
        for row in rows:
            for endpoint_lat_key, endpoint_lon_key in (
                ("start_lat", "start_lon"),
                ("end_lat", "end_lon"),
            ):
                endpoint_lat = float(row[endpoint_lat_key])
                endpoint_lon = float(row[endpoint_lon_key])
                node_key = make_node_key(endpoint_lat, endpoint_lon)
                if node_key not in self._node_coords:
                    continue

                access_distance_m = haversine_meters(lat, lon, endpoint_lat, endpoint_lon)
                if best_snap is None or access_distance_m < best_snap.access_distance_m:
                    best_snap = RoadSnap(
                        node_key=node_key,
                        lat=self._node_coords[node_key][0],
                        lon=self._node_coords[node_key][1],
                        access_distance_m=access_distance_m,
                    )

        return best_snap

    def shortest_path_distance(self, start_key: str, end_key: str) -> float | None:
        if start_key == end_key:
            return 0.0

        distances = {start_key: 0.0}
        heap: list[tuple[float, str]] = [(0.0, start_key)]
        visited: set[str] = set()

        while heap:
            current_distance, node_key = heapq.heappop(heap)
            if node_key in visited:
                continue

            if node_key == end_key:
                return current_distance

            visited.add(node_key)
            for neighbor_key, edge_distance in self._adjacency.get(node_key, []):
                next_distance = current_distance + edge_distance
                if next_distance < distances.get(neighbor_key, math.inf):
                    distances[neighbor_key] = next_distance
                    heapq.heappush(heap, (next_distance, neighbor_key))

        return None

    def route_distance(
        self, start_lat: float, start_lon: float, end_lat: float, end_lon: float
    ) -> dict[str, Any]:
        self.ensure_loaded()

        start_snap = self.snap_point(start_lat, start_lon)
        end_snap = self.snap_point(end_lat, end_lon)
        straight_line_m = haversine_meters(start_lat, start_lon, end_lat, end_lon)

        if start_snap is None or end_snap is None:
            return {
                "straight_line_m": round(straight_line_m, 2),
                "road_distance_m": round(straight_line_m, 2),
                "routing_mode": "straight_line_fallback",
                "start_snap": None,
                "end_snap": None,
            }

        graph_distance = self.shortest_path_distance(start_snap.node_key, end_snap.node_key)
        if graph_distance is None:
            return {
                "straight_line_m": round(straight_line_m, 2),
                "road_distance_m": round(straight_line_m, 2),
                "routing_mode": "straight_line_fallback",
                "start_snap": self._snap_payload(start_snap),
                "end_snap": self._snap_payload(end_snap),
            }

        road_distance_m = (
            start_snap.access_distance_m + graph_distance + end_snap.access_distance_m
        )
        return {
            "straight_line_m": round(straight_line_m, 2),
            "road_distance_m": round(road_distance_m, 2),
            "routing_mode": "road_graph",
            "start_snap": self._snap_payload(start_snap),
            "end_snap": self._snap_payload(end_snap),
        }

    @staticmethod
    def _snap_payload(snap: RoadSnap) -> dict[str, Any]:
        return {
            "lat": snap.lat,
            "lon": snap.lon,
            "access_distance_m": round(snap.access_distance_m, 2),
        }


class TransitNetwork:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._loaded = False
        self._stops: dict[str, TransitStop] = {}
        self._routes: dict[str, dict[str, Any]] = {}
        self._adjacency: dict[str, list[TransitEdge]] = defaultdict(list)
        self._route_shapes: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._route_stop_ids: dict[str, set[str]] = defaultdict(set)
        self._stop_grid: dict[tuple[int, int], list[TransitStop]] = defaultdict(list)
        self._trip_count = 0

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _grid_cell(lat: float, lon: float, cell_size: float = 0.005) -> tuple[int, int]:
        return (int(math.floor(lat / cell_size)), int(math.floor(lon / cell_size)))

    @staticmethod
    def _parse_points(raw_geometry: object) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for point in safe_json_loads(raw_geometry, []):
            if not isinstance(point, list) or len(point) < 2:
                continue
            lon = safe_float(point[0])
            lat = safe_float(point[1])
            if lon is None or lat is None:
                continue
            points.append((lon, lat))
        return points

    def ensure_loaded(self) -> None:
        if self._loaded:
            return

        with self._connect() as connection:
            stop_rows = connection.execute(
                """
                SELECT stop_id, stop_name, stop_code, stop_desc, lat, lon
                FROM transit_prod
                WHERE transit_type='stops'
                  AND stop_id IS NOT NULL
                  AND lat IS NOT NULL
                  AND lon IS NOT NULL
                """
            ).fetchall()
            trip_rows = connection.execute(
                """
                SELECT route_id, trip_id, trip_headsign, direction_id, shape_id, geometry_json
                FROM transit_prod
                WHERE transit_type='trips'
                  AND route_id IS NOT NULL
                  AND trip_id IS NOT NULL
                """
            ).fetchall()

        for row in stop_rows:
            stop = TransitStop(
                stop_id=str(row["stop_id"]),
                name=safe_text(row["stop_name"]) or str(row["stop_id"]),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                code=safe_text(row["stop_code"]),
                description=safe_text(row["stop_desc"]),
            )
            self._stops[stop.stop_id] = stop
            self._stop_grid[self._grid_cell(stop.lat, stop.lon)].append(stop)

        edge_index: dict[tuple[str, str, str], TransitEdge] = {}
        route_shape_seen: set[tuple[str, str, str]] = set()

        for row in trip_rows:
            route_id = safe_text(row["route_id"])
            trip_id = safe_text(row["trip_id"])
            if route_id is None or trip_id is None:
                continue
            points = self._parse_points(row["geometry_json"])
            if len(points) < 2:
                continue

            self._trip_count += 1
            route_summary = self._routes.setdefault(
                route_id,
                {
                    "route_id": route_id,
                    "headsigns": set(),
                    "direction_ids": set(),
                    "trip_count": 0,
                    "shape_count": 0,
                },
            )
            route_summary["trip_count"] += 1
            if safe_text(row["trip_headsign"]):
                route_summary["headsigns"].add(safe_text(row["trip_headsign"]))
            if row["direction_id"] is not None:
                route_summary["direction_ids"].add(int(row["direction_id"]))

            shape_id = safe_text(row["shape_id"]) or trip_id
            shape_key = (route_id, shape_id, json.dumps(points))
            if shape_key not in route_shape_seen:
                route_shape_seen.add(shape_key)
                route_summary["shape_count"] += 1
                self._route_shapes[route_id].append(
                    {
                        "shape_id": shape_id,
                        "trip_id": trip_id,
                        "direction_id": row["direction_id"],
                        "trip_headsign": safe_text(row["trip_headsign"]),
                        "points": [[lon, lat] for lon, lat in points],
                    }
                )

            matched_stops = self._match_stops_to_trip(points)
            if len(matched_stops) < 2:
                continue
            for match_index in range(len(matched_stops) - 1):
                current_stop = matched_stops[match_index]
                next_stop = matched_stops[match_index + 1]
                if current_stop["stop_id"] == next_stop["stop_id"]:
                    continue
                edge_distance = max(next_stop["progress_m"] - current_stop["progress_m"], 1.0)
                edge = TransitEdge(
                    from_stop_id=current_stop["stop_id"],
                    to_stop_id=next_stop["stop_id"],
                    route_id=route_id,
                    trip_id=trip_id,
                    headsign=safe_text(row["trip_headsign"]),
                    distance_m=edge_distance,
                    stop_count=1,
                )
                key = (edge.from_stop_id, edge.to_stop_id, edge.route_id)
                existing = edge_index.get(key)
                if existing is None or edge.distance_m < existing.distance_m:
                    edge_index[key] = edge
                self._route_stop_ids[route_id].add(edge.from_stop_id)
                self._route_stop_ids[route_id].add(edge.to_stop_id)

        for edge in edge_index.values():
            self._adjacency[edge.from_stop_id].append(edge)

        for route_id, summary in self._routes.items():
            summary["headsigns"] = sorted(summary["headsigns"])
            summary["direction_ids"] = sorted(summary["direction_ids"])
            summary["stop_count"] = len(self._route_stop_ids.get(route_id, set()))

        self._loaded = True

    def has_data(self) -> bool:
        self.ensure_loaded()
        return bool(self._stops) and bool(self._routes)

    def _match_stops_to_trip(self, points: list[tuple[float, float]]) -> list[dict[str, Any]]:
        threshold_m = 90.0
        min_lon = min(point[0] for point in points) - 0.003
        max_lon = max(point[0] for point in points) + 0.003
        min_lat = min(point[1] for point in points) - 0.003
        max_lat = max(point[1] for point in points) + 0.003

        min_row, min_col = self._grid_cell(min_lat, min_lon)
        max_row, max_col = self._grid_cell(max_lat, max_lon)
        candidates: list[TransitStop] = []
        for row_index in range(min_row, max_row + 1):
            for col_index in range(min_col, max_col + 1):
                candidates.extend(self._stop_grid.get((row_index, col_index), []))

        matches: list[dict[str, Any]] = []
        seen_stop_ids: set[str] = set()
        for stop in candidates:
            distance_m, progress_m = self._distance_to_polyline(stop.lat, stop.lon, points)
            if distance_m > threshold_m:
                continue
            if stop.stop_id in seen_stop_ids:
                continue
            seen_stop_ids.add(stop.stop_id)
            matches.append(
                {
                    "stop_id": stop.stop_id,
                    "progress_m": progress_m,
                    "distance_m": distance_m,
                }
            )
        matches.sort(key=lambda item: (item["progress_m"], item["distance_m"], item["stop_id"]))
        return matches

    @staticmethod
    def _distance_to_polyline(
        point_lat: float,
        point_lon: float,
        polyline: list[tuple[float, float]],
    ) -> tuple[float, float]:
        best_distance_m = math.inf
        best_progress_m = 0.0
        traversed_m = 0.0
        for index in range(len(polyline) - 1):
            start_lon, start_lat = polyline[index]
            end_lon, end_lat = polyline[index + 1]
            segment_length_m = haversine_meters(start_lat, start_lon, end_lat, end_lon)
            if segment_length_m <= 0:
                continue
            dx = end_lon - start_lon
            dy = end_lat - start_lat
            px = point_lon - start_lon
            py = point_lat - start_lat
            denominator = (dx * dx) + (dy * dy)
            t_value = 0.0 if denominator == 0 else max(0.0, min(1.0, ((px * dx) + (py * dy)) / denominator))
            proj_lon = start_lon + (t_value * dx)
            proj_lat = start_lat + (t_value * dy)
            distance_m = haversine_meters(point_lat, point_lon, proj_lat, proj_lon)
            progress_m = traversed_m + (segment_length_m * t_value)
            if distance_m < best_distance_m:
                best_distance_m = distance_m
                best_progress_m = progress_m
            traversed_m += segment_length_m
        return best_distance_m, best_progress_m

    def list_routes(self) -> list[dict[str, Any]]:
        self.ensure_loaded()
        return sorted(self._routes.values(), key=lambda row: row["route_id"])

    def get_stops(self, route_id: str | None = None) -> list[dict[str, Any]]:
        self.ensure_loaded()
        if route_id:
            allowed_ids = self._route_stop_ids.get(route_id, set())
            stops = [self._stops[stop_id] for stop_id in sorted(allowed_ids) if stop_id in self._stops]
        else:
            stops = list(self._stops.values())

        return [
            {
                "stop_id": stop.stop_id,
                "name": stop.name,
                "code": stop.code,
                "description": stop.description,
                "lat": stop.lat,
                "lon": stop.lon,
            }
            for stop in sorted(stops, key=lambda item: (item.name, item.stop_id))
        ]

    def get_route_details(self, route_id: str) -> dict[str, Any]:
        self.ensure_loaded()
        summary = self._routes.get(route_id)
        if not summary:
            raise ValueError("Transit route not found.")
        return {
            **summary,
            "stops": self.get_stops(route_id=route_id),
            "shapes": self._route_shapes.get(route_id, []),
        }

    def _nearest_stops(self, lat: float, lon: float, limit: int = 8, max_distance_m: float = 1_000.0) -> list[dict[str, Any]]:
        self.ensure_loaded()
        candidates = [
            {
                "stop_id": stop.stop_id,
                "name": stop.name,
                "lat": stop.lat,
                "lon": stop.lon,
                "walk_distance_m": haversine_meters(lat, lon, stop.lat, stop.lon),
            }
            for stop in self._stops.values()
        ]
        candidates = [item for item in candidates if item["walk_distance_m"] <= max_distance_m]
        candidates.sort(key=lambda item: (item["walk_distance_m"], item["stop_id"]))
        return candidates[:limit]

    def plan_journey(
        self,
        origin: dict[str, Any],
        destination: dict[str, Any],
    ) -> dict[str, Any]:
        self.ensure_loaded()
        if not self._stops or not self._adjacency:
            raise ValueError("Transit data is not available in the database yet.")

        start_stops = self._nearest_stops(origin["lat"], origin["lon"])
        end_stops = self._nearest_stops(destination["lat"], destination["lon"])
        if not start_stops or not end_stops:
            raise ValueError("No nearby transit stops were found for one or both endpoints.")

        end_walk_lookup = {item["stop_id"]: item for item in end_stops}
        counter = 0
        heap: list[tuple[int, float, int, str, str | None, bool]] = []
        best_cost: dict[tuple[str, str | None, bool], tuple[int, float]] = {}
        previous: dict[tuple[str, str | None, bool], tuple[tuple[str, str | None, bool] | None, dict[str, Any] | None]] = {}

        for stop in start_stops:
            state_key = (stop["stop_id"], None, False)
            cost = (0, float(stop["walk_distance_m"]))
            best_cost[state_key] = cost
            previous[state_key] = (
                None,
                {
                    "mode": "walk",
                    "from": {"label": origin["label"], "lat": origin["lat"], "lon": origin["lon"]},
                    "to": {"label": stop["name"], "lat": stop["lat"], "lon": stop["lon"], "stop_id": stop["stop_id"]},
                    "distance_m": round(stop["walk_distance_m"], 2),
                },
            )
            heapq.heappush(heap, (0, float(stop["walk_distance_m"]), counter, stop["stop_id"], None, False))
            counter += 1

        best_final: tuple[tuple[int, float], tuple[str, str | None, bool] | None, dict[str, Any] | None] = (
            (math.inf, math.inf),
            None,
            None,
        )

        while heap:
            transfer_count, total_distance_m, _, stop_id, current_route, boarded = heapq.heappop(heap)
            state_key = (stop_id, current_route, boarded)
            if best_cost.get(state_key) != (transfer_count, total_distance_m):
                continue

            end_stop = end_walk_lookup.get(stop_id)
            if boarded and end_stop:
                candidate_cost = (transfer_count, total_distance_m + float(end_stop["walk_distance_m"]))
                if candidate_cost < best_final[0]:
                    best_final = (
                        candidate_cost,
                        state_key,
                        {
                            "mode": "walk",
                            "from": {"label": end_stop["name"], "lat": end_stop["lat"], "lon": end_stop["lon"], "stop_id": stop_id},
                            "to": {"label": destination["label"], "lat": destination["lat"], "lon": destination["lon"]},
                            "distance_m": round(float(end_stop["walk_distance_m"]), 2),
                        },
                    )

            for edge in self._adjacency.get(stop_id, []):
                next_transfer_count = transfer_count
                if boarded and current_route and edge.route_id != current_route:
                    next_transfer_count += 1
                next_total_distance_m = total_distance_m + edge.distance_m
                next_state_key = (edge.to_stop_id, edge.route_id, True)
                next_cost = (next_transfer_count, next_total_distance_m)
                if next_cost >= best_cost.get(next_state_key, (math.inf, math.inf)):
                    continue
                best_cost[next_state_key] = next_cost
                previous[next_state_key] = (
                    state_key,
                    {
                        "mode": "transit",
                        "route_id": edge.route_id,
                        "trip_id": edge.trip_id,
                        "headsign": edge.headsign,
                        "from_stop_id": edge.from_stop_id,
                        "to_stop_id": edge.to_stop_id,
                        "from_stop_name": self._stops[edge.from_stop_id].name,
                        "to_stop_name": self._stops[edge.to_stop_id].name,
                        "from_lat": self._stops[edge.from_stop_id].lat,
                        "from_lon": self._stops[edge.from_stop_id].lon,
                        "to_lat": self._stops[edge.to_stop_id].lat,
                        "to_lon": self._stops[edge.to_stop_id].lon,
                        "distance_m": round(edge.distance_m, 2),
                    },
                )
                heapq.heappush(
                    heap,
                    (next_transfer_count, next_total_distance_m, counter, edge.to_stop_id, edge.route_id, True),
                )
                counter += 1

        if best_final[1] is None:
            raise ValueError("No connected transit path was found between the selected endpoints.")

        path_steps: list[dict[str, Any]] = []
        current_state = best_final[1]
        while current_state is not None:
            previous_state, step = previous[current_state]
            if step is not None:
                path_steps.append(step)
            current_state = previous_state
        path_steps.reverse()
        path_steps.append(best_final[2])

        grouped_legs: list[dict[str, Any]] = []
        routes_used: list[str] = []
        for step in path_steps:
            if step["mode"] == "walk":
                grouped_legs.append(step)
                continue
            if grouped_legs and grouped_legs[-1]["mode"] == "transit" and grouped_legs[-1]["route_id"] == step["route_id"]:
                grouped_legs[-1]["to_stop_id"] = step["to_stop_id"]
                grouped_legs[-1]["to_stop_name"] = step["to_stop_name"]
                grouped_legs[-1]["distance_m"] = round(grouped_legs[-1]["distance_m"] + step["distance_m"], 2)
                grouped_legs[-1]["segment_count"] += 1
            else:
                grouped_legs.append({**step, "segment_count": 1})
            if step["route_id"] not in routes_used:
                routes_used.append(step["route_id"])

        walking_distance_m = round(
            sum(step["distance_m"] for step in grouped_legs if step["mode"] == "walk"),
            2,
        )
        transit_distance_m = round(
            sum(step["distance_m"] for step in grouped_legs if step["mode"] == "transit"),
            2,
        )

        return {
            "origin": origin,
            "destination": destination,
            "summary": {
                "transfer_count": max(len(routes_used) - 1, 0),
                "route_count": len(routes_used),
                "routes_used": routes_used,
                "walking_distance_m": walking_distance_m,
                "transit_distance_m": transit_distance_m,
                "total_distance_m": round(walking_distance_m + transit_distance_m, 2),
            },
            "nearby_origin_stops": start_stops,
            "nearby_destination_stops": end_stops,
            "legs": grouped_legs,
        }

class OsrmError(RuntimeError):
    """Raised when the configured OSRM service cannot satisfy a request."""


class OsrmService:
    PROFILE_ENV_MAP = {
        "driving": "TESTING_STAGE_OSRM_PROFILE_DRIVING",
        "walking": "TESTING_STAGE_OSRM_PROFILE_WALKING",
        "biking": "TESTING_STAGE_OSRM_PROFILE_BIKING",
    }

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        configured_base = base_url or os.getenv("TESTING_STAGE_OSRM_BASE_URL", "").strip()
        self._base_url = configured_base.rstrip("/")
        self._timeout_seconds = float(
            timeout_seconds
            if timeout_seconds is not None
            else os.getenv("TESTING_STAGE_OSRM_TIMEOUT_SECONDS", "5")
        )

    def is_configured(self) -> bool:
        return bool(self._base_url)

    def resolve_profile(self, profile: str) -> str:
        normalized = profile.strip().lower()
        if normalized not in self.PROFILE_ENV_MAP:
            raise ValueError("Profile must be one of driving, walking, or biking.")
        return os.getenv(self.PROFILE_ENV_MAP[normalized], normalized).strip() or normalized

    def nearest(self, lat: float, lon: float, profile: str) -> dict[str, Any]:
        resolved_profile = self.resolve_profile(profile)
        payload = self._request(
            service="nearest",
            profile=resolved_profile,
            coordinates=[(lat, lon)],
            query={"number": "1"},
        )
        waypoints = payload.get("waypoints") or []
        if not waypoints:
            raise OsrmError("OSRM nearest returned no waypoints.")
        waypoint = waypoints[0]
        location = waypoint.get("location") or [None, None]
        return {
            "profile": profile,
            "resolved_profile": resolved_profile,
            "input_point": {"lat": lat, "lon": lon},
            "waypoint": {
                "name": waypoint.get("name"),
                "distance_m": round(float(waypoint.get("distance") or 0.0), 2),
                "lon": round_coord(float(location[0])),
                "lat": round_coord(float(location[1])),
                "hint": waypoint.get("hint"),
            },
        }

    def route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        profile: str,
    ) -> dict[str, Any]:
        resolved_profile = self.resolve_profile(profile)
        payload = self._request(
            service="route",
            profile=resolved_profile,
            coordinates=[(start_lat, start_lon), (end_lat, end_lon)],
            query={
                "alternatives": "false",
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
        )
        routes = payload.get("routes") or []
        waypoints = payload.get("waypoints") or []
        if not routes:
            raise OsrmError("OSRM route returned no routes.")

        route = routes[0]
        return {
            "profile": profile,
            "resolved_profile": resolved_profile,
            "start_point": {"lat": start_lat, "lon": start_lon},
            "end_point": {"lat": end_lat, "lon": end_lon},
            "distance_m": round(float(route.get("distance") or 0.0), 2),
            "duration_s": round(float(route.get("duration") or 0.0), 2),
            "duration_min": round(float(route.get("duration") or 0.0) / 60.0, 2),
            "geometry": route.get("geometry"),
            "start_waypoint": self._waypoint_payload(waypoints, 0),
            "end_waypoint": self._waypoint_payload(waypoints, 1),
        }

    def matrix(self, points: list[dict[str, float]], profile: str) -> dict[str, Any]:
        if len(points) < 2:
            raise ValueError("At least two points are required for the OSRM matrix.")

        resolved_profile = self.resolve_profile(profile)
        coordinates = [(point["lat"], point["lon"]) for point in points]
        payload = self._request(
            service="table",
            profile=resolved_profile,
            coordinates=coordinates,
            query={"annotations": "distance,duration"},
        )
        return {
            "profile": profile,
            "resolved_profile": resolved_profile,
            "points": points,
            "durations_s": self._rounded_matrix(payload.get("durations")),
            "distances_m": self._rounded_matrix(payload.get("distances")),
            "sources": [self._matrix_waypoint_payload(item) for item in payload.get("sources") or []],
            "destinations": [
                self._matrix_waypoint_payload(item) for item in payload.get("destinations") or []
            ],
        }

    def _request(
        self,
        service: str,
        profile: str,
        coordinates: list[tuple[float, float]],
        query: dict[str, str],
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise OsrmError(
                "OSRM is not configured. Set TESTING_STAGE_OSRM_BASE_URL to your local OSRM server."
            )

        coordinate_path = ";".join(
            f"{round_coord(lon)},{round_coord(lat)}" for lat, lon in coordinates
        )
        query_string = urllib.parse.urlencode(query)
        url = f"{self._base_url}/{service}/v1/{profile}/{coordinate_path}?{query_string}"

        try:
            with urllib.request.urlopen(url, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise OsrmError(
                f"OSRM {service} failed with HTTP {error.code}: {body or error.reason}"
            ) from error
        except urllib.error.URLError as error:
            raise OsrmError(
                f"OSRM {service} request failed: {error.reason}. "
                "Check TESTING_STAGE_OSRM_BASE_URL and that the OSRM server is running."
            ) from error

        if payload.get("code") not in {None, "Ok"}:
            raise OsrmError(
                f"OSRM {service} error: {payload.get('message') or payload.get('code')}"
            )
        return payload

    @staticmethod
    def _waypoint_payload(waypoints: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
        if index >= len(waypoints):
            return None
        waypoint = waypoints[index]
        location = waypoint.get("location") or [None, None]
        return {
            "name": waypoint.get("name"),
            "distance_m": round(float(waypoint.get("distance") or 0.0), 2),
            "lon": round_coord(float(location[0])),
            "lat": round_coord(float(location[1])),
        }

    @staticmethod
    def _matrix_waypoint_payload(waypoint: dict[str, Any]) -> dict[str, Any]:
        location = waypoint.get("location") or [None, None]
        return {
            "name": waypoint.get("name"),
            "distance_m": round(float(waypoint.get("distance") or 0.0), 2),
            "lon": round_coord(float(location[0])),
            "lat": round_coord(float(location[1])),
        }

    @staticmethod
    def _rounded_matrix(matrix: object) -> list[list[float | None]] | None:
        if matrix is None:
            return None
        rows: list[list[float | None]] = []
        for row in matrix:
            rows.append(
                [round(float(value), 2) if value is not None else None for value in row]
            )
        return rows


class CrimeProvider:
    def summary_by_neighbourhood(self, neighbourhood: str) -> dict[str, Any]:
        raise NotImplementedError

    def summary_by_point(self, lat: float, lon: float, radius_m: float) -> dict[str, Any]:
        raise NotImplementedError


class UnavailableCrimeProvider(CrimeProvider):
    def summary_by_neighbourhood(self, neighbourhood: str) -> dict[str, Any]:
        return {
            "available": False,
            "summary_scope": "neighbourhood",
            "neighbourhood": neighbourhood,
            "message": "Crime summary data is not available in the current repository database.",
            "todo": "Add a crime ingest source/provider and populate a crime summary table.",
            "crime_types": [],
            "total_incidents": None,
        }

    def summary_by_point(self, lat: float, lon: float, radius_m: float) -> dict[str, Any]:
        return {
            "available": False,
            "summary_scope": "point",
            "query_point": {"lat": lat, "lon": lon},
            "radius_m": radius_m,
            "message": "Crime summary data is not available in the current repository database.",
            "todo": "Add a crime ingest source/provider and populate a crime summary table.",
            "crime_types": [],
            "total_incidents": None,
        }


class SQLiteCrimeProvider(CrimeProvider):
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._mode = self._detect_mode()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def is_available(self) -> bool:
        return self._mode is not None

    def _detect_mode(self) -> str | None:
        with self._connect() as connection:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "crime_summary_prod" in tables:
                row = connection.execute(
                    "SELECT COUNT(*) AS row_count FROM crime_summary_prod"
                ).fetchone()
                if int(row["row_count"] or 0) > 0:
                    return "summary"
            if "crime_incidents_prod" in tables:
                row = connection.execute(
                    "SELECT COUNT(*) AS row_count FROM crime_incidents_prod"
                ).fetchone()
                if int(row["row_count"] or 0) > 0:
                    return "incidents"
        return None

    def summary_by_neighbourhood(self, neighbourhood: str) -> dict[str, Any]:
        if self._mode == "summary":
            return self._summary_table_by_neighbourhood(neighbourhood)
        if self._mode == "incidents":
            return self._incident_table_by_neighbourhood(neighbourhood)
        return UnavailableCrimeProvider().summary_by_neighbourhood(neighbourhood)

    def summary_by_point(self, lat: float, lon: float, radius_m: float) -> dict[str, Any]:
        if self._mode == "incidents":
            return self._incident_table_by_point(lat, lon, radius_m)
        return UnavailableCrimeProvider().summary_by_point(lat, lon, radius_m)

    def _summary_table_by_neighbourhood(self, neighbourhood: str) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT crime_type, incident_count
                FROM crime_summary_prod
                WHERE neighbourhood = ?
                ORDER BY incident_count DESC, crime_type
                """,
                (neighbourhood,),
            ).fetchall()

        crime_types = [
            {"crime_type": row["crime_type"], "count": int(row["incident_count"] or 0)}
            for row in rows
        ]
        return {
            "available": True,
            "summary_scope": "neighbourhood",
            "neighbourhood": neighbourhood,
            "crime_types": crime_types,
            "total_incidents": sum(item["count"] for item in crime_types),
        }

    def _incident_table_by_neighbourhood(self, neighbourhood: str) -> dict[str, Any]:
        with self._connect() as connection:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(crime_incidents_prod)").fetchall()
            }
            neighbourhood_field = (
                "neighbourhood"
                if "neighbourhood" in columns
                else "neighbourhood_name"
                if "neighbourhood_name" in columns
                else None
            )
            crime_type_field = (
                "crime_type"
                if "crime_type" in columns
                else "offense_type"
                if "offense_type" in columns
                else "offence_type"
                if "offence_type" in columns
                else None
            )
            if not neighbourhood_field or not crime_type_field:
                return UnavailableCrimeProvider().summary_by_neighbourhood(neighbourhood)

            rows = connection.execute(
                f"""
                SELECT {crime_type_field} AS crime_type, COUNT(*) AS incident_count
                FROM crime_incidents_prod
                WHERE {neighbourhood_field} = ?
                GROUP BY {crime_type_field}
                ORDER BY incident_count DESC, crime_type
                """,
                (neighbourhood,),
            ).fetchall()

        crime_types = [
            {"crime_type": row["crime_type"], "count": int(row["incident_count"] or 0)}
            for row in rows
        ]
        return {
            "available": True,
            "summary_scope": "neighbourhood",
            "neighbourhood": neighbourhood,
            "crime_types": crime_types,
            "total_incidents": sum(item["count"] for item in crime_types),
        }

    def _incident_table_by_point(self, lat: float, lon: float, radius_m: float) -> dict[str, Any]:
        with self._connect() as connection:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(crime_incidents_prod)").fetchall()
            }
            lat_field = "lat" if "lat" in columns else "latitude" if "latitude" in columns else None
            lon_field = "lon" if "lon" in columns else "longitude" if "longitude" in columns else None
            crime_type_field = (
                "crime_type"
                if "crime_type" in columns
                else "offense_type"
                if "offense_type" in columns
                else "offence_type"
                if "offence_type" in columns
                else None
            )
            if not lat_field or not lon_field or not crime_type_field:
                return UnavailableCrimeProvider().summary_by_point(lat, lon, radius_m)

            bounding_lat_delta = radius_m / 111_320.0
            bounding_lon_delta = radius_m / max(1.0, 111_320.0 * math.cos(math.radians(lat)))

            rows = connection.execute(
                f"""
                SELECT {lat_field} AS lat, {lon_field} AS lon, {crime_type_field} AS crime_type
                FROM crime_incidents_prod
                WHERE {lat_field} BETWEEN ? AND ?
                  AND {lon_field} BETWEEN ? AND ?
                """,
                (
                    lat - bounding_lat_delta,
                    lat + bounding_lat_delta,
                    lon - bounding_lon_delta,
                    lon + bounding_lon_delta,
                ),
            ).fetchall()

        counts: dict[str, int] = {}
        for row in rows:
            item_lat = float(row["lat"])
            item_lon = float(row["lon"])
            if haversine_meters(lat, lon, item_lat, item_lon) > radius_m:
                continue
            crime_type = row["crime_type"] or "Unknown"
            counts[crime_type] = counts.get(crime_type, 0) + 1

        crime_types = [
            {"crime_type": crime_type, "count": count}
            for crime_type, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "available": True,
            "summary_scope": "point",
            "query_point": {"lat": lat, "lon": lon},
            "radius_m": radius_m,
            "crime_types": crime_types,
            "total_incidents": sum(item["count"] for item in crime_types),
        }


class DataService:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()
        self._road_graph = RoadGraph(db_path)
        self._transit = TransitNetwork(db_path)
        self._osrm = OsrmService()
        self._property_estimator = PropertyEstimator(db_path)
        provider = SQLiteCrimeProvider(db_path)
        self._crime_provider: CrimeProvider = (
            provider if provider.is_available() else UnavailableCrimeProvider()
        )

    def _ensure_schema(self) -> None:
        connection = connect_db(self._db_path)
        try:
            init_open_data_db(connection)
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get_nearest_property(self, lat: float, lon: float) -> dict[str, Any]:
        nearest_properties = self._nearest_properties(lat, lon, limit=15)
        if not nearest_properties:
            raise ValueError("No properties with coordinates were found in the database.")

        nearest_property = nearest_properties[0]
        estimation_summary = summarize_property_cluster(nearest_properties)

        return {
            "query_point": {"lat": lat, "lon": lon},
            "selected_property": nearest_property,
            "estimator_summary": estimation_summary,
            "nearby_sample": nearest_properties,
        }

    def get_top_x(self, lat: float, lon: float, limit: int, category: str) -> dict[str, Any]:
        normalized_category = category.lower()
        if normalized_category == "schools":
            raw_categories = ("School", "school")
        elif normalized_category == "parks":
            raw_categories = ("Park", "park")
        else:
            raise ValueError("Unsupported category.")

        placeholders = ",".join("?" for _ in raw_categories)
        lon_scale = math.cos(math.radians(lat))

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT canonical_poi_id, name, raw_category, address, lat, lon
                FROM poi_prod
                WHERE lat IS NOT NULL
                  AND lon IS NOT NULL
                  AND raw_category IN ({placeholders})
                ORDER BY
                  ((lat - ?) * (lat - ?))
                  + (((lon - ?) * ?) * ((lon - ?) * ?))
                LIMIT ?
                """,
                (*raw_categories, lat, lat, lon, lon_scale, lon, lon_scale, limit),
            ).fetchall()

        results = []
        for row in rows:
            item_lat = float(row["lat"])
            item_lon = float(row["lon"])
            results.append(
                {
                    "id": row["canonical_poi_id"],
                    "name": row["name"],
                    "raw_category": row["raw_category"],
                    "address": row["address"],
                    "lat": item_lat,
                    "lon": item_lon,
                    "distance_m": round(haversine_meters(lat, lon, item_lat, item_lon), 2),
                }
            )

        return {
            "query_point": {"lat": lat, "lon": lon},
            "category": normalized_category,
            "limit": limit,
            "results": results,
        }

    def query_pois(
        self,
        *,
        source: str | None = None,
        neighbourhood: str | None = None,
        category: str | None = None,
        poi_type: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        clauses = ["lat IS NOT NULL", "lon IS NOT NULL"]
        params: list[Any] = []

        if source:
            clauses.append("instr(source_ids_json, ?) > 0")
            params.append(source)
        if neighbourhood:
            clauses.append("UPPER(COALESCE(neighbourhood, '')) = UPPER(?)")
            params.append(neighbourhood)
        if category:
            clauses.append("UPPER(COALESCE(raw_category, '')) = UPPER(?)")
            params.append(category)
        if poi_type:
            clauses.append("UPPER(COALESCE(raw_subcategory, '')) = UPPER(?)")
            params.append(poi_type)

        query_lat = lat
        query_lon = lon
        if query_lat is not None and query_lon is not None:
            lon_scale = math.cos(math.radians(query_lat))
            order_by = (
                "ORDER BY ((lat - ?) * (lat - ?)) + (((lon - ?) * ?) * ((lon - ?) * ?))"
            )
            params.extend([query_lat, query_lat, query_lon, lon_scale, query_lon, lon_scale])
        else:
            order_by = "ORDER BY name"

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT canonical_poi_id, name, raw_category, raw_subcategory, address, lat, lon,
                       neighbourhood, source_dataset, source_provider, metadata_json
                FROM poi_prod
                WHERE {' AND '.join(clauses)}
                {order_by}
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()

        results = []
        for row in rows:
            item_lat = float(row["lat"])
            item_lon = float(row["lon"])
            distance_m = (
                round(haversine_meters(query_lat, query_lon, item_lat, item_lon), 2)
                if query_lat is not None and query_lon is not None
                else None
            )
            if radius_m is not None and distance_m is not None and distance_m > radius_m:
                continue
            results.append(
                {
                    "id": row["canonical_poi_id"],
                    "name": row["name"],
                    "raw_category": row["raw_category"],
                    "raw_subcategory": row["raw_subcategory"],
                    "address": row["address"],
                    "neighbourhood": row["neighbourhood"],
                    "lat": item_lat,
                    "lon": item_lon,
                    "distance_m": distance_m,
                    "source_dataset": row["source_dataset"],
                    "source_provider": row["source_provider"],
                    "metadata": safe_json_loads(row["metadata_json"], {}),
                }
            )

        return {
            "query": {
                "source": source,
                "neighbourhood": neighbourhood,
                "category": category,
                "type": poi_type,
                "lat": query_lat,
                "lon": query_lon,
                "radius_m": radius_m,
                "limit": limit,
            },
            "results": results,
        }

    def get_neighborhoods(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT neighbourhood
                FROM property_locations_prod
                WHERE neighbourhood IS NOT NULL
                  AND neighbourhood <> ''
                ORDER BY neighbourhood
                """
            ).fetchall()

        return [row["neighbourhood"] for row in rows]

    def get_neighborhood_summary(
        self, neighbourhood: str, detail_level: str = "high"
    ) -> dict[str, Any]:
        normalized_detail_level = detail_level.strip().lower()
        if normalized_detail_level not in {"high", "detailed"}:
            raise ValueError("detail_level must be either 'high' or 'detailed'.")

        with self._connect() as connection:
            property_row = connection.execute(
                """
                SELECT
                  COUNT(*) AS property_count,
                  AVG(assessment_value) AS average_assessment,
                  MIN(lat) AS min_lat,
                  MAX(lat) AS max_lat,
                  MIN(lon) AS min_lon,
                  MAX(lon) AS max_lon
                FROM property_locations_prod
                WHERE neighbourhood = ?
                  AND lat IS NOT NULL
                  AND lon IS NOT NULL
                """,
                (neighbourhood,),
            ).fetchone()

            if not property_row or int(property_row["property_count"] or 0) == 0:
                raise ValueError("Neighbourhood not found in property data.")

            bbox = {
                "min_lat": float(property_row["min_lat"]),
                "max_lat": float(property_row["max_lat"]),
                "min_lon": float(property_row["min_lon"]),
                "max_lon": float(property_row["max_lon"]),
            }

            schools = self._count_pois_in_bbox(connection, ("School", "school"), bbox)
            parks = self._count_pois_in_bbox(connection, ("Park", "park"), bbox)
            playgrounds = self._count_pois_in_bbox(
                connection, ("Playground", "playground"), bbox
            )

            road_row = connection.execute(
                """
                SELECT COALESCE(SUM(length_m), 0) AS road_length_m
                FROM road_segments_prod
                WHERE center_lat BETWEEN ? AND ?
                  AND center_lon BETWEEN ? AND ?
                """,
                (bbox["min_lat"], bbox["max_lat"], bbox["min_lon"], bbox["max_lon"]),
            ).fetchone()

            road_type_rows = []
            if normalized_detail_level == "detailed":
                road_type_rows = connection.execute(
                    """
                    SELECT
                      COALESCE(NULLIF(TRIM(segment_type), ''), 'Unknown') AS road_type,
                      COALESCE(SUM(length_m), 0) AS road_length_m,
                      COUNT(*) AS segment_count
                    FROM road_segments_prod
                    WHERE center_lat BETWEEN ? AND ?
                      AND center_lon BETWEEN ? AND ?
                    GROUP BY COALESCE(NULLIF(TRIM(segment_type), ''), 'Unknown')
                    ORDER BY road_length_m DESC, road_type
                    """,
                    (
                        bbox["min_lat"],
                        bbox["max_lat"],
                        bbox["min_lon"],
                        bbox["max_lon"],
                    ),
                ).fetchall()

            codes_rows = connection.execute(
                """
                SELECT DISTINCT neighbourhood_id, ward
                FROM property_locations_prod
                WHERE neighbourhood = ?
                ORDER BY neighbourhood_id, ward
                """,
                (neighbourhood,),
            ).fetchall()

            housing_rows = connection.execute(
                """
                SELECT year_built, lot_size, total_gross_area, garage
                FROM property_locations_prod
                WHERE UPPER(COALESCE(neighbourhood, '')) = UPPER(?)
                """,
                (neighbourhood,),
            ).fetchall()

        area_codes: list[str] = []
        for row in codes_rows:
            if row["neighbourhood_id"] is not None:
                area_codes.append(f"neighbourhood_id:{row['neighbourhood_id']}")
            if row["ward"]:
                area_codes.append(f"ward:{row['ward']}")

        current_year = 2026
        age_values: list[float] = []
        size_values: list[float] = []
        garage_yes_count = 0
        garage_known_count = 0

        for row in housing_rows:
            year_built = safe_float(row["year_built"])
            if year_built is not None and 1800 <= year_built <= current_year:
                age_values.append(current_year - year_built)

            size_value = safe_float(row["lot_size"])
            if size_value is None:
                size_value = safe_float(row["total_gross_area"])
            if size_value is not None and size_value >= 0:
                size_values.append(size_value)

            garage_value = safe_text(row["garage"])
            if garage_value is not None:
                normalized_garage = garage_value.strip().upper()
                if normalized_garage in {"Y", "YES", "TRUE", "1"}:
                    garage_yes_count += 1
                    garage_known_count += 1
                elif normalized_garage in {"N", "NO", "FALSE", "0"}:
                    garage_known_count += 1

        deduped_area_codes = sorted(set(area_codes))

        road_type_breakdown = [
            {
                "road_type": row["road_type"],
                "road_length_m": round(float(row["road_length_m"] or 0), 2),
                "segment_count": int(row["segment_count"] or 0),
            }
            for row in road_type_rows
        ]

        return {
            "neighbourhood": neighbourhood,
            "detail_level": normalized_detail_level,
            "number_of_properties": int(property_row["property_count"]),
            "average_assessment": round(float(property_row["average_assessment"] or 0), 2),
            "number_of_schools": schools,
            "number_of_parks": parks,
            "number_of_playgrounds": playgrounds,
            "road_length_m": round(float(road_row["road_length_m"] or 0), 2),
            "area_codes": deduped_area_codes,
            "bounding_box_method": "property_extent_bbox",
            "average_house_age_years": round(sum(age_values) / len(age_values), 2)
            if age_values
            else None,
            "average_house_size": round(sum(size_values) / len(size_values), 2)
            if size_values
            else None,
            "house_age_row_count": len(age_values),
            "house_size_row_count": len(size_values),
            "garage_known_row_count": garage_known_count,
            "garage_yes_row_count": garage_yes_count,
            "garage_percentage": round((garage_yes_count / garage_known_count) * 100, 2)
            if garage_known_count
            else None,
            "total_row_count_considered": len(housing_rows),
            "road_type_breakdown": road_type_breakdown,
        }

    def get_point_distances(self, points: list[dict[str, float]]) -> dict[str, Any]:
        if len(points) < 2:
            raise ValueError("At least two points are required.")

        segments = []
        total_straight_line = 0.0
        total_road_distance = 0.0

        for index in range(len(points) - 1):
            start_point = points[index]
            end_point = points[index + 1]
            route = self._road_graph.route_distance(
                start_point["lat"],
                start_point["lon"],
                end_point["lat"],
                end_point["lon"],
            )
            total_straight_line += route["straight_line_m"]
            total_road_distance += route["road_distance_m"]
            segments.append(
                {
                    "from_index": index,
                    "to_index": index + 1,
                    "from_point": start_point,
                    "to_point": end_point,
                    **route,
                }
            )

        return {
            "points": points,
            "segments": segments,
            "total_straight_line_m": round(total_straight_line, 2),
            "total_road_distance_m": round(total_road_distance, 2),
        }

    def get_osrm_nearest(self, lat: float, lon: float, profile: str) -> dict[str, Any]:
        return self._osrm.nearest(lat, lon, profile)

    def get_osrm_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        profile: str,
    ) -> dict[str, Any]:
        return self._osrm.route(start_lat, start_lon, end_lat, end_lon, profile)

    def get_osrm_matrix(self, points: list[dict[str, float]], profile: str) -> dict[str, Any]:
        return self._osrm.matrix(points, profile)

    def list_transit_routes(self) -> dict[str, Any]:
        routes = self._transit.list_routes()
        return {
            "available": bool(routes),
            "route_count": len(routes),
            "routes": routes,
        }

    def get_transit_stops(self, route_id: str | None = None) -> dict[str, Any]:
        stops = self._transit.get_stops(route_id=route_id)
        return {
            "available": bool(stops),
            "route_id": route_id,
            "stop_count": len(stops),
            "stops": stops,
        }

    def get_transit_route_details(self, route_id: str) -> dict[str, Any]:
        details = self._transit.get_route_details(route_id)
        return {
            "available": True,
            **details,
        }

    def plan_transit_journey(
        self,
        origin_input: dict[str, Any],
        destination_input: dict[str, Any],
    ) -> dict[str, Any]:
        origin = self._resolve_location_input(origin_input, "origin")
        destination = self._resolve_location_input(destination_input, "destination")
        return self._transit.plan_journey(origin, destination)

    def get_crime_summary(
        self,
        *,
        neighbourhood: str | None = None,
        property_query: str | None = None,
        radius_m: float = 1_000.0,
    ) -> dict[str, Any]:
        if neighbourhood:
            return self._crime_provider.summary_by_neighbourhood(neighbourhood)

        if property_query:
            property_match = self.find_property_by_text(property_query)
            if not property_match:
                raise ValueError("No property matched the supplied address or property identifier.")

            if isinstance(self._crime_provider, SQLiteCrimeProvider) and self._crime_provider.is_available():
                if property_match.get("lat") is not None and property_match.get("lon") is not None:
                    summary = self._crime_provider.summary_by_point(
                        float(property_match["lat"]),
                        float(property_match["lon"]),
                        radius_m,
                    )
                elif property_match.get("neighbourhood"):
                    summary = self._crime_provider.summary_by_neighbourhood(
                        str(property_match["neighbourhood"])
                    )
                else:
                    summary = UnavailableCrimeProvider().summary_by_point(0.0, 0.0, radius_m)
            else:
                summary = UnavailableCrimeProvider().summary_by_point(
                    float(property_match.get("lat") or 0.0),
                    float(property_match.get("lon") or 0.0),
                    radius_m,
                )

            summary["property_match"] = property_match
            return summary

        raise ValueError("Provide either neighbourhood or property_query.")

    def get_property_estimate(
        self,
        lat: float,
        lon: float,
        property_attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._property_estimator.estimate(
            lat=lat,
            lon=lon,
            property_attributes=property_attributes,
        )

    def _resolve_location_input(self, raw_value: dict[str, Any], label: str) -> dict[str, Any]:
        if not isinstance(raw_value, dict):
            raise ValueError(f"{label} must be an object.")

        lat = safe_float(raw_value.get("lat"))
        lon = safe_float(raw_value.get("lon"))
        if lat is not None and lon is not None:
            return {
                "label": safe_text(raw_value.get("label")) or f"{label.title()} coordinates",
                "lat": lat,
                "lon": lon,
                "source": "coordinates",
            }

        text = safe_text(raw_value.get("text") or raw_value.get("address"))
        if text:
            property_match = self.find_property_by_text(text)
            if not property_match or property_match.get("lat") is None or property_match.get("lon") is None:
                raise ValueError(f"Could not resolve {label} from the supplied address or property text.")
            return {
                "label": property_match["address"],
                "lat": float(property_match["lat"]),
                "lon": float(property_match["lon"]),
                "source": "property_lookup",
                "property_match": property_match,
            }

        raise ValueError(f"{label} must include either lat/lon or address text.")

    def find_property_by_text(self, search_text: str) -> dict[str, Any] | None:
        normalized = search_text.strip()
        if not normalized:
            raise ValueError("Property search text is required.")

        like_value = f"%{normalized.upper()}%"
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT canonical_location_id, house_number, street_name, neighbourhood, ward, lat, lon
                FROM property_locations_prod
                WHERE canonical_location_id = ?
                   OR UPPER(TRIM(COALESCE(house_number, '') || ' ' || COALESCE(street_name, ''))) LIKE ?
                ORDER BY
                  CASE WHEN canonical_location_id = ? THEN 0 ELSE 1 END,
                  canonical_location_id
                LIMIT 1
                """,
                (normalized, like_value, normalized),
            ).fetchone()

        if not row:
            return None

        address = " ".join(
            part for part in [safe_text(row["house_number"]), safe_text(row["street_name"])] if part
        ).strip()
        return {
            "canonical_location_id": row["canonical_location_id"],
            "address": address or "Address unavailable",
            "neighbourhood": row["neighbourhood"],
            "ward": row["ward"],
            "lat": safe_float(row["lat"]),
            "lon": safe_float(row["lon"]),
        }

    def _nearest_properties(self, lat: float, lon: float, limit: int) -> list[dict[str, Any]]:
        lon_scale = math.cos(math.radians(lat))

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                  canonical_location_id,
                  assessment_year,
                  assessment_value,
                  house_number,
                  street_name,
                  neighbourhood_id,
                  neighbourhood,
                  ward,
                  lat,
                  lon
                FROM property_locations_prod
                WHERE lat IS NOT NULL
                  AND lon IS NOT NULL
                ORDER BY
                  ((lat - ?) * (lat - ?))
                  + (((lon - ?) * ?) * ((lon - ?) * ?))
                LIMIT ?
                """,
                (lat, lat, lon, lon_scale, lon, lon_scale, limit),
            ).fetchall()

        properties = []
        for row in rows:
            item_lat = float(row["lat"])
            item_lon = float(row["lon"])
            address = " ".join(
                part for part in [row["house_number"], row["street_name"]] if part
            ).strip()
            properties.append(
                {
                    "canonical_location_id": row["canonical_location_id"],
                    "assessment_year": row["assessment_year"],
                    "assessment_value": safe_float(row["assessment_value"]),
                    "house_number": row["house_number"],
                    "street_name": row["street_name"],
                    "address": address or "Address unavailable",
                    "neighbourhood_id": safe_float(row["neighbourhood_id"]),
                    "neighbourhood": row["neighbourhood"],
                    "ward": row["ward"],
                    "lat": item_lat,
                    "lon": item_lon,
                    "distance_m": round(haversine_meters(lat, lon, item_lat, item_lon), 2),
                }
            )

        return properties

    @staticmethod
    def _count_pois_in_bbox(
        connection: sqlite3.Connection,
        categories: tuple[str, ...],
        bbox: dict[str, float],
    ) -> int:
        placeholders = ",".join("?" for _ in categories)
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS item_count
            FROM poi_prod
            WHERE raw_category IN ({placeholders})
              AND lat BETWEEN ? AND ?
              AND lon BETWEEN ? AND ?
            """,
            (*categories, bbox["min_lat"], bbox["max_lat"], bbox["min_lon"], bbox["max_lon"]),
        ).fetchone()
        return int(row["item_count"] or 0)
