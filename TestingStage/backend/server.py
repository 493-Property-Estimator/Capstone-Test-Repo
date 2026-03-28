from __future__ import annotations

import heapq
import json
import math
import sqlite3
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "TestingStage" / "frontend"
DATABASE_PATH = REPO_ROOT / "src" / "data_sourcing" / "open_data.db"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
    if value is None:
        return None
    return float(value)


@dataclass
class RoadSnap:
    node_key: str
    lat: float
    lon: float
    access_distance_m: float


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

    def route_distance(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> dict:
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
    def _snap_payload(snap: RoadSnap) -> dict:
        return {
            "lat": snap.lat,
            "lon": snap.lon,
            "access_distance_m": round(snap.access_distance_m, 2),
        }


class DataService:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._road_graph = RoadGraph(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get_nearest_property(self, lat: float, lon: float) -> dict:
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

    def get_top_x(self, lat: float, lon: float, limit: int, category: str) -> dict:
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

    def get_neighborhood_summary(self, neighbourhood: str) -> dict:
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

            codes_rows = connection.execute(
                """
                SELECT DISTINCT neighbourhood_id, ward
                FROM property_locations_prod
                WHERE neighbourhood = ?
                ORDER BY neighbourhood_id, ward
                """,
                (neighbourhood,),
            ).fetchall()

        area_codes: list[str] = []
        for row in codes_rows:
            if row["neighbourhood_id"] is not None:
                area_codes.append(f"neighbourhood_id:{row['neighbourhood_id']}")
            if row["ward"]:
                area_codes.append(f"ward:{row['ward']}")

        deduped_area_codes = sorted(set(area_codes))

        return {
            "neighbourhood": neighbourhood,
            "number_of_properties": int(property_row["property_count"]),
            "average_assessment": round(float(property_row["average_assessment"] or 0), 2),
            "number_of_schools": schools,
            "number_of_parks": parks,
            "number_of_playgrounds": playgrounds,
            "road_length_m": round(float(road_row["road_length_m"] or 0), 2),
            "area_codes": deduped_area_codes,
            "bounding_box_method": "property_extent_bbox",
        }

    def get_point_distances(self, points: list[dict]) -> dict:
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

    def _nearest_properties(self, lat: float, lon: float, limit: int) -> list[dict]:
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


class TestingStageHandler(SimpleHTTPRequestHandler):
    api_prefix = "/api"
    route_aliases = {
        "/": "index.html",
        "/top-x": "top-x.html",
        "/distance-points": "distance-points.html",
        "/neighborhood-results": "neighborhood-results.html",
    }
    data_service = DataService(DATABASE_PATH)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        if parsed_url.path.startswith(self.api_prefix):
            self._handle_api_get(parsed_url)
            return

        alias_target = self.route_aliases.get(parsed_url.path)
        if alias_target:
            self.path = f"/{alias_target}"
        super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        if parsed_url.path.startswith(self.api_prefix):
            self._handle_api_post(parsed_url)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found.")

    def _handle_api_get(self, parsed_url) -> None:
        try:
            if parsed_url.path == "/api/health":
                self._send_json({"status": "ok", "database_path": str(DATABASE_PATH)})
                return

            if parsed_url.path == "/api/neighborhoods":
                self._send_json({"neighborhoods": self.data_service.get_neighborhoods()})
                return

            if parsed_url.path == "/api/neighborhood-summary":
                query = parse_qs(parsed_url.query)
                neighbourhood = (query.get("name") or [None])[0]
                if not neighbourhood:
                    raise ValueError("Query parameter 'name' is required.")
                self._send_json(self.data_service.get_neighborhood_summary(neighbourhood))
                return

            self.send_error(HTTPStatus.NOT_FOUND, "API endpoint not found.")
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_api_post(self, parsed_url) -> None:
        try:
            body = self._read_json_body()

            if parsed_url.path == "/api/nearest-property":
                lat, lon = self._extract_lat_lon(body)
                self._send_json(self.data_service.get_nearest_property(lat, lon))
                return

            if parsed_url.path == "/api/top-x":
                lat, lon = self._extract_lat_lon(body)
                limit = int(body.get("limit", 5))
                if limit < 1:
                    raise ValueError("Limit must be at least 1.")
                if limit > 100:
                    raise ValueError("Limit must be 100 or less.")
                category = str(body.get("category", "")).strip()
                self._send_json(self.data_service.get_top_x(lat, lon, limit, category))
                return

            if parsed_url.path == "/api/point-distances":
                raw_points = body.get("points")
                if not isinstance(raw_points, list):
                    raise ValueError("'points' must be an array.")
                points = [self._normalize_point(point) for point in raw_points]
                self._send_json(self.data_service.get_point_distances(points))
                return

            self.send_error(HTTPStatus.NOT_FOUND, "API endpoint not found.")
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json(
                {"error": "Request body must be valid JSON."},
                status=HTTPStatus.BAD_REQUEST,
            )
        except Exception as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        return json.loads(raw_body.decode("utf-8"))

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _extract_lat_lon(body: dict) -> tuple[float, float]:
        point = TestingStageHandler._normalize_point(body)
        return point["lat"], point["lon"]

    @staticmethod
    def _normalize_point(point: dict) -> dict:
        if not isinstance(point, dict):
            raise ValueError("Each point must be an object with lat and lon.")

        lat = float(point.get("lat"))
        lon = float(point.get("lon"))

        if lat < -90 or lat > 90:
            raise ValueError("Latitude must be between -90 and 90.")
        if lon < -180 or lon > 180:
            raise ValueError("Longitude must be between -180 and 180.")

        return {"lat": round(lat, 6), "lon": round(lon, 6)}


def run(host: str = "127.0.0.1", port: int = 8010) -> None:
    server = ThreadingHTTPServer((host, port), TestingStageHandler)
    print(f"TestingStage server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
