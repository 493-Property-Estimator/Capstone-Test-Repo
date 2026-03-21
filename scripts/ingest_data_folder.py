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
    file_path: Path
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
    return parser.parse_args()


def _pick_assessment_csv(data_dir: Path) -> Path | None:
    candidates = sorted(data_dir.glob("Property_Assessment_Data_*.csv"))
    return candidates[-1] if candidates else None


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


def discover_sources(data_dir: Path) -> tuple[list[PlannedSource], list[str]]:
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

    planned, notes = discover_sources(data_dir)
    plan_payload = [
        {
            "source_key": item.source_key,
            "file_path": str(item.file_path),
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
        override = {item.source_key: str(item.file_path)}
        result = service.ingest(source_keys=[item.source_key], source_overrides=override, trigger="manual")
        results.append(
            {
                "source_key": item.source_key,
                "file_path": str(item.file_path),
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
