"""Reporting utilities for bed/bath enrichment workflow runs."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

REVIEW_EXPORT_FIELDS = [
    "canonical_location_id",
    "source_record_id",
    "source_type",
    "source_name",
    "match_method",
    "reason_code",
    "confidence",
    "normalized_address",
    "raw_source_address",
    "suite",
    "house_number",
    "street_name",
    "legal_description",
    "lat",
    "lon",
]


def build_report(
    staging_rows: list[dict[str, Any]],
    candidate_count: int,
    *,
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_breakdown = Counter(row.get("source_type", "unknown") for row in staging_rows)
    confidence_distribution = {
        "high": sum(1 for row in staging_rows if float(row.get("confidence") or 0.0) >= 0.9),
        "medium": sum(1 for row in staging_rows if 0.75 <= float(row.get("confidence") or 0.0) < 0.9),
        "low": sum(1 for row in staging_rows if float(row.get("confidence") or 0.0) < 0.75),
    }
    observed_count = sum(1 for row in staging_rows if row.get("source_type") == "observed")
    inferred_count = sum(1 for row in staging_rows if row.get("source_type") == "inferred")
    imputed_count = sum(1 for row in staging_rows if row.get("source_type") == "imputed")
    ambiguous_count = sum(1 for row in staging_rows if row.get("ambiguous"))
    quarantined_count = sum(1 for row in staging_rows if row.get("quarantined"))
    confidence_buckets = build_confidence_buckets(staging_rows)

    report = {
        "total_candidate_properties": candidate_count,
        "filled_from_observed_values": observed_count,
        "filled_from_inferred_permit_values": inferred_count,
        "filled_from_imputation": imputed_count,
        "remaining_nulls": max(candidate_count - len(staging_rows), 0),
        "ambiguity_count": ambiguous_count,
        "quarantine_count": quarantined_count,
        "source_breakdown": dict(source_breakdown),
        "confidence_distribution": confidence_distribution,
        "confidence_buckets": confidence_buckets,
    }
    if diagnostics:
        report.update(diagnostics)
    return report


def build_confidence_buckets(staging_rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "observed_exact": sum(
            1
            for row in staging_rows
            if row.get("source_type") == "observed"
            and row.get("match_method") in {"exact_address_suite", "exact_legal_description"}
        ),
        "observed_fuzzy": sum(
            1
            for row in staging_rows
            if row.get("source_type") == "observed" and row.get("match_method") == "fuzzy_address_geo"
        ),
        "inferred_permit": sum(1 for row in staging_rows if row.get("source_type") == "inferred"),
        "imputed_high_confidence": sum(
            1
            for row in staging_rows
            if row.get("source_type") == "imputed" and float(row.get("confidence") or 0.0) >= 0.9
        ),
        "imputed_medium_confidence": sum(
            1
            for row in staging_rows
            if row.get("source_type") == "imputed" and 0.75 <= float(row.get("confidence") or 0.0) < 0.9
        ),
        "imputed_low_confidence": sum(
            1
            for row in staging_rows
            if row.get("source_type") == "imputed" and float(row.get("confidence") or 0.0) < 0.75
        ),
    }


def export_rows_csv(
    rows: list[dict[str, Any]],
    output_path: str | Path,
    *,
    fields: list[str] | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    selected_fields = fields or REVIEW_EXPORT_FIELDS
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=selected_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in selected_fields})
    return output


def export_ambiguous_csv(staging_rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    return export_rows_csv(
        [row for row in staging_rows if row.get("ambiguous") or row.get("quarantined")],
        output_path,
        fields=REVIEW_EXPORT_FIELDS,
    )
