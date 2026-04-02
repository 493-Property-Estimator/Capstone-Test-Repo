#!/usr/bin/env python3
"""Download and prepare official Edmonton crime summary data for ingestion."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_sourcing.service import IngestionService

DEFAULT_DOWNLOAD_URL = "https://www150.statcan.gc.ca/n1/tbl/csv/35100183-eng.zip"
DEFAULT_ZIP_PATH = ROOT / "src" / "data_sourcing" / "data" / "35100183-eng.zip"
DEFAULT_OUTPUT_CSV = (
    ROOT / "src" / "data_sourcing" / "data" / "StatsCan_Police_Service_Crime_Edmonton.csv"
)
DEFAULT_SOURCE_KEY = "crime.statscan_police_service"
DEFAULT_GEO_MATCH = "Edmonton, Alberta, municipal"
DEFAULT_STATS = ("Actual incidents", "Rate per 100,000 population")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the official StatsCan crime ZIP and prepare an Edmonton-only CSV."
    )
    parser.add_argument(
        "--download-url",
        default=DEFAULT_DOWNLOAD_URL,
        help="Official ZIP URL to download.",
    )
    parser.add_argument(
        "--zip-path",
        default=str(DEFAULT_ZIP_PATH),
        help="Where to save the downloaded ZIP.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Where to save the filtered Edmonton CSV.",
    )
    parser.add_argument(
        "--geo-match",
        default=DEFAULT_GEO_MATCH,
        help="Substring match used on the GEO column.",
    )
    parser.add_argument(
        "--stats",
        nargs="+",
        default=list(DEFAULT_STATS),
        help="Statistics values to keep from the StatsCan table.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse an existing ZIP instead of downloading it again.",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Run the crime ingest after preparing the filtered CSV.",
    )
    parser.add_argument(
        "--db",
        default=str(ROOT / "src" / "data_sourcing" / "open_data.db"),
        help="SQLite database path used when --ingest is supplied.",
    )
    return parser.parse_args()


def _download_zip(download_url: str, zip_path: Path) -> dict[str, object]:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        body = response.read()
    zip_path.write_bytes(body)
    return {
        "download_url": download_url,
        "zip_path": str(zip_path),
        "zip_size_bytes": len(body),
    }


def _find_csv_member(zip_path: Path) -> str:
    with zipfile.ZipFile(zip_path) as archive:
        csv_members = sorted(name for name in archive.namelist() if name.lower().endswith(".csv"))
    for member in csv_members:
        if "metadata" not in member.lower():
            return member
    if csv_members:
        return csv_members[0]
    raise FileNotFoundError(f"No CSV file was found inside {zip_path}")


def _prepare_edmonton_csv(
    zip_path: Path,
    output_csv: Path,
    *,
    geo_match: str,
    allowed_stats: set[str],
) -> dict[str, object]:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    csv_member = _find_csv_member(zip_path)

    kept_rows = 0
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(csv_member) as raw_csv:
            reader = csv.DictReader((line.decode("utf-8-sig") for line in raw_csv))
            fieldnames = reader.fieldnames
            if fieldnames is None:
                raise ValueError(f"CSV member {csv_member} did not contain a header row.")
            with output_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in reader:
                    if geo_match not in str(row.get("GEO", "")):
                        continue
                    if str(row.get("Statistics", "")) not in allowed_stats:
                        continue
                    writer.writerow(row)
                    kept_rows += 1

    return {
        "csv_member": csv_member,
        "output_csv": str(output_csv),
        "kept_rows": kept_rows,
    }


def _run_ingest(db_path: Path, output_csv: Path) -> dict[str, object]:
    service = IngestionService(db_path=db_path)
    service.init_database()
    return service.ingest(
        source_keys=[DEFAULT_SOURCE_KEY],
        source_overrides={DEFAULT_SOURCE_KEY: str(output_csv)},
        trigger="manual",
    )


def main() -> int:
    args = _parse_args()
    zip_path = Path(args.zip_path).resolve()
    output_csv = Path(args.output_csv).resolve()
    db_path = Path(args.db).resolve()

    summary: dict[str, object] = {
        "zip_path": str(zip_path),
        "output_csv": str(output_csv),
        "db_path": str(db_path),
    }

    if args.skip_download:
        if not zip_path.exists():
            print(
                json.dumps(
                    {
                        "status": "failed",
                        **summary,
                        "error": f"--skip-download was set but ZIP was not found: {zip_path}",
                    },
                    indent=2,
                )
            )
            return 2
        summary["download"] = {"skipped": True}
    else:
        summary["download"] = _download_zip(args.download_url, zip_path)

    summary["prepare"] = _prepare_edmonton_csv(
        zip_path,
        output_csv,
        geo_match=args.geo_match,
        allowed_stats=set(args.stats),
    )

    if args.ingest:
        summary["ingest"] = _run_ingest(db_path, output_csv)

    summary["status"] = "succeeded"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
