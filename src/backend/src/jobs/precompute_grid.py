from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from statistics import median

from fastapi import APIRouter, Request

from backend.src.db.connection import connect

router = APIRouter()


@router.post("/jobs/precompute-grid")
async def precompute_grid(request: Request):
    settings = request.app.state.settings
    run_id = f"grid-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    warnings: list[str] = []
    metrics = {
        "cell_count": 0,
        "flagged_cells": 0,
        "dataset_version": None,
    }
    try:
        _ensure_grid_table(settings.data_db_path)
        metrics = _compute_grid(
            db_path=settings.data_db_path,
            cell_size_deg=settings.grid_cell_size_deg,
            warnings=warnings,
        )
        status = "succeeded"
    except Exception as exc:
        status = "failed"
        warnings.append(str(exc))
    return {
        "job_id": run_id,
        "status": status,
        "warnings": warnings,
        "metrics": metrics,
    }


def _ensure_grid_table(db_path):
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS grid_features_prod (
                grid_id TEXT PRIMARY KEY,
                west REAL,
                south REAL,
                east REAL,
                north REAL,
                property_count INTEGER,
                mean_baseline_value REAL,
                median_baseline_value REAL,
                store_density REAL,
                store_type_distribution TEXT,
                avg_walkability_proxy REAL,
                green_space_density REAL,
                crime_rate_index REAL,
                crime_severity_index REAL,
                school_proximity_median_m REAL,
                dataset_version TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()


def _compute_grid(db_path, cell_size_deg: float, warnings: list[str]) -> dict[str, int | str | None]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT canonical_location_id, assessment_value, neighbourhood, lat, lon
            FROM property_locations_prod
            WHERE lat IS NOT NULL AND lon IS NOT NULL AND assessment_value IS NOT NULL
            """
        ).fetchall()
        if not rows:
            warnings.append("No property rows available for grid precompute.")
            return {"cell_count": 0, "flagged_cells": 0, "dataset_version": None}

        dataset_version = _dataset_version(conn)
        geo_rows = _load_geospatial_rows(conn) if _table_exists(conn, "geospatial_prod") else []
        crime_by_neighbourhood = _load_crime_summary(conn) if _table_exists(conn, "crime_summary_prod") else {}

        grid = {}
        for row in rows:
            lat = float(row["lat"])
            lon = float(row["lon"])
            grid_id = _grid_id(lon, lat, cell_size_deg)
            grid.setdefault(grid_id, {"properties": [], "geospatial": [], "schools": []})
            grid[grid_id]["properties"].append(dict(row))

        for geo in geo_rows:
            lat = geo.get("lat")
            lon = geo.get("lon")
            if lat is None or lon is None:
                continue
            grid_id = _grid_id(float(lon), float(lat), cell_size_deg)
            grid.setdefault(grid_id, {"properties": [], "geospatial": [], "schools": []})
            grid[grid_id]["geospatial"].append(geo)
            if (geo.get("raw_category") or "").lower() == "school":
                grid[grid_id]["schools"].append(geo)

        now = datetime.now(UTC).isoformat()
        flagged_cells = 0
        conn.execute("DELETE FROM grid_features_prod")
        for gid, bundle in grid.items():
            values = [float(item["assessment_value"]) for item in bundle["properties"]]
            if not values:
                continue
            mean_val = sum(values) / len(values)
            med_val = float(median(values))
            if mean_val < 10_000 or mean_val > 10_000_000:
                flagged_cells += 1
                warnings.append(f"Outlier mean_baseline_value in cell {gid}")
                mean_val = max(10_000.0, min(mean_val, 10_000_000.0))

            west, south, east, north = _grid_bounds(gid, cell_size_deg)
            area_km2 = max(_approx_cell_area_km2(south, north, west, east), 0.01)
            geo_features = bundle["geospatial"]
            store_features = [g for g in geo_features if "store" in (g.get("raw_category") or "").lower()]
            park_features = [
                g
                for g in geo_features
                if (g.get("raw_category") or "").lower() in {"park", "dog_park", "green_space"}
            ]

            school_dist_median = _school_median_distance(bundle["properties"], bundle["schools"])
            walk_proxy = _walkability_proxy(bundle["properties"])
            store_type_distribution = _store_type_distribution(store_features)
            crime_rate_index, crime_severity_index = _crime_indexes(bundle["properties"], crime_by_neighbourhood)

            conn.execute(
                """
                INSERT INTO grid_features_prod (
                    grid_id, west, south, east, north, property_count,
                    mean_baseline_value, median_baseline_value,
                    store_density, store_type_distribution, avg_walkability_proxy,
                    green_space_density, crime_rate_index, crime_severity_index,
                    school_proximity_median_m, dataset_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gid,
                    west,
                    south,
                    east,
                    north,
                    len(bundle["properties"]),
                    mean_val,
                    med_val,
                    round(len(store_features) / area_km2, 4),
                    json.dumps(store_type_distribution, sort_keys=True),
                    walk_proxy,
                    round(len(park_features) / area_km2, 4),
                    crime_rate_index,
                    crime_severity_index,
                    school_dist_median,
                    dataset_version,
                    now,
                ),
            )
        conn.commit()
        return {"cell_count": len(grid), "flagged_cells": flagged_cells, "dataset_version": dataset_version}


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _dataset_version(conn) -> str | None:
    row = conn.execute(
        """
        SELECT version_id
        FROM dataset_versions
        ORDER BY promoted_at DESC
        LIMIT 1
        """
    ).fetchone()
    return row["version_id"] if row else None


def _load_geospatial_rows(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT raw_category, lat, lon
        FROM geospatial_prod
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _load_crime_summary(conn) -> dict[str, dict[str, float]]:
    rows = conn.execute(
        """
        SELECT neighbourhood, AVG(COALESCE(rate_per_100k, 0)) AS rate_idx, AVG(COALESCE(incident_count, 0)) AS sev_idx
        FROM crime_summary_prod
        GROUP BY neighbourhood
        """
    ).fetchall()
    output: dict[str, dict[str, float]] = {}
    for row in rows:
        output[str(row["neighbourhood"] or "").strip().lower()] = {
            "rate_idx": round(float(row["rate_idx"] or 0.0), 4),
            "sev_idx": round(float(row["sev_idx"] or 0.0), 4),
        }
    return output


def _grid_id(lon: float, lat: float, cell_size_deg: float) -> str:
    gx = math.floor(lon / cell_size_deg)
    gy = math.floor(lat / cell_size_deg)
    return f"{gx}_{gy}"


def _grid_bounds(grid_id: str, cell_size_deg: float) -> tuple[float, float, float, float]:
    gx, gy = (int(part) for part in grid_id.split("_"))
    west = gx * cell_size_deg
    east = west + cell_size_deg
    south = gy * cell_size_deg
    north = south + cell_size_deg
    return west, south, east, north


def _approx_cell_area_km2(south: float, north: float, west: float, east: float) -> float:
    lat_mid = (south + north) / 2.0
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * max(math.cos(math.radians(lat_mid)), 0.1)
    height = abs(north - south) * km_per_deg_lat
    width = abs(east - west) * km_per_deg_lon
    return height * width


def _walkability_proxy(properties: list[dict]) -> float:
    # Cheap deterministic proxy centered around downtown Edmonton.
    downtown_lat = 53.5461
    downtown_lon = -113.4938
    distances = []
    for row in properties:
        lat = float(row["lat"])
        lon = float(row["lon"])
        d = math.sqrt((lat - downtown_lat) ** 2 + (lon - downtown_lon) ** 2)
        distances.append(d)
    avg = sum(distances) / len(distances)
    return round(max(0.0, 1.0 - avg * 5.0), 4)


def _store_type_distribution(store_features: list[dict]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for row in store_features:
        key = str(row.get("raw_category") or "unknown").strip().lower()
        dist[key] = dist.get(key, 0) + 1
    return dist


def _crime_indexes(properties: list[dict], crime_by_neighbourhood: dict[str, dict[str, float]]) -> tuple[float, float]:
    if not crime_by_neighbourhood:
        return 0.0, 0.0
    rates = []
    sevs = []
    for prop in properties:
        key = str(prop.get("neighbourhood") or "").strip().lower()
        value = crime_by_neighbourhood.get(key)
        if not value:
            continue
        rates.append(value["rate_idx"])
        sevs.append(value["sev_idx"])
    if not rates:
        return 0.0, 0.0
    return round(sum(rates) / len(rates), 4), round(sum(sevs) / len(sevs), 4)


def _school_median_distance(properties: list[dict], schools: list[dict]) -> float | None:
    if not schools or not properties:
        return None
    distances = []
    for prop in properties:
        lat = float(prop["lat"])
        lon = float(prop["lon"])
        nearest = None
        for school in schools:
            s_lat = float(school["lat"])
            s_lon = float(school["lon"])
            d = _haversine_m(lat, lon, s_lat, s_lon)
            if nearest is None or d < nearest:
                nearest = d
        if nearest is not None:
            distances.append(nearest)
    if not distances:
        return None
    return round(float(median(distances)), 2)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_m * c
