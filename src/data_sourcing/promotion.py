"""Promotion rules for property attribute staging to prod."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .database import transaction, utc_now


PRECEDENCE_ORDER = {
    "observed_exact": 400,
    "observed_fuzzy": 300,
    "inferred_permit": 200,
    "imputed_model": 100,
}


def precedence_key(row: dict[str, Any]) -> tuple[float, float]:
    source_type = row.get("source_type")
    match_method = row.get("match_method") or ""
    if source_type == "observed" and match_method == "exact_address_suite":
        rank = PRECEDENCE_ORDER["observed_exact"]
    elif source_type == "observed":
        rank = PRECEDENCE_ORDER["observed_fuzzy"]
    elif source_type == "inferred":
        rank = PRECEDENCE_ORDER["inferred_permit"]
    else:
        rank = PRECEDENCE_ORDER["imputed_model"]
    return (float(rank), float(row.get("confidence") or 0.0))


def choose_preferred_record(existing: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        merged = dict(candidate)
        merged.setdefault("updated_at", utc_now())
        return merged

    existing_observed = existing.get("source_type") == "observed"
    candidate_observed = candidate.get("source_type") == "observed"

    if existing_observed and not candidate_observed:
        merged = dict(existing)
        if merged.get("bedrooms_estimated") is None and candidate.get("bedrooms_estimated") is not None:
            merged["bedrooms_estimated"] = candidate.get("bedrooms_estimated")
        if merged.get("bathrooms_estimated") is None and candidate.get("bathrooms_estimated") is not None:
            merged["bathrooms_estimated"] = candidate.get("bathrooms_estimated")
        merged["updated_at"] = candidate.get("updated_at", utc_now())
        return merged

    if precedence_key(candidate) < precedence_key(existing):
        merged = dict(existing)
        if merged.get("bedrooms_estimated") is None and candidate.get("bedrooms_estimated") is not None:
            merged["bedrooms_estimated"] = candidate.get("bedrooms_estimated")
        if merged.get("bathrooms_estimated") is None and candidate.get("bathrooms_estimated") is not None:
            merged["bathrooms_estimated"] = candidate.get("bathrooms_estimated")
        merged["updated_at"] = candidate.get("updated_at", utc_now())
        return merged

    merged = dict(existing)
    merged.update(candidate)
    if candidate.get("source_type") != "imputed":
        merged["bedrooms_estimated"] = existing.get("bedrooms_estimated")
        merged["bathrooms_estimated"] = existing.get("bathrooms_estimated")
    merged["updated_at"] = candidate.get("updated_at", utc_now())
    return merged


def upsert_staging_rows(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO property_attributes_staging (
            run_id, canonical_location_id, bedrooms, bathrooms, bedrooms_estimated,
            bathrooms_estimated, source_type, source_name, source_record_id, observed_at,
            confidence, match_method, ambiguous, quarantined, reason_code,
            feature_snapshot_json, raw_payload_json, updated_at
        ) VALUES (
            :run_id, :canonical_location_id, :bedrooms, :bathrooms, :bedrooms_estimated,
            :bathrooms_estimated, :source_type, :source_name, :source_record_id, :observed_at,
            :confidence, :match_method, :ambiguous, :quarantined, :reason_code,
            :feature_snapshot_json, :raw_payload_json, :updated_at
        )
        ON CONFLICT(run_id, canonical_location_id) DO UPDATE SET
            bedrooms=excluded.bedrooms,
            bathrooms=excluded.bathrooms,
            bedrooms_estimated=excluded.bedrooms_estimated,
            bathrooms_estimated=excluded.bathrooms_estimated,
            source_type=excluded.source_type,
            source_name=excluded.source_name,
            source_record_id=excluded.source_record_id,
            observed_at=excluded.observed_at,
            confidence=excluded.confidence,
            match_method=excluded.match_method,
            ambiguous=excluded.ambiguous,
            quarantined=excluded.quarantined,
            reason_code=excluded.reason_code,
            feature_snapshot_json=excluded.feature_snapshot_json,
            raw_payload_json=excluded.raw_payload_json,
            updated_at=excluded.updated_at
        """,
        rows,
    )


def promote_run(conn: sqlite3.Connection, run_id: str, *, target_table: str = "property_attributes_prod") -> dict[str, Any]:
    staging_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT *
            FROM property_attributes_staging
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchall()
    ]
    existing_rows = {
        row["canonical_location_id"]: dict(row)
        for row in conn.execute(f"SELECT * FROM {target_table}").fetchall()
    }

    merged_rows: list[dict[str, Any]] = []
    promoted = 0
    with transaction(conn):
        for row in staging_rows:
            existing = existing_rows.get(row["canonical_location_id"])
            merged = choose_preferred_record(existing, row)
            if merged != existing:
                promoted += 1
            merged_rows.append(_jsonify_row(merged))

        _upsert_target_rows(conn, target_table, merged_rows)
    return {"promoted_records": promoted, "staging_records": len(staging_rows), "target_table": target_table}


def _upsert_target_rows(conn: sqlite3.Connection, target_table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    conn.executemany(
        f"""
        INSERT INTO {target_table} (
            canonical_location_id, bedrooms, bathrooms, bedrooms_estimated,
            bathrooms_estimated, source_type, source_name, source_record_id,
            observed_at, confidence, match_method, ambiguous, quarantined,
            reason_code, feature_snapshot_json, raw_payload_json, updated_at
        ) VALUES (
            :canonical_location_id, :bedrooms, :bathrooms, :bedrooms_estimated,
            :bathrooms_estimated, :source_type, :source_name, :source_record_id,
            :observed_at, :confidence, :match_method, :ambiguous, :quarantined,
            :reason_code, :feature_snapshot_json, :raw_payload_json, :updated_at
        )
        ON CONFLICT(canonical_location_id) DO UPDATE SET
            bedrooms=excluded.bedrooms,
            bathrooms=excluded.bathrooms,
            bedrooms_estimated=excluded.bedrooms_estimated,
            bathrooms_estimated=excluded.bathrooms_estimated,
            source_type=excluded.source_type,
            source_name=excluded.source_name,
            source_record_id=excluded.source_record_id,
            observed_at=excluded.observed_at,
            confidence=excluded.confidence,
            match_method=excluded.match_method,
            ambiguous=excluded.ambiguous,
            quarantined=excluded.quarantined,
            reason_code=excluded.reason_code,
            feature_snapshot_json=excluded.feature_snapshot_json,
            raw_payload_json=excluded.raw_payload_json,
            updated_at=excluded.updated_at
        """,
        rows,
    )


def _jsonify_row(row: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(row)
    for column in ("feature_snapshot_json", "raw_payload_json"):
        value = prepared.get(column, {})
        if isinstance(value, str):
            continue
        prepared[column] = json.dumps(value)
    prepared.setdefault("updated_at", utc_now())
    return prepared
