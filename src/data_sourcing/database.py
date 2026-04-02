"""SQLite schema and helper functions for ingestion workflows."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _quote_identifier(name: str) -> str:
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS run_logs (
            run_id TEXT PRIMARY KEY,
            story TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            errors_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS dataset_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_type TEXT NOT NULL,
            version_id TEXT NOT NULL,
            promoted_at TEXT NOT NULL,
            source_version TEXT,
            provenance TEXT,
            run_id TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS source_configs (
            source_key TEXT PRIMARY KEY,
            pipeline TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            city TEXT,
            dataset TEXT,
            ingestion_technique TEXT NOT NULL,
            local_path TEXT,
            remote_url TEXT,
            link_status TEXT,
            field_map_json TEXT NOT NULL DEFAULT '{}',
            downstream_json TEXT NOT NULL DEFAULT '[]',
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS source_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_group_id TEXT,
            source_key TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            resolved_location TEXT,
            checked_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS geospatial_staging (
            run_id TEXT NOT NULL,
            dataset_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            name TEXT NOT NULL,
            raw_category TEXT,
            canonical_geom_type TEXT NOT NULL,
            lon REAL NOT NULL,
            lat REAL NOT NULL,
            geometry_json TEXT NOT NULL DEFAULT '{}',
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (run_id, dataset_type, entity_id)
        );

        CREATE TABLE IF NOT EXISTS geospatial_prod (
            dataset_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            name TEXT NOT NULL,
            raw_category TEXT,
            canonical_geom_type TEXT NOT NULL,
            lon REAL NOT NULL,
            lat REAL NOT NULL,
            geometry_json TEXT NOT NULL DEFAULT '{}',
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (dataset_type, entity_id)
        );

        CREATE TABLE IF NOT EXISTS roads_staging (
            run_id TEXT NOT NULL,
            road_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            road_name TEXT NOT NULL,
            road_type TEXT,
            official_road_name TEXT,
            jurisdiction TEXT,
            functional_class TEXT,
            quadrant TEXT,
            source_version TEXT,
            updated_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (run_id, road_id, source_id)
        );

        CREATE TABLE IF NOT EXISTS roads_prod (
            road_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            road_name TEXT NOT NULL,
            road_type TEXT,
            official_road_name TEXT,
            jurisdiction TEXT,
            functional_class TEXT,
            quadrant TEXT,
            source_version TEXT,
            updated_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (road_id, source_id)
        );

        CREATE TABLE IF NOT EXISTS road_segments_staging (
            run_id TEXT NOT NULL,
            segment_id TEXT NOT NULL,
            road_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            sequence_no INTEGER,
            segment_name TEXT NOT NULL,
            segment_type TEXT,
            lane_count INTEGER,
            municipal_segment_id TEXT,
            official_road_name TEXT,
            roadway_category TEXT,
            surface_type TEXT,
            jurisdiction TEXT,
            functional_class TEXT,
            travel_direction TEXT,
            quadrant TEXT,
            from_intersection_id TEXT,
            to_intersection_id TEXT,
            start_lon REAL NOT NULL,
            start_lat REAL NOT NULL,
            end_lon REAL NOT NULL,
            end_lat REAL NOT NULL,
            center_lon REAL NOT NULL,
            center_lat REAL NOT NULL,
            length_m REAL,
            geometry_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (run_id, segment_id, source_id)
        );

        CREATE TABLE IF NOT EXISTS road_segments_prod (
            segment_id TEXT NOT NULL,
            road_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            sequence_no INTEGER,
            segment_name TEXT NOT NULL,
            segment_type TEXT,
            lane_count INTEGER,
            municipal_segment_id TEXT,
            official_road_name TEXT,
            roadway_category TEXT,
            surface_type TEXT,
            jurisdiction TEXT,
            functional_class TEXT,
            travel_direction TEXT,
            quadrant TEXT,
            from_intersection_id TEXT,
            to_intersection_id TEXT,
            start_lon REAL NOT NULL,
            start_lat REAL NOT NULL,
            end_lon REAL NOT NULL,
            end_lat REAL NOT NULL,
            center_lon REAL NOT NULL,
            center_lat REAL NOT NULL,
            length_m REAL,
            geometry_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (segment_id, source_id),
            FOREIGN KEY (road_id, source_id) REFERENCES roads_prod (road_id, source_id)
        );

        CREATE TABLE IF NOT EXISTS poi_types (
            poi_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_category TEXT NOT NULL,
            canonical_subcategory TEXT,
            display_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            UNIQUE (canonical_category, canonical_subcategory)
        );

        CREATE TABLE IF NOT EXISTS poi_staging (
            run_id TEXT NOT NULL,
            canonical_poi_id TEXT NOT NULL,
            name TEXT NOT NULL,
            raw_category TEXT,
            raw_subcategory TEXT,
            address TEXT,
            lon REAL,
            lat REAL,
            neighbourhood TEXT,
            source_dataset TEXT,
            source_provider TEXT,
            source_ids_json TEXT NOT NULL DEFAULT '[]',
            source_entity_ids_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (run_id, canonical_poi_id)
        );

        CREATE TABLE IF NOT EXISTS poi_prod (
            canonical_poi_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            raw_category TEXT,
            raw_subcategory TEXT,
            address TEXT,
            lon REAL,
            lat REAL,
            neighbourhood TEXT,
            source_dataset TEXT,
            source_provider TEXT,
            source_ids_json TEXT NOT NULL DEFAULT '[]',
            source_entity_ids_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            source_version TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS census_staging (
            run_id TEXT NOT NULL,
            area_id TEXT NOT NULL,
            geography_level TEXT NOT NULL,
            population INTEGER,
            households INTEGER,
            median_income REAL,
            area_sq_km REAL NOT NULL,
            population_density REAL,
            limited_accuracy INTEGER NOT NULL,
            PRIMARY KEY (run_id, area_id)
        );

        CREATE TABLE IF NOT EXISTS census_prod (
            area_id TEXT PRIMARY KEY,
            geography_level TEXT NOT NULL,
            population INTEGER,
            households INTEGER,
            median_income REAL,
            area_sq_km REAL NOT NULL,
            population_density REAL,
            limited_accuracy INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS crime_summary_staging (
            run_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            neighbourhood TEXT NOT NULL,
            crime_type TEXT NOT NULL,
            incident_count INTEGER,
            rate_per_100k REAL,
            year INTEGER,
            geography_level TEXT,
            raw_metric_name TEXT,
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (run_id, source_id, neighbourhood, crime_type, year)
        );

        CREATE TABLE IF NOT EXISTS crime_summary_prod (
            source_id TEXT NOT NULL,
            neighbourhood TEXT NOT NULL,
            crime_type TEXT NOT NULL,
            incident_count INTEGER,
            rate_per_100k REAL,
            year INTEGER,
            geography_level TEXT,
            raw_metric_name TEXT,
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (source_id, neighbourhood, crime_type, year)
        );

        CREATE TABLE IF NOT EXISTS assessments_staging (
            run_id TEXT NOT NULL,
            record_id TEXT NOT NULL,
            assessment_year INTEGER NOT NULL,
            canonical_location_id TEXT,
            assessment_value REAL,
            link_method TEXT NOT NULL,
            confidence REAL,
            ambiguous INTEGER NOT NULL,
            quarantined INTEGER NOT NULL,
            reason_code TEXT,
            PRIMARY KEY (run_id, record_id)
        );

        CREATE TABLE IF NOT EXISTS assessments_records_staging (
            run_id TEXT NOT NULL,
            record_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            assessment_year INTEGER NOT NULL,
            canonical_location_id TEXT,
            assessment_value REAL,
            suite TEXT,
            house_number TEXT,
            street_name TEXT,
            neighbourhood_id TEXT,
            neighbourhood TEXT,
            ward TEXT,
            tax_class TEXT,
            garage TEXT,
            assessment_class_1 TEXT,
            assessment_class_2 TEXT,
            assessment_class_3 TEXT,
            assessment_class_pct_1 REAL,
            assessment_class_pct_2 REAL,
            assessment_class_pct_3 REAL,
            lat REAL,
            lon REAL,
            point_location TEXT,
            link_method TEXT NOT NULL,
            confidence REAL,
            ambiguous INTEGER NOT NULL,
            quarantined INTEGER NOT NULL,
            reason_code TEXT,
            raw_record_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (run_id, record_id, source_id)
        );

        CREATE TABLE IF NOT EXISTS assessments_prod (
            canonical_location_id TEXT PRIMARY KEY,
            assessment_year INTEGER NOT NULL,
            assessment_value REAL NOT NULL,
            chosen_record_id TEXT NOT NULL,
            confidence REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS property_locations_staging (
            run_id TEXT NOT NULL,
            canonical_location_id TEXT NOT NULL,
            assessment_year INTEGER,
            assessment_value REAL,
            suite TEXT,
            house_number TEXT,
            street_name TEXT,
            legal_description TEXT,
            zoning TEXT,
            lot_size REAL,
            total_gross_area TEXT,
            year_built INTEGER,
            neighbourhood_id TEXT,
            neighbourhood TEXT,
            ward TEXT,
            tax_class TEXT,
            garage TEXT,
            assessment_class_1 TEXT,
            assessment_class_2 TEXT,
            assessment_class_3 TEXT,
            assessment_class_pct_1 REAL,
            assessment_class_pct_2 REAL,
            assessment_class_pct_3 REAL,
            lat REAL,
            lon REAL,
            point_location TEXT,
            source_ids_json TEXT NOT NULL DEFAULT '[]',
            record_ids_json TEXT NOT NULL DEFAULT '[]',
            link_method TEXT NOT NULL,
            confidence REAL,
            updated_at TEXT,
            PRIMARY KEY (run_id, canonical_location_id)
        );

        CREATE TABLE IF NOT EXISTS property_locations_prod (
            canonical_location_id TEXT PRIMARY KEY,
            assessment_year INTEGER,
            assessment_value REAL,
            suite TEXT,
            house_number TEXT,
            street_name TEXT,
            legal_description TEXT,
            zoning TEXT,
            lot_size REAL,
            total_gross_area TEXT,
            year_built INTEGER,
            neighbourhood_id TEXT,
            neighbourhood TEXT,
            ward TEXT,
            tax_class TEXT,
            garage TEXT,
            assessment_class_1 TEXT,
            assessment_class_2 TEXT,
            assessment_class_3 TEXT,
            assessment_class_pct_1 REAL,
            assessment_class_pct_2 REAL,
            assessment_class_pct_3 REAL,
            lat REAL,
            lon REAL,
            point_location TEXT,
            source_ids_json TEXT NOT NULL DEFAULT '[]',
            record_ids_json TEXT NOT NULL DEFAULT '[]',
            link_method TEXT NOT NULL,
            confidence REAL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS assessments_records_prod (
            record_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            assessment_year INTEGER NOT NULL,
            canonical_location_id TEXT,
            assessment_value REAL,
            suite TEXT,
            house_number TEXT,
            street_name TEXT,
            neighbourhood_id TEXT,
            neighbourhood TEXT,
            ward TEXT,
            tax_class TEXT,
            garage TEXT,
            assessment_class_1 TEXT,
            assessment_class_2 TEXT,
            assessment_class_3 TEXT,
            assessment_class_pct_1 REAL,
            assessment_class_pct_2 REAL,
            assessment_class_pct_3 REAL,
            lat REAL,
            lon REAL,
            point_location TEXT,
            link_method TEXT NOT NULL,
            confidence REAL,
            ambiguous INTEGER NOT NULL,
            quarantined INTEGER NOT NULL,
            reason_code TEXT,
            raw_record_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (record_id, source_id)
        );

        CREATE TABLE IF NOT EXISTS poi_standardized_staging (
            run_id TEXT NOT NULL,
            poi_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            poi_type_id INTEGER,
            canonical_category TEXT NOT NULL,
            canonical_subcategory TEXT,
            raw_category TEXT NOT NULL,
            mapping_rule_id TEXT NOT NULL,
            mapping_rationale TEXT NOT NULL,
            taxonomy_version TEXT NOT NULL,
            mapping_version TEXT NOT NULL,
            unmapped INTEGER NOT NULL,
            PRIMARY KEY (run_id, poi_id, source_id),
            FOREIGN KEY (poi_type_id) REFERENCES poi_types (poi_type_id)
        );

        CREATE TABLE IF NOT EXISTS poi_standardized_prod (
            poi_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            poi_type_id INTEGER,
            canonical_category TEXT NOT NULL,
            canonical_subcategory TEXT,
            raw_category TEXT NOT NULL,
            mapping_rule_id TEXT NOT NULL,
            mapping_rationale TEXT NOT NULL,
            taxonomy_version TEXT NOT NULL,
            mapping_version TEXT NOT NULL,
            unmapped INTEGER NOT NULL,
            PRIMARY KEY (poi_id, source_id),
            FOREIGN KEY (poi_type_id) REFERENCES poi_types (poi_type_id)
        );

        CREATE TABLE IF NOT EXISTS canonical_entities_staging (
            run_id TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            canonical_category TEXT NOT NULL,
            name TEXT NOT NULL,
            lon REAL,
            lat REAL,
            source_precedence TEXT NOT NULL,
            PRIMARY KEY (run_id, canonical_id)
        );

        CREATE TABLE IF NOT EXISTS canonical_links_staging (
            run_id TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            link_reason TEXT NOT NULL,
            PRIMARY KEY (run_id, canonical_id, source_id, entity_id)
        );

        CREATE TABLE IF NOT EXISTS canonical_entities_prod (
            canonical_id TEXT PRIMARY KEY,
            canonical_category TEXT NOT NULL,
            name TEXT NOT NULL,
            lon REAL,
            lat REAL,
            source_precedence TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS canonical_links_prod (
            canonical_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            link_reason TEXT NOT NULL,
            PRIMARY KEY (canonical_id, source_id, entity_id)
        );

        CREATE TABLE IF NOT EXISTS workflow_runs (
            run_id TEXT PRIMARY KEY,
            trigger_type TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            errors_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS workflow_steps (
            step_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            dataset_type TEXT NOT NULL,
            status TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            errors_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS workflow_summaries (
            run_id TEXT PRIMARY KEY,
            promoted_json TEXT NOT NULL,
            skipped_json TEXT NOT NULL,
            failed_json TEXT NOT NULL,
            reasons_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transit_staging (
            run_id TEXT NOT NULL,
            transit_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            name TEXT NOT NULL,
            route_id TEXT,
            service_id TEXT,
            trip_id TEXT,
            trip_headsign TEXT,
            direction_id INTEGER,
            block_id TEXT,
            shape_id TEXT,
            wheelchair_accessible TEXT,
            bikes_allowed TEXT,
            line_length REAL,
            stop_id TEXT,
            stop_code TEXT,
            stop_name TEXT,
            stop_desc TEXT,
            stop_lat REAL,
            stop_lon REAL,
            zone_id TEXT,
            stop_url TEXT,
            location_type INTEGER,
            parent_station TEXT,
            level_name TEXT,
            lon REAL,
            lat REAL,
            geometry_json TEXT NOT NULL DEFAULT '[]',
            raw_record_json TEXT NOT NULL DEFAULT '{}',
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (run_id, transit_type, entity_id, source_id)
        );

        CREATE TABLE IF NOT EXISTS transit_prod (
            transit_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            name TEXT NOT NULL,
            route_id TEXT,
            service_id TEXT,
            trip_id TEXT,
            trip_headsign TEXT,
            direction_id INTEGER,
            block_id TEXT,
            shape_id TEXT,
            wheelchair_accessible TEXT,
            bikes_allowed TEXT,
            line_length REAL,
            stop_id TEXT,
            stop_code TEXT,
            stop_name TEXT,
            stop_desc TEXT,
            stop_lat REAL,
            stop_lon REAL,
            zone_id TEXT,
            stop_url TEXT,
            location_type INTEGER,
            parent_station TEXT,
            level_name TEXT,
            lon REAL,
            lat REAL,
            geometry_json TEXT NOT NULL DEFAULT '[]',
            raw_record_json TEXT NOT NULL DEFAULT '{}',
            source_version TEXT,
            updated_at TEXT,
            PRIMARY KEY (transit_type, entity_id, source_id)
        );
        """
    )
    # Backward-compatible schema evolution for existing DB files.
    for statement in (
        "ALTER TABLE source_configs ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE source_configs ADD COLUMN field_map_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE geospatial_staging ADD COLUMN geometry_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE geospatial_prod ADD COLUMN geometry_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE poi_standardized_staging ADD COLUMN poi_type_id INTEGER",
        "ALTER TABLE poi_standardized_prod ADD COLUMN poi_type_id INTEGER",
        "ALTER TABLE poi_staging ADD COLUMN raw_subcategory TEXT",
        "ALTER TABLE poi_staging ADD COLUMN neighbourhood TEXT",
        "ALTER TABLE poi_staging ADD COLUMN source_dataset TEXT",
        "ALTER TABLE poi_staging ADD COLUMN source_provider TEXT",
        "ALTER TABLE poi_staging ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE poi_prod ADD COLUMN raw_subcategory TEXT",
        "ALTER TABLE poi_prod ADD COLUMN neighbourhood TEXT",
        "ALTER TABLE poi_prod ADD COLUMN source_dataset TEXT",
        "ALTER TABLE poi_prod ADD COLUMN source_provider TEXT",
        "ALTER TABLE poi_prod ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE assessments_records_staging ADD COLUMN legal_description TEXT",
        "ALTER TABLE assessments_records_staging ADD COLUMN zoning TEXT",
        "ALTER TABLE assessments_records_staging ADD COLUMN lot_size REAL",
        "ALTER TABLE assessments_records_staging ADD COLUMN total_gross_area TEXT",
        "ALTER TABLE assessments_records_staging ADD COLUMN year_built INTEGER",
        "ALTER TABLE assessments_records_prod ADD COLUMN legal_description TEXT",
        "ALTER TABLE assessments_records_prod ADD COLUMN zoning TEXT",
        "ALTER TABLE assessments_records_prod ADD COLUMN lot_size REAL",
        "ALTER TABLE assessments_records_prod ADD COLUMN total_gross_area TEXT",
        "ALTER TABLE assessments_records_prod ADD COLUMN year_built INTEGER",
        "ALTER TABLE roads_staging ADD COLUMN official_road_name TEXT",
        "ALTER TABLE roads_staging ADD COLUMN jurisdiction TEXT",
        "ALTER TABLE roads_staging ADD COLUMN functional_class TEXT",
        "ALTER TABLE roads_staging ADD COLUMN quadrant TEXT",
        "ALTER TABLE roads_prod ADD COLUMN official_road_name TEXT",
        "ALTER TABLE roads_prod ADD COLUMN jurisdiction TEXT",
        "ALTER TABLE roads_prod ADD COLUMN functional_class TEXT",
        "ALTER TABLE roads_prod ADD COLUMN quadrant TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN municipal_segment_id TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN official_road_name TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN roadway_category TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN surface_type TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN jurisdiction TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN functional_class TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN travel_direction TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN quadrant TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN from_intersection_id TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN to_intersection_id TEXT",
        "ALTER TABLE road_segments_staging ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE road_segments_prod ADD COLUMN municipal_segment_id TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN official_road_name TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN roadway_category TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN surface_type TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN jurisdiction TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN functional_class TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN travel_direction TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN quadrant TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN from_intersection_id TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN to_intersection_id TEXT",
        "ALTER TABLE road_segments_prod ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'",
    ):
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass
    conn.commit()


def inspect_db(conn: sqlite3.Connection) -> dict[str, Any]:
    tables = [
        row["name"]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
    ]

    summaries: list[dict[str, Any]] = []
    for table_name in tables:
        columns = [
            {
                "name": column["name"],
                "type": column["type"],
                "not_null": bool(column["notnull"]),
                "default": column["dflt_value"],
                "primary_key_position": column["pk"],
            }
            for column in conn.execute(f"PRAGMA table_info({_quote_identifier(table_name)})")
        ]
        row_count = conn.execute(
            f"SELECT COUNT(*) AS row_count FROM {_quote_identifier(table_name)}"
        ).fetchone()["row_count"]
        summaries.append(
            {
                "table": table_name,
                "row_count": row_count,
                "columns": columns,
            }
        )

    return {"tables": summaries}


@contextmanager
def transaction(conn: sqlite3.Connection):
    savepoint = f"sp_{datetime.now(UTC).strftime('%H%M%S%f')}"
    try:
        conn.execute(f"SAVEPOINT {savepoint}")
        yield
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
    except Exception:
        conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        raise


def upsert_run_log(
    conn: sqlite3.Connection,
    run_id: str,
    story: str,
    trigger_type: str,
    status: str,
    started_at: str,
    completed_at: str | None,
    warnings: list[str],
    errors: list[str],
    metadata: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO run_logs (
            run_id, story, trigger_type, status, started_at, completed_at,
            warnings_json, errors_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            status=excluded.status,
            completed_at=excluded.completed_at,
            warnings_json=excluded.warnings_json,
            errors_json=excluded.errors_json,
            metadata_json=excluded.metadata_json
        """,
        (
            run_id,
            story,
            trigger_type,
            status,
            started_at,
            completed_at,
            json.dumps(warnings),
            json.dumps(errors),
            json.dumps(metadata),
        ),
    )


def add_alert(conn: sqlite3.Connection, run_id: str | None, level: str, message: str) -> None:
    conn.execute(
        "INSERT INTO alerts (run_id, level, message, created_at) VALUES (?, ?, ?, ?)",
        (run_id, level, message, utc_now()),
    )


def record_dataset_version(
    conn: sqlite3.Connection,
    dataset_type: str,
    version_id: str,
    run_id: str,
    source_version: str | None = None,
    provenance: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO dataset_versions (dataset_type, version_id, promoted_at, source_version, provenance, run_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (dataset_type, version_id, utc_now(), source_version, provenance, run_id),
    )


def upsert_source_config(conn: sqlite3.Connection, source_key: str, spec: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO source_configs (
            source_key, pipeline, enabled, city, dataset, ingestion_technique, local_path, remote_url,
            link_status, field_map_json, downstream_json, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_key) DO UPDATE SET
            pipeline=excluded.pipeline,
            enabled=excluded.enabled,
            city=excluded.city,
            dataset=excluded.dataset,
            ingestion_technique=excluded.ingestion_technique,
            local_path=excluded.local_path,
            remote_url=excluded.remote_url,
            link_status=excluded.link_status,
            field_map_json=excluded.field_map_json,
            downstream_json=excluded.downstream_json,
            notes=excluded.notes,
            updated_at=excluded.updated_at
        """,
        (
            source_key,
            spec.get("pipeline", ""),
            1 if bool(spec.get("enabled", True)) else 0,
            spec.get("city"),
            spec.get("dataset"),
            spec.get("ingestion_technique", "local_json"),
            spec.get("local_path"),
            spec.get("remote_url"),
            spec.get("link_status"),
            json.dumps(spec.get("field_map", {})),
            json.dumps(spec.get("downstream_pipelines", [])),
            spec.get("ingestion_notes"),
            utc_now(),
        ),
    )


def log_source_check(
    conn: sqlite3.Connection,
    run_group_id: str | None,
    source_key: str,
    status: str,
    message: str | None,
    resolved_location: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO source_checks (run_group_id, source_key, status, message, resolved_location, checked_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (run_group_id, source_key, status, message, resolved_location, utc_now()),
    )


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
