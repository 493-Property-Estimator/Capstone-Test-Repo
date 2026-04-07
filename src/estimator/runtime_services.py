from __future__ import annotations

import json
import math
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


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


def safe_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
        if not routes:
            raise OsrmError("OSRM route returned no routes.")

        route = routes[0]
        return {
            "distance_m": round(float(route.get("distance") or 0.0), 2),
            "duration_s": round(float(route.get("duration") or 0.0), 2),
            "duration_min": round(float(route.get("duration") or 0.0) / 60.0, 2),
            "geometry": route.get("geometry"),
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


class CrimeProvider:
    def summary_by_neighbourhood(self, neighbourhood: str) -> dict[str, Any]:
        raise NotImplementedError

    def summary_by_point(self, lat: float, lon: float, radius_m: float) -> dict[str, Any]:
        raise NotImplementedError


class UnavailableCrimeProvider(CrimeProvider):
    def is_available(self) -> bool:
        return False

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

