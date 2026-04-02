"""Bedroom and bathroom enrichment pipeline for Edmonton properties."""

from __future__ import annotations

import argparse
import json
import uuid
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .address_normalization import normalize_property_address
from .attribute_schema import apply_attribute_schema
from .bedbath_models import build_feature_snapshot, select_model, training_rows_from_candidates
from .database import (
    add_alert,
    connect,
    init_db,
    record_dataset_version,
    rows_to_dicts,
    upsert_run_log,
    utc_now,
)
from .permit_parser import parse_permit_record
from .promotion import choose_preferred_record, promote_run, upsert_staging_rows
from .property_matcher import choose_best_match
from .reporting import REVIEW_EXPORT_FIELDS, build_report, export_ambiguous_csv, export_rows_csv
from .source_clients import SourceClients


WORKFLOW_STEPS = [
    "schema migration",
    "candidate extraction",
    "observed matching",
    "permit parsing",
    "model training",
    "imputation",
    "promotion",
    "reporting",
]


@dataclass
class EnrichmentConfig:
    fuzzy_threshold: float = 0.90
    observed_min_confidence: float = 0.85
    imputation_min_confidence: float = 0.70
    training_min_confidence: float = 0.90
    min_training_rows: int = 25
    ambiguous_export_path: str = "reports/bedbath_ambiguous_matches.csv"
    review_export_dir: str = "reports/bedbath_review_exports"
    dataset_type: str = "property_attributes"
    shadow_mode: bool = False
    promotion_target: str = "prod"
    shadow_table_name: str = "property_attributes_shadow"


def _new_run_id(prefix: str = "bedbath") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def run_bedbath_enrichment(
    db_path: str | Path,
    *,
    trigger: str = "on_demand",
    listing_records: list[dict[str, Any]] | None = None,
    permit_records: list[dict[str, Any]] | None = None,
    listing_json_path: str | Path | None = None,
    permit_json_path: str | Path | None = None,
    listing_field_map_path: str | Path | None = None,
    permit_field_map_path: str | Path | None = None,
    config: EnrichmentConfig | None = None,
) -> dict[str, Any]:
    cfg = config or EnrichmentConfig()
    conn = connect(Path(db_path))
    init_db(conn)
    apply_attribute_schema(conn)
    run_id = _new_run_id()
    started_at = utc_now()
    _start_workflow_run(conn, run_id, trigger)
    upsert_run_log(conn, run_id, "bedbath_enrichment", trigger, "running", started_at, None, [], [], {})

    step_runs: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    report: dict[str, Any] = {}

    clients = SourceClients(
        conn,
        listing_records=listing_records,
        listing_json_path=listing_json_path,
        listing_field_map_path=listing_field_map_path,
        permit_records=permit_records,
        permit_json_path=permit_json_path,
        permit_field_map_path=permit_field_map_path,
    )

    try:
        _run_step(conn, run_id, "schema migration", step_runs, lambda: apply_attribute_schema(conn))
        candidate_rows = _run_step(conn, run_id, "candidate extraction", step_runs, lambda: extract_candidates(conn))
        observed_rows = _run_step(
            conn,
            run_id,
            "observed matching",
            step_runs,
            lambda: run_observed_matching(conn, run_id, candidate_rows, clients, cfg),
        )
        permit_rows = _run_step(
            conn,
            run_id,
            "permit parsing",
            step_runs,
            lambda: run_permit_inference(conn, run_id, candidate_rows, clients, cfg),
        )
        training_info = _run_step(
            conn,
            run_id,
            "model training",
            step_runs,
            lambda: train_models(conn, run_id, cfg),
        )
        imputed_rows = _run_step(
            conn,
            run_id,
            "imputation",
            step_runs,
            lambda: run_imputation(conn, run_id, candidate_rows, training_info, cfg),
        )
        promotion_result = _run_step(conn, run_id, "promotion", step_runs, lambda: promote_attributes(conn, run_id, cfg))
        report = _run_step(
            conn,
            run_id,
            "reporting",
            step_runs,
            lambda: generate_report(conn, run_id, candidate_rows, clients, cfg),
        )
        warnings.extend(_collect_alert_warnings(observed_rows + permit_rows + imputed_rows))
        if promotion_result.get("dataset_version_recorded"):
            record_dataset_version(
                conn,
                dataset_type=cfg.dataset_type,
                version_id=run_id,
                run_id=run_id,
                provenance=str(promotion_result["dataset_version_recorded"]),
            )
        _finish_workflow_run(conn, run_id, "succeeded", warnings, errors, promotion_result.get("promoted_datasets", []))
        upsert_run_log(
            conn,
            run_id,
            "bedbath_enrichment",
            trigger,
            "succeeded",
            started_at,
            utc_now(),
            warnings,
            errors,
            {
                "report": report,
                "promotion": promotion_result,
                "training": {
                    "model_version": training_info["model_version"],
                    "training_rows": training_info["training_rows"],
                    "imputation_enabled": training_info["imputation_enabled"],
                },
                "shadow_mode": cfg.shadow_mode,
            },
        )
        conn.commit()
        return {
            "run_id": run_id,
            "status": "succeeded",
            "step_runs": step_runs,
            "report": report,
            "promotion": promotion_result,
            "warnings": warnings,
            "errors": errors,
        }
    except Exception as exc:
        errors.append(str(exc))
        add_alert(conn, run_id, "error", str(exc))
        _finish_workflow_run(conn, run_id, "failed", warnings, errors, [])
        upsert_run_log(
            conn,
            run_id,
            "bedbath_enrichment",
            trigger,
            "failed",
            started_at,
            utc_now(),
            warnings,
            errors,
            {"report": report},
        )
        conn.commit()
        raise
    finally:
        conn.close()


def extract_candidates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT pl.*, ap.assessment_value AS assessment_value_override
        FROM property_locations_prod pl
        LEFT JOIN assessments_prod ap ON ap.canonical_location_id = pl.canonical_location_id
        """
    ).fetchall()
    candidates = rows_to_dicts(rows)
    for row in candidates:
        if row.get("assessment_value_override") is not None:
            row["assessment_value"] = row["assessment_value_override"]
        row["normalized_address"] = normalize_property_address(row).to_dict()
    base_address_counts = Counter(
        row["normalized_address"]["address_key_without_suite"]
        for row in candidates
        if row["normalized_address"].get("address_key_without_suite")
    )
    for row in candidates:
        base_key = row["normalized_address"].get("address_key_without_suite")
        row["multi_unit_group_size"] = int(base_address_counts.get(base_key, 0))
        row["is_multi_unit_group"] = int(base_address_counts.get(base_key, 0) > 1)
    return candidates


def run_observed_matching(
    conn: sqlite3.Connection,
    run_id: str,
    candidates: list[dict[str, Any]],
    clients: SourceClients,
    config: EnrichmentConfig,
) -> list[dict[str, Any]]:
    listing_candidates = clients.load_listing_candidates()
    historical_candidates = clients.load_prior_observed_candidates()
    staged_rows: list[dict[str, Any]] = []

    for property_row in candidates:
        source_priority = [
            ("listing_api", listing_candidates, "observed"),
            ("prior_observed_recovery", historical_candidates, "observed"),
        ]
        best: dict[str, Any] | None = None
        for source_name, records, source_type in source_priority:
            matched = choose_best_match(
                property_row,
                [record for record in records if record.get("bedrooms") is not None or record.get("bathrooms") is not None],
                fuzzy_threshold=config.fuzzy_threshold,
            )
            if matched is None or matched.confidence < config.observed_min_confidence:
                continue
            candidate = {
                "run_id": run_id,
                "canonical_location_id": property_row["canonical_location_id"],
                "bedrooms": _coerce_int(matched.matched_row.get("bedrooms")),
                "bathrooms": _coerce_float(matched.matched_row.get("bathrooms")),
                "bedrooms_estimated": None,
                "bathrooms_estimated": None,
                "source_type": source_type,
                "source_name": matched.matched_row.get("source_name") or source_name,
                "source_record_id": matched.source_record_id,
                "observed_at": matched.matched_row.get("observed_at") or utc_now(),
                "confidence": matched.confidence,
                "match_method": matched.match_method,
                "ambiguous": int(matched.ambiguous),
                "quarantined": int(matched.quarantined),
                "reason_code": matched.reason_code,
                "feature_snapshot_json": build_feature_snapshot(property_row),
                "raw_payload_json": matched.matched_row,
                "updated_at": utc_now(),
            }
            best = choose_preferred_record(best, candidate)
        if best is not None:
            staged_rows.append(_jsonify(best))
            if best["ambiguous"] or best["quarantined"]:
                add_alert(
                    conn,
                    run_id,
                    "warning",
                    f"ambiguous observed match for {best['canonical_location_id']}: {best.get('reason_code') or best['match_method']}",
                )

    staged_rows = _retain_best_source_assignments(staged_rows)
    upsert_staging_rows(conn, staged_rows)
    conn.commit()
    return staged_rows


def run_permit_inference(
    conn: sqlite3.Connection,
    run_id: str,
    candidates: list[dict[str, Any]],
    clients: SourceClients,
    config: EnrichmentConfig,
) -> list[dict[str, Any]]:
    permit_candidates = [parse_permit_record(record) for record in clients.load_permit_candidates()]
    permit_candidates = [record for record in permit_candidates if record is not None]
    staged_rows: list[dict[str, Any]] = []

    for property_row in candidates:
        existing = conn.execute(
            """
            SELECT *
            FROM property_attributes_staging
            WHERE run_id = ? AND canonical_location_id = ?
            """,
            (run_id, property_row["canonical_location_id"]),
        ).fetchone()
        if existing is not None and dict(existing).get("source_type") == "observed":
            continue

        matched = choose_best_match(property_row, permit_candidates, fuzzy_threshold=config.fuzzy_threshold)
        if matched is None:
            continue
        inferred = {
            "run_id": run_id,
            "canonical_location_id": property_row["canonical_location_id"],
            "bedrooms": _coerce_int(matched.matched_row.get("bedrooms")),
            "bathrooms": _coerce_float(matched.matched_row.get("bathrooms")),
            "bedrooms_estimated": None,
            "bathrooms_estimated": None,
            "source_type": "inferred",
            "source_name": matched.matched_row.get("source_name") or "permit_text",
            "source_record_id": matched.source_record_id,
            "observed_at": matched.matched_row.get("observed_at") or utc_now(),
            "confidence": matched.confidence * float(matched.matched_row.get("confidence") or 1.0),
            "match_method": "permit_text",
            "ambiguous": int(matched.ambiguous),
            "quarantined": int(matched.quarantined),
            "reason_code": matched.reason_code,
            "feature_snapshot_json": build_feature_snapshot(property_row),
            "raw_payload_json": matched.matched_row,
            "updated_at": utc_now(),
        }
        staged_rows.append(_jsonify(inferred))
        if inferred["ambiguous"] or inferred["quarantined"]:
            add_alert(
                conn,
                run_id,
                "warning",
                f"permit inference quarantined for {inferred['canonical_location_id']}",
            )

    staged_rows = _retain_best_source_assignments(staged_rows)
    upsert_staging_rows(conn, staged_rows)
    conn.commit()
    return staged_rows


def train_models(conn: sqlite3.Connection, run_id: str, config: EnrichmentConfig) -> dict[str, Any]:
    rows = rows_to_dicts(
        conn.execute(
            """
            SELECT pa.run_id, pa.canonical_location_id, pa.bedrooms, pa.bathrooms,
                   pa.bedrooms_estimated, pa.bathrooms_estimated, pa.source_type, pa.source_name,
                   pa.source_record_id, pa.observed_at, pa.confidence, pa.match_method,
                   pa.ambiguous, pa.quarantined, pa.reason_code, pa.feature_snapshot_json,
                   pa.raw_payload_json, pa.updated_at, pl.assessment_value, pl.suite, pl.house_number, pl.street_name,
                   pl.legal_description, pl.zoning, pl.lot_size, pl.total_gross_area,
                   pl.year_built, pl.neighbourhood_id, pl.neighbourhood, pl.ward,
                   pl.tax_class, pl.garage, pl.assessment_class_1, pl.assessment_class_2,
                   pl.assessment_class_3, pl.assessment_class_pct_1, pl.assessment_class_pct_2,
                   pl.assessment_class_pct_3, pl.lat, pl.lon
            FROM property_attributes_staging pa
            JOIN property_locations_prod pl ON pl.canonical_location_id = pa.canonical_location_id
            WHERE pa.run_id = ?
            UNION ALL
            SELECT NULL AS run_id, pa.canonical_location_id, pa.bedrooms, pa.bathrooms,
                   pa.bedrooms_estimated, pa.bathrooms_estimated, pa.source_type, pa.source_name,
                   pa.source_record_id, pa.observed_at, pa.confidence, pa.match_method,
                   pa.ambiguous, pa.quarantined, pa.reason_code, pa.feature_snapshot_json,
                   pa.raw_payload_json, pa.updated_at, pl.assessment_value, pl.suite, pl.house_number, pl.street_name,
                   pl.legal_description, pl.zoning, pl.lot_size, pl.total_gross_area,
                   pl.year_built, pl.neighbourhood_id, pl.neighbourhood, pl.ward,
                   pl.tax_class, pl.garage, pl.assessment_class_1, pl.assessment_class_2,
                   pl.assessment_class_3, pl.assessment_class_pct_1, pl.assessment_class_pct_2,
                   pl.assessment_class_pct_3, pl.lat, pl.lon
            FROM property_attributes_prod pa
            JOIN property_locations_prod pl ON pl.canonical_location_id = pa.canonical_location_id
            WHERE pa.source_type = 'observed'
            """
            ,
            (run_id,),
        ).fetchall()
    )
    candidate_training_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        canonical_location_id = str(row["canonical_location_id"])
        existing = candidate_training_rows.get(canonical_location_id)
        candidate_training_rows[canonical_location_id] = choose_preferred_record(existing, row)

    training_rows = training_rows_from_candidates(
        list(candidate_training_rows.values()),
        min_confidence=config.training_min_confidence,
    )
    model = select_model()
    imputation_enabled = len(training_rows) >= config.min_training_rows
    if imputation_enabled:
        model.fit(training_rows)
    return {
        "model": model,
        "model_version": model.version,
        "training_rows": len(training_rows),
        "imputation_enabled": imputation_enabled,
    }


def run_imputation(
    conn: sqlite3.Connection,
    run_id: str,
    candidates: list[dict[str, Any]],
    training_info: dict[str, Any],
    config: EnrichmentConfig,
) -> list[dict[str, Any]]:
    model = training_info["model"]
    staged_rows: list[dict[str, Any]] = []
    if not training_info.get("imputation_enabled"):
        return staged_rows

    for property_row in candidates:
        existing = conn.execute(
            """
            SELECT *
            FROM property_attributes_staging
            WHERE run_id = ? AND canonical_location_id = ?
            """,
            (run_id, property_row["canonical_location_id"]),
        ).fetchone()
        if existing is not None:
            existing_dict = dict(existing)
            if existing_dict.get("bedrooms") is not None or existing_dict.get("bathrooms") is not None:
                continue
        prediction = model.predict(property_row)
        if prediction.confidence < config.imputation_min_confidence:
            continue
        staged_rows.append(
            _jsonify(
                {
                    "run_id": run_id,
                    "canonical_location_id": property_row["canonical_location_id"],
                    "bedrooms": None,
                    "bathrooms": None,
                    "bedrooms_estimated": prediction.bedrooms_estimated,
                    "bathrooms_estimated": prediction.bathrooms_estimated,
                    "source_type": "imputed",
                    "source_name": training_info["model_version"],
                    "source_record_id": None,
                    "observed_at": None,
                    "confidence": prediction.confidence,
                    "match_method": "model_imputation",
                    "ambiguous": 0,
                    "quarantined": 0,
                    "reason_code": None,
                    "feature_snapshot_json": prediction.feature_snapshot,
                    "raw_payload_json": {"model_version": training_info["model_version"]},
                    "updated_at": utc_now(),
                }
            )
        )

    upsert_staging_rows(conn, staged_rows)
    conn.commit()
    return staged_rows


def promote_attributes(conn: sqlite3.Connection, run_id: str, config: EnrichmentConfig) -> dict[str, Any]:
    if config.promotion_target == "disabled":
        staging_records = conn.execute(
            "SELECT COUNT(*) FROM property_attributes_staging WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
        return {
            "promotion_disabled": True,
            "promotion_isolated": False,
            "target_table": None,
            "promoted_records": 0,
            "staging_records": staging_records,
            "promoted_datasets": [],
            "dataset_version_recorded": None,
        }
    if config.promotion_target == "shadow":
        result = promote_run(conn, run_id, target_table=config.shadow_table_name)
        result.update(
            {
                "promotion_disabled": False,
                "promotion_isolated": True,
                "promoted_datasets": [config.shadow_table_name],
                "dataset_version_recorded": "bedbath enrichment shadow promotion",
            }
        )
        return result
    result = promote_run(conn, run_id)
    result.update(
        {
            "promotion_disabled": False,
            "promotion_isolated": False,
            "promoted_datasets": [config.dataset_type],
            "dataset_version_recorded": "bedbath enrichment promotion",
        }
    )
    return result


def generate_report(
    conn: sqlite3.Connection,
    run_id: str,
    candidates: list[dict[str, Any]],
    clients: SourceClients,
    config: EnrichmentConfig,
) -> dict[str, Any]:
    staging_rows = rows_to_dicts(
        conn.execute(
            """
            SELECT *
            FROM property_attributes_staging
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchall()
    )
    listing_candidates = clients.load_listing_candidates()
    permit_candidates = clients.load_permit_candidates()
    diagnostics = _build_matching_diagnostics(candidates, listing_candidates, permit_candidates, staging_rows)
    report = build_report(staging_rows, len(candidates), diagnostics=diagnostics)
    report["ambiguous_csv_path"] = str(export_ambiguous_csv(staging_rows, config.ambiguous_export_path))
    report["review_exports"] = _export_review_sets(run_id, candidates, staging_rows, diagnostics, config)
    report["shadow_run_summary"] = _build_shadow_run_summary(report, diagnostics)
    report["real_feed_readiness_checklist"] = _build_real_feed_readiness_checklist(report, config)
    return report


def _build_matching_diagnostics(
    candidates: list[dict[str, Any]],
    listing_candidates: list[dict[str, Any]],
    permit_candidates: list[dict[str, Any]],
    staging_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    observed_rows = [row for row in staging_rows if row.get("source_type") == "observed"]
    matched_source_keys = {
        source_key
        for row in staging_rows
        if (source_key := _source_identity(row, str(row.get("source_type") or "unknown"))) is not None
    }
    typo_normalized_matches = sum(1 for row in observed_rows if row.get("reason_code") == "typo_normalized_match")
    suite_missing_multi_unit_quarantines = sum(
        1 for row in observed_rows if row.get("reason_code") == "suite_missing_multi_unit"
    )

    duplicate_groups: dict[str, list[str]] = {}
    candidates_by_house_number: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        normalized = row.get("normalized_address") or {}
        base_key = normalized.get("address_key_without_suite")
        if base_key:
            duplicate_groups.setdefault(base_key, []).append(str(row["canonical_location_id"]))
        house_number = normalized.get("house_number")
        if house_number:
            candidates_by_house_number.setdefault(house_number, []).append(row)

    fuzzy_miss_reasons: Counter[str] = Counter()
    unmatched_patterns: Counter[str] = Counter()
    unmatched_source_records: list[dict[str, Any]] = []
    source_batches = (
        [(row, "observed") for row in listing_candidates]
        + [(row, "inferred") for row in permit_candidates]
    )
    for source_row, source_type in source_batches:
        source_key = _source_identity(source_row, source_type)
        if source_key is not None and source_key in matched_source_keys:
            continue
        normalized = normalize_property_address(source_row)
        base_key = normalized.address_key_without_suite
        if not base_key:
            reason = "missing_address_components"
        elif not normalized.suite and len(duplicate_groups.get(base_key, [])) > 1:
            reason = "suite_missing_multi_unit"
        else:
            same_house_candidates = candidates_by_house_number.get(normalized.house_number or "", [])
            if same_house_candidates:
                best_similarity = max(
                    _diagnostic_similarity(
                        normalized.street_name or "",
                        (candidate.get("normalized_address") or {}).get("street_name") or "",
                    )
                    for candidate in same_house_candidates
                )
                reason = "fuzzy_below_threshold" if best_similarity >= 0.75 else "street_name_mismatch"
            else:
                reason = "no_house_number_match"
        fuzzy_miss_reasons[reason] += 1
        pattern = normalized.strict_address_key_without_suite or normalized.address_key_without_suite or "UNKNOWN"
        unmatched_patterns[pattern] += 1
        unmatched_source_records.append(
            {
                "source_type": source_type,
                "source_name": source_row.get("source_name"),
                "source_record_id": source_row.get("source_record_id"),
                "match_method": "unmatched_source_record",
                "reason_code": reason,
                "confidence": None,
                "source_row": source_row,
            }
        )

    duplicate_base_address_groups = [
        {"address_key_without_suite": key, "locations": location_ids}
        for key, location_ids in sorted(
            duplicate_groups.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
        if len(location_ids) > 1
    ]
    return {
        "typo_normalized_matches": typo_normalized_matches,
        "suite_missing_multi_unit_quarantines": suite_missing_multi_unit_quarantines,
        "fuzzy_misses_by_reason": dict(sorted(fuzzy_miss_reasons.items())),
        "unmatched_source_records_count": len(unmatched_source_records),
        "total_source_records": len(listing_candidates) + len(permit_candidates),
        "duplicate_source_count": sum(1 for row in staging_rows if row.get("reason_code") == "duplicate_source_record_match"),
        "unmatched_source_records": unmatched_source_records,
        "top_unmatched_address_patterns": [
            {"pattern": pattern, "count": count}
            for pattern, count in unmatched_patterns.most_common(10)
        ],
        "duplicate_base_address_groups": duplicate_base_address_groups,
    }


def _diagnostic_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _collect_alert_warnings(rows: list[dict[str, Any]]) -> list[str]:
    warnings = []
    for row in rows:
        if row.get("ambiguous") or row.get("quarantined"):
            warnings.append(f"{row['canonical_location_id']}:{row.get('reason_code') or row.get('match_method')}")
    return warnings


def _retain_best_source_assignments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        source_record_id = row.get("source_record_id")
        if not source_record_id:
            passthrough.append(row)
            continue
        grouped.setdefault(str(source_record_id), []).append(row)

    winners: list[dict[str, Any]] = []
    for source_record_id, candidates in grouped.items():
        suite_missing_candidates = [row for row in candidates if row.get("reason_code") == "suite_missing_multi_unit"]
        if suite_missing_candidates:
            best = sorted(
                suite_missing_candidates,
                key=lambda row: float(row.get("confidence") or 0.0),
                reverse=True,
            )[0]
            quarantined = dict(best)
            quarantined["ambiguous"] = 1
            quarantined["quarantined"] = 1
            quarantined["reason_code"] = "suite_missing_multi_unit"
            winners.append(quarantined)
            continue
        ordered = sorted(
            candidates,
            key=lambda row: (
                float(row.get("confidence") or 0.0),
                1 if row.get("match_method") == "exact_address_suite" else 0,
                1 if row.get("match_method") == "exact_legal_description" else 0,
            ),
            reverse=True,
        )
        best = ordered[0]
        if len(ordered) > 1 and abs(float(best.get("confidence") or 0.0) - float(ordered[1].get("confidence") or 0.0)) < 1e-9:
            quarantined = dict(best)
            quarantined["ambiguous"] = 1
            quarantined["quarantined"] = 1
            if any(row.get("match_method") == "suite_missing_multi_unit" for row in ordered):
                quarantined["match_method"] = "suite_missing_multi_unit"
                quarantined["reason_code"] = "suite_missing_multi_unit"
            else:
                quarantined["reason_code"] = "duplicate_source_record_match"
            winners.append(quarantined)
            continue
        winners.append(best)
    return passthrough + winners


def _start_workflow_run(conn: sqlite3.Connection, run_id: str, trigger: str) -> None:
    conn.execute(
        """
        INSERT INTO workflow_runs (run_id, trigger_type, correlation_id, status, started_at)
        VALUES (?, ?, ?, 'running', ?)
        """,
        (run_id, trigger, f"corr-{uuid.uuid4().hex[:10]}", utc_now()),
    )
    conn.commit()


def _finish_workflow_run(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    warnings: list[str],
    errors: list[str],
    promoted_datasets: list[str],
) -> None:
    conn.execute(
        """
        UPDATE workflow_runs
        SET status = ?, completed_at = ?, warnings_json = ?, errors_json = ?
        WHERE run_id = ?
        """,
        (status, utc_now(), json.dumps(warnings), json.dumps(errors), run_id),
    )
    conn.execute(
        """
        INSERT INTO workflow_summaries (run_id, promoted_json, skipped_json, failed_json, reasons_json)
        VALUES (?, ?, '[]', ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            promoted_json = excluded.promoted_json,
            failed_json = excluded.failed_json,
            reasons_json = excluded.reasons_json
        """,
        (
            run_id,
            json.dumps(promoted_datasets if status == "succeeded" else []),
            json.dumps([] if status == "succeeded" else ["property_attributes"]),
            json.dumps({} if status == "succeeded" else {"property_attributes": errors}),
        ),
    )


def _run_step(conn: sqlite3.Connection, run_id: str, name: str, step_runs: list[dict[str, Any]], fn) -> Any:
    step_id = f"step-{uuid.uuid4().hex[:8]}"
    started = utc_now()
    try:
        result = fn()
        conn.execute(
            """
            INSERT INTO workflow_steps (
                step_id, run_id, dataset_type, status, retry_count, started_at, completed_at,
                warnings_json, errors_json
            ) VALUES (?, ?, ?, 'succeeded', 0, ?, ?, '[]', '[]')
            """,
            (step_id, run_id, name, started, utc_now()),
        )
        conn.commit()
        step_runs.append({"dataset": name, "status": "succeeded"})
        return result
    except Exception as exc:
        conn.execute(
            """
            INSERT INTO workflow_steps (
                step_id, run_id, dataset_type, status, retry_count, started_at, completed_at,
                warnings_json, errors_json
            ) VALUES (?, ?, ?, 'failed', 0, ?, ?, '[]', ?)
            """,
            (step_id, run_id, name, started, utc_now(), json.dumps([str(exc)])),
        )
        conn.commit()
        step_runs.append({"dataset": name, "status": "failed"})
        raise


def _jsonify(row: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(row)
    prepared["feature_snapshot_json"] = json.dumps(prepared.get("feature_snapshot_json", {}))
    prepared["raw_payload_json"] = json.dumps(prepared.get("raw_payload_json", {}))
    return prepared


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_identity(row: dict[str, Any], source_type: str) -> str | None:
    source_record_id = row.get("source_record_id")
    if source_record_id not in (None, ""):
        return f"{source_type}:{source_record_id}"
    normalized = normalize_property_address(row)
    identity_key = normalized.full_address_key or normalized.address_key_without_suite
    if identity_key:
        return f"{source_type}:{identity_key}:{row.get('source_name') or ''}"
    return None


def _decode_jsonish(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _raw_source_address(source_row: dict[str, Any]) -> str | None:
    if not source_row:
        return None
    raw_payload = _decode_jsonish(source_row.get("raw_payload_json"))
    address = source_row.get("address") or raw_payload.get("address") or raw_payload.get("property_address")
    if address not in (None, ""):
        return str(address)
    parts = [source_row.get("suite"), source_row.get("house_number"), source_row.get("street_name")]
    rendered = " ".join(str(part).strip() for part in parts if part not in (None, ""))
    return rendered or None


def _review_row_from_staging(row: dict[str, Any], candidate_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    property_row = candidate_lookup.get(str(row.get("canonical_location_id")), {})
    source_row = _decode_jsonish(row.get("raw_payload_json"))
    normalized = normalize_property_address(source_row or property_row)
    return {
        "canonical_location_id": row.get("canonical_location_id"),
        "source_record_id": row.get("source_record_id"),
        "source_type": row.get("source_type"),
        "source_name": row.get("source_name"),
        "match_method": row.get("match_method"),
        "reason_code": row.get("reason_code"),
        "confidence": row.get("confidence"),
        "normalized_address": normalized.full_address_key or normalized.address_key_without_suite,
        "raw_source_address": _raw_source_address(source_row),
        "suite": source_row.get("suite") or property_row.get("suite"),
        "house_number": source_row.get("house_number") or property_row.get("house_number"),
        "street_name": source_row.get("street_name") or property_row.get("street_name"),
        "legal_description": source_row.get("legal_description") or property_row.get("legal_description"),
        "lat": source_row.get("lat") if source_row.get("lat") is not None else property_row.get("lat"),
        "lon": source_row.get("lon") if source_row.get("lon") is not None else property_row.get("lon"),
    }


def _review_row_from_unmatched(item: dict[str, Any]) -> dict[str, Any]:
    source_row = dict(item.get("source_row") or {})
    normalized = normalize_property_address(source_row)
    return {
        "canonical_location_id": None,
        "source_record_id": source_row.get("source_record_id"),
        "source_type": item.get("source_type"),
        "source_name": source_row.get("source_name"),
        "match_method": item.get("match_method"),
        "reason_code": item.get("reason_code"),
        "confidence": item.get("confidence"),
        "normalized_address": normalized.full_address_key or normalized.address_key_without_suite,
        "raw_source_address": _raw_source_address(source_row),
        "suite": source_row.get("suite"),
        "house_number": source_row.get("house_number"),
        "street_name": source_row.get("street_name"),
        "legal_description": source_row.get("legal_description"),
        "lat": source_row.get("lat"),
        "lon": source_row.get("lon"),
    }


def _duplicate_group_export_rows(
    duplicate_groups: list[dict[str, Any]],
    candidate_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in duplicate_groups:
        for canonical_location_id in group.get("locations", []):
            property_row = candidate_lookup.get(str(canonical_location_id), {})
            normalized = normalize_property_address(property_row)
            rows.append(
                {
                    "canonical_location_id": canonical_location_id,
                    "source_record_id": None,
                    "source_type": "property_candidate",
                    "source_name": "property_locations_prod",
                    "match_method": "duplicate_base_address_group",
                    "reason_code": "duplicate_base_address_group",
                    "confidence": property_row.get("confidence"),
                    "normalized_address": normalized.full_address_key or group.get("address_key_without_suite"),
                    "raw_source_address": None,
                    "suite": property_row.get("suite"),
                    "house_number": property_row.get("house_number"),
                    "street_name": property_row.get("street_name"),
                    "legal_description": property_row.get("legal_description"),
                    "lat": property_row.get("lat"),
                    "lon": property_row.get("lon"),
                }
            )
    return rows


def _export_review_sets(
    run_id: str,
    candidates: list[dict[str, Any]],
    staging_rows: list[dict[str, Any]],
    diagnostics: dict[str, Any],
    config: EnrichmentConfig,
) -> dict[str, str]:
    export_dir = Path(config.review_export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    candidate_lookup = {str(row["canonical_location_id"]): row for row in candidates}
    unmatched_rows = [_review_row_from_unmatched(item) for item in diagnostics.get("unmatched_source_records", [])]
    suite_missing_rows = [
        _review_row_from_staging(row, candidate_lookup)
        for row in staging_rows
        if row.get("reason_code") == "suite_missing_multi_unit"
    ]
    suite_missing_rows.extend(row for row in unmatched_rows if row.get("reason_code") == "suite_missing_multi_unit")
    export_paths = {
        "fuzzy_address_geo_matches": export_dir / f"{run_id}_fuzzy_address_geo_matches.csv",
        "typo_normalized_matches": export_dir / f"{run_id}_typo_normalized_matches.csv",
        "quarantined_rows": export_dir / f"{run_id}_quarantined_rows.csv",
        "suite_missing_multi_unit_cases": export_dir / f"{run_id}_suite_missing_multi_unit_cases.csv",
        "imputed_rows_above_threshold": export_dir / f"{run_id}_imputed_rows_above_threshold.csv",
        "unmatched_source_records": export_dir / f"{run_id}_unmatched_source_records.csv",
        "duplicate_base_address_groups": export_dir / f"{run_id}_duplicate_base_address_groups.csv",
    }
    export_rows_csv(
        [_review_row_from_staging(row, candidate_lookup) for row in staging_rows if row.get("match_method") == "fuzzy_address_geo"],
        export_paths["fuzzy_address_geo_matches"],
        fields=REVIEW_EXPORT_FIELDS,
    )
    export_rows_csv(
        [_review_row_from_staging(row, candidate_lookup) for row in staging_rows if row.get("reason_code") == "typo_normalized_match"],
        export_paths["typo_normalized_matches"],
        fields=REVIEW_EXPORT_FIELDS,
    )
    export_rows_csv(
        [_review_row_from_staging(row, candidate_lookup) for row in staging_rows if row.get("quarantined")],
        export_paths["quarantined_rows"],
        fields=REVIEW_EXPORT_FIELDS,
    )
    export_rows_csv(
        suite_missing_rows,
        export_paths["suite_missing_multi_unit_cases"],
        fields=REVIEW_EXPORT_FIELDS,
    )
    export_rows_csv(
        [
            _review_row_from_staging(row, candidate_lookup)
            for row in staging_rows
            if row.get("source_type") == "imputed" and float(row.get("confidence") or 0.0) >= config.imputation_min_confidence
        ],
        export_paths["imputed_rows_above_threshold"],
        fields=REVIEW_EXPORT_FIELDS,
    )
    export_rows_csv(
        unmatched_rows,
        export_paths["unmatched_source_records"],
        fields=REVIEW_EXPORT_FIELDS,
    )
    export_rows_csv(
        _duplicate_group_export_rows(diagnostics.get("duplicate_base_address_groups", []), candidate_lookup),
        export_paths["duplicate_base_address_groups"],
        fields=REVIEW_EXPORT_FIELDS,
    )
    return {key: str(path) for key, path in export_paths.items()}


def _build_shadow_run_summary(report: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    candidate_properties = int(report["total_candidate_properties"])
    observed_fills = int(report["filled_from_observed_values"])
    inferred_fills = int(report["filled_from_inferred_permit_values"])
    imputed_fills = int(report["filled_from_imputation"])
    total_source_records = int(diagnostics.get("total_source_records") or 0)
    unmatched_source_records = int(diagnostics.get("unmatched_source_records_count") or 0)
    return {
        "candidate_properties": candidate_properties,
        "observed_fills": observed_fills,
        "inferred_fills": inferred_fills,
        "imputed_fills": imputed_fills,
        "remaining_nulls": int(report["remaining_nulls"]),
        "ambiguous_count": int(report["ambiguity_count"]),
        "quarantine_count": int(report["quarantine_count"]),
        "duplicate_source_count": int(diagnostics.get("duplicate_source_count") or 0),
        "percent_observed": round((observed_fills / candidate_properties) * 100, 2) if candidate_properties else 0.0,
        "percent_estimated": round(((inferred_fills + imputed_fills) / candidate_properties) * 100, 2) if candidate_properties else 0.0,
        "percent_unmatched_source_records": round((unmatched_source_records / total_source_records) * 100, 2)
        if total_source_records
        else 0.0,
    }


def _build_real_feed_readiness_checklist(report: dict[str, Any], config: EnrichmentConfig) -> dict[str, Any]:
    return {
        "safe_to_review_fuzzy_matches": bool(report["review_exports"].get("fuzzy_address_geo_matches")),
        "safe_to_review_quarantines": bool(report["review_exports"].get("quarantined_rows")),
        "safe_to_review_imputed_rows": bool(report["review_exports"].get("imputed_rows_above_threshold")),
        "promotion_still_disabled": config.promotion_target == "disabled",
        "recommended_promotion_threshold": 0.90,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Edmonton bedroom/bathroom enrichment workflow.")
    parser.add_argument("--db-path", required=True, help="Path to the SQLite warehouse database.")
    parser.add_argument("--trigger", default="on_demand", help="Workflow trigger type.")
    parser.add_argument("--listings-json", help="Optional JSON file containing listing/API records.")
    parser.add_argument("--listings-csv", help="Optional CSV file containing listing/API records.")
    parser.add_argument("--listings-map", help="Optional JSON field map for listing records.")
    parser.add_argument("--permits-json", help="Optional JSON file containing permit text records.")
    parser.add_argument("--permits-csv", help="Optional CSV file containing permit text records.")
    parser.add_argument("--permits-map", help="Optional JSON field map for permit records.")
    parser.add_argument("--ambiguous-csv", default="reports/bedbath_ambiguous_matches.csv")
    parser.add_argument("--review-export-dir", default="reports/bedbath_review_exports")
    parser.add_argument("--min-training-rows", type=int, default=25)
    parser.add_argument("--shadow-mode", action="store_true", help="Run in review-only shadow mode.")
    parser.add_argument("--disable-promotion", action="store_true", help="Do not promote staging rows to prod.")
    parser.add_argument("--shadow-table-name", help="Optional isolated table for shadow promotion output.")
    args = parser.parse_args()

    promotion_target = "prod"
    if args.shadow_table_name:
        promotion_target = "shadow"
    if args.disable_promotion or (args.shadow_mode and not args.shadow_table_name):
        promotion_target = "disabled"

    result = run_bedbath_enrichment(
        args.db_path,
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
        ),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
