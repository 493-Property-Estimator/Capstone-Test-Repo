"""CLI wrapper to run source-driven ingestion flows."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .config import DEFAULT_DB_PATH
from .enrich_bedbath import EnrichmentConfig, run_bedbath_enrichment
from .service import IngestionService


def _parse_source_overrides(raw_values: list[str] | None) -> dict[str, str]:
    overrides: dict[str, str] = {}
    if not raw_values:
        return overrides
    for raw in raw_values:
        if "=" not in raw:
            raise ValueError(f"invalid --source value '{raw}', expected key=value")
        key, value = raw.split("=", 1)
        overrides[key.strip()] = value.strip()
    return overrides


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Source-driven data ingestion pipelines")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Initialize database schema")
    init_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest sources and auto-select processing pipelines")
    ingest_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    ingest_parser.add_argument("--trigger", default="manual", help="manual|scheduled|on_demand")
    ingest_parser.add_argument("--source-key", action="append", help="Source key to ingest (repeatable). If omitted, ingests all configured sources.")
    ingest_parser.add_argument("--source", action="append", help="Override source location: source.key=/path/or/url")
    ingest_parser.add_argument("--taxonomy-version", default="v1")
    ingest_parser.add_argument("--mapping-version", default="v1")

    refresh_parser = subparsers.add_parser("run-refresh", help="Run scheduled/on-demand refresh workflow")
    refresh_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    refresh_parser.add_argument("--trigger", default="on_demand", help="scheduled|on_demand")
    refresh_parser.add_argument("--source", action="append", help="Override source location: source.key=/path/or/url")

    list_parser = subparsers.add_parser("list-sources", help="List configured ingestion sources")
    list_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    list_parser.add_argument("--pipeline", choices=["geospatial", "transit", "census", "assessments", "poi_standardization", "deduplication"])
    list_parser.add_argument("--enabled-only", action="store_true", help="Show only enabled sources")

    show_parser = subparsers.add_parser("show-source", help="Show one source config")
    show_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    show_parser.add_argument("--key", required=True)

    db_summary_parser = subparsers.add_parser("db-summary", help="Show DB schema and row counts")
    db_summary_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")

    db_path_parser = subparsers.add_parser("db-path", help="Show the active SQLite DB path")
    db_path_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")

    bedbath_parser = subparsers.add_parser(
        "ingest-bedbath",
        help="Ingest listing/permit records for bed/bath enrichment and optionally backfill property location fields",
    )
    bedbath_parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path")
    bedbath_parser.add_argument("--trigger", default="on_demand", help="manual|scheduled|on_demand")
    bedbath_parser.add_argument("--listings-json", help="Optional JSON file containing listing/API records.")
    bedbath_parser.add_argument("--listings-csv", help="Optional CSV file containing listing/API records.")
    bedbath_parser.add_argument("--listings-map", help="Optional JSON field map for listing records.")
    bedbath_parser.add_argument("--permits-json", help="Optional JSON file containing permit text records.")
    bedbath_parser.add_argument("--permits-csv", help="Optional CSV file containing permit text records.")
    bedbath_parser.add_argument("--permits-map", help="Optional JSON field map for permit records.")
    bedbath_parser.add_argument("--ambiguous-csv", default="reports/bedbath_ambiguous_matches.csv")
    bedbath_parser.add_argument("--review-export-dir", default="reports/bedbath_review_exports")
    bedbath_parser.add_argument("--min-training-rows", type=int, default=25)
    bedbath_parser.add_argument("--shadow-mode", action="store_true", help="Run in review-only shadow mode.")
    bedbath_parser.add_argument("--disable-promotion", action="store_true", help="Do not promote staging rows to prod.")
    bedbath_parser.add_argument("--shadow-table-name", help="Optional isolated table for shadow promotion output.")
    bedbath_parser.add_argument(
        "--backfill-location-fields",
        action="store_true",
        help="Backfill matched property_locations_prod rows with suite/house/street/lat/lon from observed listings.",
    )
    bedbath_parser.add_argument(
        "--overwrite-location-fields",
        action="store_true",
        help="When backfilling, overwrite existing non-null location fields instead of only filling missing values.",
    )

    return parser


def _format_column(column: dict[str, Any]) -> str:
    parts = [column["name"]]
    if column["type"]:
        parts.append(column["type"])
    if column["primary_key_position"]:
        parts.append("PK")
    if column["not_null"]:
        parts.append("NOT NULL")
    return " ".join(parts)


def _format_db_summary(summary: dict[str, Any]) -> str:
    table_count = len(summary["tables"])
    lines = [
        f"Database: {summary['db']}",
        f"Tables: {table_count}",
        "",
    ]
    for table in summary["tables"]:
        row_label = "row" if table["row_count"] == 1 else "rows"
        lines.append(f"{table['table']}")
        lines.append(f"  Rows: {table['row_count']} {row_label}")
        lines.append("  Columns:")
        for column in table["columns"]:
            lines.append(f"    - {_format_column(column)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    service = IngestionService(db_path=args.db)

    if args.command == "init-db":
        out: Any = service.init_database()
    elif args.command == "ingest":
        out = service.ingest(
            source_keys=args.source_key,
            trigger=args.trigger,
            source_overrides=_parse_source_overrides(args.source),
            taxonomy_version=args.taxonomy_version,
            mapping_version=args.mapping_version,
        )
    elif args.command == "run-refresh":
        out = service.run_refresh(trigger=args.trigger, source_overrides=_parse_source_overrides(args.source))
    elif args.command == "list-sources":
        out = service.list_sources(pipeline=args.pipeline, enabled_only=args.enabled_only)
    elif args.command == "show-source":
        out = service.get_source(args.key)
    elif args.command == "db-summary":
        out = service.database_summary()
    elif args.command == "db-path":
        out = service.database_path()
    elif args.command == "ingest-bedbath":
        promotion_target = "prod"
        if args.shadow_table_name:
            promotion_target = "shadow"
        if args.disable_promotion or (args.shadow_mode and not args.shadow_table_name):
            promotion_target = "disabled"
        out = run_bedbath_enrichment(
            args.db,
            trigger=args.trigger,
            listing_json_path=args.listings_json or args.listings_csv,
            permit_json_path=args.permits_json or args.permits_csv,
            listing_field_map_path=args.listings_map,
            permit_field_map_path=args.permits_map,
            config=EnrichmentConfig(
                ambiguous_export_path=args.ambiguous_csv,
                review_export_dir=args.review_export_dir,
                min_training_rows=args.min_training_rows,
                shadow_mode=args.shadow_mode,
                promotion_target=promotion_target,
                shadow_table_name=args.shadow_table_name or "property_attributes_shadow",
                backfill_property_locations_from_observed=args.backfill_location_fields,
                backfill_overwrite_existing_values=args.overwrite_location_fields,
            ),
        )
    else:
        raise ValueError(f"unsupported command: {args.command}")

    if args.command == "db-summary":
        print(_format_db_summary(out))
    else:
        print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
