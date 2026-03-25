#!/usr/bin/env python3
"""Create a smaller SQLite sample DB containing property and POI records."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_sourcing.database import connect, init_db  # noqa: E402
from data_sourcing.config import DEFAULT_DB_PATH  # noqa: E402


PROPERTY_TABLES = (
    "property_locations_prod",
    "assessments_prod",
    "assessments_records_prod",
)

POI_TABLES = (
    "poi_prod",
    "poi_types",
    "poi_standardized_prod",
    "geospatial_prod",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a smaller sample DB with property and POI rows")
    parser.add_argument("--source-db", default=str(DEFAULT_DB_PATH), help="Source SQLite DB path")
    parser.add_argument("--output-db", required=True, help="Output SQLite DB path")
    parser.add_argument("--property-limit", type=int, default=100, help="Number of property rows to keep")
    parser.add_argument("--poi-limit", type=int, default=200, help="Number of POI rows to keep")
    return parser.parse_args()


def _copy_rows(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    table: str,
    query: str,
    params: tuple[object, ...],
) -> int:
    rows = [dict(row) for row in src.execute(query, params).fetchall()]
    if not rows:
        return 0

    columns = list(rows[0].keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    dst.executemany(
        f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        rows,
    )
    return len(rows)


def main() -> int:
    args = _parse_args()
    source_db = Path(args.source_db).resolve()
    output_db = Path(args.output_db).resolve()

    if not source_db.exists():
        print(f"source db does not exist: {source_db}", file=sys.stderr)
        return 2

    output_db.parent.mkdir(parents=True, exist_ok=True)
    if output_db.exists():
        output_db.unlink()

    src = connect(source_db)
    dst = connect(output_db)
    try:
        init_db(dst)

        copied: dict[str, int] = {}

        copied["property_locations_prod"] = _copy_rows(
            src,
            dst,
            "property_locations_prod",
            "SELECT * FROM property_locations_prod ORDER BY canonical_location_id LIMIT ?",
            (args.property_limit,),
        )

        copied["assessments_prod"] = _copy_rows(
            src,
            dst,
            "assessments_prod",
            """
            SELECT a.*
            FROM assessments_prod a
            JOIN property_locations_prod p ON p.canonical_location_id = a.canonical_location_id
            ORDER BY a.canonical_location_id
            LIMIT ?
            """,
            (args.property_limit,),
        )

        copied["assessments_records_prod"] = _copy_rows(
            src,
            dst,
            "assessments_records_prod",
            """
            SELECT r.*
            FROM assessments_records_prod r
            JOIN property_locations_prod p ON p.canonical_location_id = r.canonical_location_id
            ORDER BY r.canonical_location_id, r.record_id, r.source_id
            LIMIT ?
            """,
            (max(args.property_limit * 3, args.property_limit),),
        )

        copied["poi_prod"] = _copy_rows(
            src,
            dst,
            "poi_prod",
            "SELECT * FROM poi_prod ORDER BY canonical_poi_id LIMIT ?",
            (args.poi_limit,),
        )

        copied["poi_types"] = _copy_rows(
            src,
            dst,
            "poi_types",
            """
            SELECT DISTINCT t.*
            FROM poi_types t
            JOIN poi_standardized_prod s ON s.poi_type_id = t.poi_type_id
            JOIN (
                SELECT value AS source_entity_ref
                FROM poi_prod, json_each(poi_prod.source_entity_ids_json)
                ORDER BY poi_prod.canonical_poi_id
                LIMIT ?
            ) refs
              ON refs.source_entity_ref = s.source_id || ':' || s.poi_id
            ORDER BY t.poi_type_id
            """,
            (args.poi_limit,),
        )

        copied["poi_standardized_prod"] = _copy_rows(
            src,
            dst,
            "poi_standardized_prod",
            """
            SELECT s.*
            FROM poi_standardized_prod s
            JOIN (
                SELECT value AS source_entity_ref
                FROM poi_prod, json_each(poi_prod.source_entity_ids_json)
                ORDER BY poi_prod.canonical_poi_id
                LIMIT ?
            ) refs
              ON refs.source_entity_ref = s.source_id || ':' || s.poi_id
            ORDER BY s.source_id, s.poi_id
            """,
            (args.poi_limit,),
        )

        copied["geospatial_prod"] = _copy_rows(
            src,
            dst,
            "geospatial_prod",
            """
            SELECT g.*
            FROM geospatial_prod g
            JOIN (
                SELECT value AS source_entity_ref
                FROM poi_prod, json_each(poi_prod.source_entity_ids_json)
                ORDER BY poi_prod.canonical_poi_id
                LIMIT ?
            ) refs
              ON refs.source_entity_ref = g.source_id || ':' || g.entity_id
            WHERE g.dataset_type = 'pois'
            ORDER BY g.source_id, g.entity_id
            """,
            (args.poi_limit,),
        )

        dst.commit()
    finally:
        src.close()
        dst.close()

    print("sample db created")
    print(f"source_db: {source_db}")
    print(f"output_db: {output_db}")
    for table in PROPERTY_TABLES + POI_TABLES:
        print(f"{table}: {copied.get(table, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
