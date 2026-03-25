#!/usr/bin/env python3
"""Initialize a database and auto-ingest recognized local open-data files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_sourcing.config import DEFAULT_DB_PATH  # noqa: E402
from data_sourcing.service import IngestionService  # noqa: E402
from ingest_data_folder import discover_sources  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a DB and auto-ingest discovered open-data files")
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "src" / "data_sourcing" / "data"),
        help="Directory that contains downloaded datasets",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be ingested")
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


def main() -> int:
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
                    "db": str(args.db),
                    "data_dir": str(data_dir),
                    "planned_sources": plan_payload,
                    "notes": notes,
                },
                indent=2,
            )
        )
        return 0

    init_result = service.init_database()
    runs: list[dict[str, Any]] = []
    overall_failed = False

    for item in planned:
        result = service.ingest(
            source_keys=[item.source_key],
            source_overrides={item.source_key: str(item.file_path)},
            trigger="manual",
        )
        runs.append(
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

    status = "failed" if overall_failed else "succeeded"
    print(
        json.dumps(
            {
                "status": status,
                "db": str(args.db),
                "data_dir": str(data_dir),
                "init_db": init_result,
                "planned_sources": plan_payload,
                "notes": notes,
                "runs": runs,
            },
            indent=2,
        )
    )
    return 1 if overall_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
