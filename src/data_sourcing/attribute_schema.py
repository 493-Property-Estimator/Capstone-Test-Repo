"""Schema migration helpers for bedroom/bathroom enrichment datasets."""

from __future__ import annotations

import sqlite3


ATTRIBUTE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS property_attributes_staging (
    run_id TEXT NOT NULL,
    canonical_location_id TEXT NOT NULL,
    bedrooms INTEGER,
    bathrooms REAL,
    bedrooms_estimated INTEGER,
    bathrooms_estimated REAL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_record_id TEXT,
    observed_at TEXT,
    confidence REAL,
    match_method TEXT,
    ambiguous INTEGER NOT NULL DEFAULT 0,
    quarantined INTEGER NOT NULL DEFAULT 0,
    reason_code TEXT,
    feature_snapshot_json TEXT NOT NULL DEFAULT '{}',
    raw_payload_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (run_id, canonical_location_id),
    FOREIGN KEY (canonical_location_id) REFERENCES property_locations_prod (canonical_location_id)
);

CREATE TABLE IF NOT EXISTS property_attributes_prod (
    canonical_location_id TEXT PRIMARY KEY,
    bedrooms INTEGER,
    bathrooms REAL,
    bedrooms_estimated INTEGER,
    bathrooms_estimated REAL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_record_id TEXT,
    observed_at TEXT,
    confidence REAL,
    match_method TEXT,
    ambiguous INTEGER NOT NULL DEFAULT 0,
    quarantined INTEGER NOT NULL DEFAULT 0,
    reason_code TEXT,
    feature_snapshot_json TEXT NOT NULL DEFAULT '{}',
    raw_payload_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    FOREIGN KEY (canonical_location_id) REFERENCES property_locations_prod (canonical_location_id)
);

CREATE TABLE IF NOT EXISTS property_attributes_shadow (
    canonical_location_id TEXT PRIMARY KEY,
    bedrooms INTEGER,
    bathrooms REAL,
    bedrooms_estimated INTEGER,
    bathrooms_estimated REAL,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_record_id TEXT,
    observed_at TEXT,
    confidence REAL,
    match_method TEXT,
    ambiguous INTEGER NOT NULL DEFAULT 0,
    quarantined INTEGER NOT NULL DEFAULT 0,
    reason_code TEXT,
    feature_snapshot_json TEXT NOT NULL DEFAULT '{}',
    raw_payload_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    FOREIGN KEY (canonical_location_id) REFERENCES property_locations_prod (canonical_location_id)
);
"""

ATTRIBUTE_ALTER_STATEMENTS = (
    "ALTER TABLE property_attributes_staging ADD COLUMN bedrooms INTEGER",
    "ALTER TABLE property_attributes_staging ADD COLUMN bathrooms REAL",
    "ALTER TABLE property_attributes_staging ADD COLUMN bedrooms_estimated INTEGER",
    "ALTER TABLE property_attributes_staging ADD COLUMN bathrooms_estimated REAL",
    "ALTER TABLE property_attributes_staging ADD COLUMN source_type TEXT NOT NULL DEFAULT 'observed'",
    "ALTER TABLE property_attributes_staging ADD COLUMN source_name TEXT NOT NULL DEFAULT 'unknown'",
    "ALTER TABLE property_attributes_staging ADD COLUMN source_record_id TEXT",
    "ALTER TABLE property_attributes_staging ADD COLUMN observed_at TEXT",
    "ALTER TABLE property_attributes_staging ADD COLUMN confidence REAL",
    "ALTER TABLE property_attributes_staging ADD COLUMN match_method TEXT",
    "ALTER TABLE property_attributes_staging ADD COLUMN ambiguous INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE property_attributes_staging ADD COLUMN quarantined INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE property_attributes_staging ADD COLUMN reason_code TEXT",
    "ALTER TABLE property_attributes_staging ADD COLUMN feature_snapshot_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE property_attributes_staging ADD COLUMN raw_payload_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE property_attributes_staging ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE property_attributes_prod ADD COLUMN bedrooms INTEGER",
    "ALTER TABLE property_attributes_prod ADD COLUMN bathrooms REAL",
    "ALTER TABLE property_attributes_prod ADD COLUMN bedrooms_estimated INTEGER",
    "ALTER TABLE property_attributes_prod ADD COLUMN bathrooms_estimated REAL",
    "ALTER TABLE property_attributes_prod ADD COLUMN source_type TEXT NOT NULL DEFAULT 'observed'",
    "ALTER TABLE property_attributes_prod ADD COLUMN source_name TEXT NOT NULL DEFAULT 'unknown'",
    "ALTER TABLE property_attributes_prod ADD COLUMN source_record_id TEXT",
    "ALTER TABLE property_attributes_prod ADD COLUMN observed_at TEXT",
    "ALTER TABLE property_attributes_prod ADD COLUMN confidence REAL",
    "ALTER TABLE property_attributes_prod ADD COLUMN match_method TEXT",
    "ALTER TABLE property_attributes_prod ADD COLUMN ambiguous INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE property_attributes_prod ADD COLUMN quarantined INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE property_attributes_prod ADD COLUMN reason_code TEXT",
    "ALTER TABLE property_attributes_prod ADD COLUMN feature_snapshot_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE property_attributes_prod ADD COLUMN raw_payload_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE property_attributes_prod ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE property_attributes_shadow ADD COLUMN bedrooms INTEGER",
    "ALTER TABLE property_attributes_shadow ADD COLUMN bathrooms REAL",
    "ALTER TABLE property_attributes_shadow ADD COLUMN bedrooms_estimated INTEGER",
    "ALTER TABLE property_attributes_shadow ADD COLUMN bathrooms_estimated REAL",
    "ALTER TABLE property_attributes_shadow ADD COLUMN source_type TEXT NOT NULL DEFAULT 'observed'",
    "ALTER TABLE property_attributes_shadow ADD COLUMN source_name TEXT NOT NULL DEFAULT 'unknown'",
    "ALTER TABLE property_attributes_shadow ADD COLUMN source_record_id TEXT",
    "ALTER TABLE property_attributes_shadow ADD COLUMN observed_at TEXT",
    "ALTER TABLE property_attributes_shadow ADD COLUMN confidence REAL",
    "ALTER TABLE property_attributes_shadow ADD COLUMN match_method TEXT",
    "ALTER TABLE property_attributes_shadow ADD COLUMN ambiguous INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE property_attributes_shadow ADD COLUMN quarantined INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE property_attributes_shadow ADD COLUMN reason_code TEXT",
    "ALTER TABLE property_attributes_shadow ADD COLUMN feature_snapshot_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE property_attributes_shadow ADD COLUMN raw_payload_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE property_attributes_shadow ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
)


def apply_attribute_schema(conn: sqlite3.Connection) -> None:
    """Create or evolve the property attribute enrichment tables."""

    conn.executescript(ATTRIBUTE_TABLES_SQL)
    for statement in ATTRIBUTE_ALTER_STATEMENTS:
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass
    conn.commit()
