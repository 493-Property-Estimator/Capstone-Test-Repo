#!/usr/bin/env python3
"""Auto-discover known data files and ingest them into the SQLite database."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_sourcing.config import DEFAULT_DB_PATH  # noqa: E402
from data_sourcing.service import IngestionService  # noqa: E402


@dataclass
class PlannedSource:
    source_key: str
    file_path: Path | None
    reason: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest known files from src/data_sourcing/data")
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "src" / "data_sourcing" / "data"),
        help="Directory that contains downloaded datasets",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    parser.add_argument("--dry-run", action="store_true", help="Only show planned ingests")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue ingesting remaining files if one source fails",
    )
    parser.add_argument(
        "--include-osm",
        action="store_true",
        help="Also ingest OSM roads/POIs if matching files are found",
    )
    return parser.parse_args()


def _pick_latest(data_dir: Path, patterns: list[str]) -> Path | None:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(data_dir.glob(pattern))
    if not candidates:
        return None
    return sorted(candidates)[-1]


def _pick_assessment_csv(data_dir: Path) -> Path | None:
    return _pick_latest(data_dir, ["Property_Assessment_Data_*.csv"])


def _pick_property_info_path(data_dir: Path) -> Path | None:
    return _pick_latest(data_dir, ["Property Information*.csv", "Property Information*.zip"])


def _pick_transit_stops_zip(data_dir: Path) -> Path | None:
    return _pick_latest(data_dir, ["ETS Bus Schedule GTFS Data Feed - Stops*.zip"])


def _pick_transit_trips_zip(data_dir: Path) -> Path | None:
    return _pick_latest(data_dir, ["ETS Bus Schedule GTFS Data Feed - Trips*.zip"])


def _pick_school_locations_path(data_dir: Path) -> Path | None:
    return _pick_latest(
        data_dir,
        [
            "Edmonton Public School Board (EPSB)_School Locations_*.csv",
            "Edmonton Public School Board (EPSB)_School Locations_*.zip",
        ],
    )


def _pick_police_stations_path(data_dir: Path) -> Path | None:
    return _pick_latest(data_dir, ["Police Stations_*.csv", "Police Stations_*.zip"])


def _pick_playgrounds_path(data_dir: Path) -> Path | None:
    return _pick_latest(data_dir, ["Playgrounds_*.csv", "Playgrounds_*.zip"])


def _pick_parks_path(data_dir: Path) -> Path | None:
    return _pick_latest(data_dir, ["Parks_*.csv", "Parks_*.zip"])


def _pick_osm_roads_path(data_dir: Path) -> Path | None:
    shp = data_dir / "_tmp_alberta_layers" / "gis_osm_roads_free_1.shp"
    if shp.exists():
        return shp
    zips = sorted(data_dir.glob("alberta-*.shp.zip"))
    return zips[-1] if zips else None


def _pick_osm_pois_path(data_dir: Path) -> Path | None:
    shp = data_dir / "_tmp_alberta_layers" / "gis_osm_pois_free_1.shp"
    if shp.exists():
        return shp
    zips = sorted(data_dir.glob("alberta-*.shp.zip"))
    return zips[-1] if zips else None


def _bundled_roads_snapshot() -> Path | None:
    candidate = ROOT / "src" / "data_sourcing" / "sources" / "geospatial_roads.json"
    return candidate if candidate.exists() else None


def discover_sources(data_dir: Path, include_osm: bool = False) -> tuple[list[PlannedSource], list[str]]:
    planned: list[PlannedSource] = []
    notes: list[str] = []

    assessment_csv = _pick_assessment_csv(data_dir)
    if assessment_csv:
        planned.append(
            PlannedSource(
                source_key="assessments.property_tax_csv",
                file_path=assessment_csv,
                reason="latest Property_Assessment_Data_*.csv",
            )
        )
    else:
        notes.append("No assessment CSV matched Property_Assessment_Data_*.csv")

    property_info_path = _pick_property_info_path(data_dir)
    if property_info_path:
        planned.append(
            PlannedSource(
                source_key="assessments.property_information",
                file_path=property_info_path,
                reason="latest Property Information CSV/ZIP",
            )
        )
    else:
        notes.append("No property information file matched Property Information*.csv or Property Information*.zip")

    school_locations = _pick_school_locations_path(data_dir)
    if school_locations:
        planned.append(
            PlannedSource(
                source_key="geospatial.school_locations",
                file_path=school_locations,
                reason="latest EPSB school locations CSV/ZIP",
            )
        )
    else:
        notes.append("No school locations file matched Edmonton Public School Board (EPSB)_School Locations_*.csv/.zip")

    police_stations = _pick_police_stations_path(data_dir)
    if police_stations:
        planned.append(
            PlannedSource(
                source_key="geospatial.police_stations",
                file_path=police_stations,
                reason="latest Police Stations CSV/ZIP",
            )
        )
    else:
        notes.append("No police station file matched Police Stations_*.csv or Police Stations_*.zip")

    playgrounds = _pick_playgrounds_path(data_dir)
    if playgrounds:
        planned.append(
            PlannedSource(
                source_key="geospatial.playgrounds",
                file_path=playgrounds,
                reason="latest Playgrounds CSV/ZIP",
            )
        )
    else:
        notes.append("No playground file matched Playgrounds_*.csv or Playgrounds_*.zip")

    parks = _pick_parks_path(data_dir)
    if parks:
        planned.append(
            PlannedSource(
                source_key="geospatial.parks",
                file_path=parks,
                reason="latest Parks CSV/ZIP",
            )
        )
    else:
        notes.append("No parks file matched Parks_*.csv or Parks_*.zip")

    roads_snapshot = _bundled_roads_snapshot()
    if roads_snapshot:
        planned.append(
            PlannedSource(
                source_key="geospatial.roads",
                file_path=roads_snapshot,
                reason="bundled local geospatial_roads.json snapshot",
            )
        )
    else:
        notes.append("No bundled geospatial roads snapshot found at src/data_sourcing/sources/geospatial_roads.json")

    transit_stops_zip = _pick_transit_stops_zip(data_dir)
    if transit_stops_zip:
        planned.append(
            PlannedSource(
                source_key="transit.ets_stops",
                file_path=transit_stops_zip,
                reason="latest ETS GTFS stops zip",
            )
        )
    else:
        notes.append("No ETS GTFS stops ZIP matched ETS Bus Schedule GTFS Data Feed - Stops*.zip")

    transit_trips_zip = _pick_transit_trips_zip(data_dir)
    if transit_trips_zip:
        planned.append(
            PlannedSource(
                source_key="transit.ets_trips",
                file_path=transit_trips_zip,
                reason="latest ETS GTFS trips zip",
            )
        )
    else:
        notes.append("No ETS GTFS trips ZIP matched ETS Bus Schedule GTFS Data Feed - Trips*.zip")

    if include_osm:
        osm_roads = _pick_osm_roads_path(data_dir)
        if osm_roads:
            planned.append(
                PlannedSource(
                    source_key="geospatial.osm_alberta",
                    file_path=osm_roads,
                    reason="OSM roads shapefile (or Alberta zip fallback)",
                )
            )
        else:
            notes.append("No OSM roads file found (expected _tmp_alberta_layers/gis_osm_roads_free_1.shp or alberta-*.shp.zip)")

        osm_pois = _pick_osm_pois_path(data_dir)
        if osm_pois:
            planned.append(
                PlannedSource(
                    source_key="geospatial.osm_pois_alberta",
                    file_path=osm_pois,
                    reason="OSM POIs shapefile (or Alberta zip fallback)",
                )
            )
        else:
            notes.append("No OSM POIs file found (expected _tmp_alberta_layers/gis_osm_pois_free_1.shp or alberta-*.shp.zip)")

    return planned, notes


def run() -> int:
    args = _parse_args()
    data_dir = Path(args.data_dir).resolve()
    service = IngestionService(db_path=args.db)

    if not data_dir.exists():
        print(json.dumps({"status": "failed", "error": f"data_dir does not exist: {data_dir}"}, indent=2))
        return 2

    planned, notes = discover_sources(data_dir, include_osm=args.include_osm)
    plan_payload = [
        {
                "source_key": item.source_key,
                "file_path": str(item.file_path) if item.file_path else None,
                "reason": item.reason,
            }
        for item in planned
    ]

    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "data_dir": str(data_dir),
                    "planned_sources": plan_payload,
                    "notes": notes,
                },
                indent=2,
            )
        )
        return 0

    init_result = service.init_database()
    results: list[dict[str, Any]] = []
    overall_failed = False

    for item in planned:
        override = {item.source_key: str(item.file_path)} if item.file_path else None
        result = service.ingest(source_keys=[item.source_key], source_overrides=override, trigger="manual")
        results.append(
            {
                "source_key": item.source_key,
                "file_path": str(item.file_path) if item.file_path else None,
                "status": result.get("status"),
                "result": result,
            }
        )
        if result.get("status") not in {"succeeded", "partial_success"}:
            overall_failed = True
            if not args.continue_on_error:
                break

    final_status = "failed" if overall_failed else "succeeded"
    print(
        json.dumps(
            {
                "status": final_status,
                "data_dir": str(data_dir),
                "planned_sources": plan_payload,
                "notes": notes,
                "init_db": init_result,
                "runs": results,
            },
            indent=2,
        )
    )
    return 1 if overall_failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
