"""Source adapters for observed and permit-derived bed/bath enrichment."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .database import rows_to_dicts
from .address_normalization import parse_address_components


LISTING_FIELD_ALIASES = {
    "address": ["address", "full_address", "property_address"],
    "suite": ["suite", "unit", "unit_number", "suite_number"],
    "house_number": ["house_number", "street_number", "civic_number"],
    "street_name": ["street_name", "street", "street_address"],
    "legal_description": ["legal_description", "legal", "legal_desc"],
    "lat": ["lat", "latitude"],
    "lon": ["lon", "lng", "longitude"],
    "bedrooms": ["bedrooms", "beds", "bedroom_count"],
    "bathrooms": ["bathrooms", "baths", "bathroom_count"],
    "source_record_id": ["source_record_id", "record_id", "listing_id", "id"],
    "observed_at": ["observed_at", "listed_at", "updated_at"],
}

PERMIT_FIELD_ALIASES = {
    "address": ["address", "full_address", "property_address"],
    "suite": ["suite", "unit", "unit_number", "suite_number"],
    "house_number": ["house_number", "street_number", "civic_number"],
    "street_name": ["street_name", "street", "street_address"],
    "legal_description": ["legal_description", "legal", "legal_desc"],
    "lat": ["lat", "latitude"],
    "lon": ["lon", "lng", "longitude"],
    "permit_description": ["permit_description", "description", "permit_text", "work_description"],
    "source_record_id": ["source_record_id", "record_id", "permit_id", "id"],
    "observed_at": ["observed_at", "issued_at", "updated_at"],
}


def _load_mapping(path: str | Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object mapping at {path}")
    return {str(key): str(value) for key, value in payload.items()}


def _load_records(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    source_path = Path(path)
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload]
        if isinstance(payload, dict):
            records = payload.get("records", [])
            return [dict(item) for item in records]
        raise ValueError(f"Unsupported JSON payload at {path}")
    if suffix == ".csv":
        with source_path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError(f"Unsupported file type for {path}")


def _normalize_record(
    row: dict[str, Any],
    aliases: dict[str, list[str]],
    field_map: dict[str, str],
    *,
    source_name: str,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {"source_name": source_name}
    lower_row = {str(key).lower(): value for key, value in row.items()}

    for canonical_field, fallback_aliases in aliases.items():
        source_field = field_map.get(canonical_field)
        candidates = [source_field] if source_field else []
        candidates.extend(fallback_aliases)
        value = None
        for candidate in candidates:
            if candidate is None:
                continue
            looked_up = lower_row.get(candidate.lower())
            if looked_up not in (None, ""):
                value = looked_up
                break
        normalized[canonical_field] = value

    parsed = parse_address_components(normalized.get("address"))
    normalized["suite"] = normalized.get("suite") or parsed.get("suite")
    normalized["house_number"] = normalized.get("house_number") or parsed.get("house_number")
    normalized["street_name"] = normalized.get("street_name") or parsed.get("street_name")
    normalized["source_record_id"] = normalized.get("source_record_id") or row.get("id")
    normalized["raw_payload_json"] = dict(row)
    return normalized


class SourceClients:
    """Container for the trusted record sources used by the enrichment workflow."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        listing_records: Iterable[dict[str, Any]] | None = None,
        listing_json_path: str | Path | None = None,
        listing_field_map_path: str | Path | None = None,
        permit_records: Iterable[dict[str, Any]] | None = None,
        permit_json_path: str | Path | None = None,
        permit_field_map_path: str | Path | None = None,
    ) -> None:
        self.conn = conn
        listing_map = _load_mapping(listing_field_map_path)
        permit_map = _load_mapping(permit_field_map_path)
        raw_listing_records = [dict(row) for row in listing_records or []] + _load_records(listing_json_path)
        raw_permit_records = [dict(row) for row in permit_records or []] + _load_records(permit_json_path)
        self._listing_records = [
            _normalize_record(row, LISTING_FIELD_ALIASES, listing_map, source_name="listing_file")
            for row in raw_listing_records
        ]
        self._permit_records = [
            _normalize_record(row, PERMIT_FIELD_ALIASES, permit_map, source_name="permit_file")
            for row in raw_permit_records
        ]

    def load_listing_candidates(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._listing_records]

    def load_prior_observed_candidates(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT pa.*, pl.suite, pl.house_number, pl.street_name, pl.legal_description,
                   pl.lat, pl.lon, pl.neighbourhood, pl.zoning, pl.total_gross_area, pl.year_built
            FROM property_attributes_prod pa
            JOIN property_locations_prod pl ON pl.canonical_location_id = pa.canonical_location_id
            WHERE pa.source_type = 'observed'
              AND pa.quarantined = 0
              AND (pa.bedrooms IS NOT NULL OR pa.bathrooms IS NOT NULL)
            """
        ).fetchall()
        return rows_to_dicts(rows)

    def load_permit_candidates(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._permit_records]
