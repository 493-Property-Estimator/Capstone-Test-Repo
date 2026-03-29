from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "TestingStage" / "frontend"
DATABASE_PATH = REPO_ROOT / "src" / "data_sourcing" / "open_data.db"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from TestingStage.backend.services import DataService, OsrmError


class TestingStageHandler(SimpleHTTPRequestHandler):
    api_prefix = "/api"
    route_aliases = {
        "/": "index.html",
        "/top-x": "top-x.html",
        "/distance-points": "distance-points.html",
        "/neighborhood-results": "neighborhood-results.html",
        "/osrm": "osrm.html",
        "/crime": "crime.html",
        "/transit": "transit.html",
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
                detail_level = (query.get("detail_level") or ["high"])[0]
                if not neighbourhood:
                    raise ValueError("Query parameter 'name' is required.")
                self._send_json(
                    self.data_service.get_neighborhood_summary(
                        neighbourhood,
                        detail_level=detail_level,
                    )
                )
                return

            if parsed_url.path == "/api/transit/routes":
                self._send_json(self.data_service.list_transit_routes())
                return

            if parsed_url.path == "/api/transit/stops":
                query = parse_qs(parsed_url.query)
                route_id = (query.get("route_id") or [None])[0]
                self._send_json(self.data_service.get_transit_stops(route_id=route_id))
                return

            if parsed_url.path == "/api/transit/route":
                query = parse_qs(parsed_url.query)
                route_id = (query.get("route_id") or [None])[0]
                if not route_id:
                    raise ValueError("Query parameter 'route_id' is required.")
                self._send_json(self.data_service.get_transit_route_details(route_id))
                return

            self.send_error(HTTPStatus.NOT_FOUND, "API endpoint not found.")
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except OsrmError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_GATEWAY)
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

            if parsed_url.path == "/api/pois/query":
                limit = int(body.get("limit", 20))
                if limit < 1 or limit > 100:
                    raise ValueError("Limit must be between 1 and 100.")

                query_lat = body.get("lat")
                query_lon = body.get("lon")
                if (query_lat is None) != (query_lon is None):
                    raise ValueError("lat and lon must be provided together.")

                point = (
                    self._normalize_point({"lat": query_lat, "lon": query_lon})
                    if query_lat is not None and query_lon is not None
                    else None
                )
                radius_m = body.get("radius_m")
                radius_value = float(radius_m) if radius_m not in (None, "") else None
                if radius_value is not None and radius_value <= 0:
                    raise ValueError("radius_m must be greater than 0 when provided.")

                self._send_json(
                    self.data_service.query_pois(
                        source=self._optional_text(body.get("source")),
                        neighbourhood=self._optional_text(body.get("neighbourhood")),
                        category=self._optional_text(body.get("category")),
                        poi_type=self._optional_text(body.get("type")),
                        lat=point["lat"] if point else None,
                        lon=point["lon"] if point else None,
                        radius_m=radius_value,
                        limit=limit,
                    )
                )
                return

            if parsed_url.path == "/api/point-distances":
                raw_points = body.get("points")
                if not isinstance(raw_points, list):
                    raise ValueError("'points' must be an array.")
                points = [self._normalize_point(point) for point in raw_points]
                self._send_json(self.data_service.get_point_distances(points))
                return

            if parsed_url.path == "/api/osrm/nearest":
                lat, lon = self._extract_lat_lon(body)
                profile = self._extract_profile(body)
                self._send_json(self.data_service.get_osrm_nearest(lat, lon, profile))
                return

            if parsed_url.path == "/api/osrm/route":
                start_point = self._normalize_point(body.get("start"))
                end_point = self._normalize_point(body.get("end"))
                profile = self._extract_profile(body)
                self._send_json(
                    self.data_service.get_osrm_route(
                        start_point["lat"],
                        start_point["lon"],
                        end_point["lat"],
                        end_point["lon"],
                        profile,
                    )
                )
                return

            if parsed_url.path == "/api/osrm/matrix":
                raw_points = body.get("points")
                if not isinstance(raw_points, list):
                    raise ValueError("'points' must be an array.")
                points = [self._normalize_point(point) for point in raw_points]
                profile = self._extract_profile(body)
                self._send_json(self.data_service.get_osrm_matrix(points, profile))
                return

            if parsed_url.path == "/api/crime-summary":
                neighbourhood = self._optional_text(body.get("neighbourhood"))
                property_query = self._optional_text(body.get("property_query"))
                radius_m = float(body.get("radius_m", 1000))
                if radius_m <= 0:
                    raise ValueError("radius_m must be greater than 0.")
                self._send_json(
                    self.data_service.get_crime_summary(
                        neighbourhood=neighbourhood,
                        property_query=property_query,
                        radius_m=radius_m,
                    )
                )
                return

            if parsed_url.path == "/api/transit/journey":
                origin = body.get("origin")
                destination = body.get("destination")
                if origin is None or destination is None:
                    raise ValueError("Both origin and destination are required.")
                self._send_json(
                    self.data_service.plan_transit_journey(origin, destination)
                )
                return

            self.send_error(HTTPStatus.NOT_FOUND, "API endpoint not found.")
        except ValueError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json(
                {"error": "Request body must be valid JSON."},
                status=HTTPStatus.BAD_REQUEST,
            )
        except OsrmError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_GATEWAY)
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
    def _extract_profile(body: dict) -> str:
        profile = str(body.get("profile", "driving")).strip().lower()
        if profile not in {"driving", "walking", "biking"}:
            raise ValueError("Profile must be one of driving, walking, or biking.")
        return profile

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

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


def run(host: str = "127.0.0.1", port: int = 8010) -> None:
    server = ThreadingHTTPServer((host, port), TestingStageHandler)
    print(f"TestingStage server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
