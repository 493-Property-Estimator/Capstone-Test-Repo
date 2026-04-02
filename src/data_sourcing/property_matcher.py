"""Deterministic property matching for observed bed/bath enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from math import radians, sin, cos, sqrt, atan2
from typing import Any

from .address_normalization import NormalizedAddress, normalize_property_address

try:
    from rapidfuzz import fuzz  # type: ignore
except ImportError:  # pragma: no cover
    fuzz = None


@dataclass(frozen=True)
class MatchResult:
    canonical_location_id: str
    source_record_id: str | None
    match_method: str
    confidence: float
    ambiguous: bool
    quarantined: bool
    reason_code: str | None
    matched_row: dict[str, Any]


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return max(
            float(fuzz.ratio(left, right)) / 100.0,
            float(fuzz.token_sort_ratio(left, right)) / 100.0,
        )
    return SequenceMatcher(None, left, right).ratio()


def geo_distance_meters(lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius = 6_371_000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius * atan2(sqrt(a), sqrt(1 - a))


def _agreement_score(property_row: dict[str, Any], source_row: dict[str, Any]) -> float:
    score = 0.0
    if _safe_equal(property_row.get("year_built"), source_row.get("year_built")):
        score += 0.15
    area_similarity = _numeric_similarity(property_row.get("total_gross_area"), source_row.get("total_gross_area"))
    if area_similarity is not None:
        score += 0.20 * area_similarity
    distance = geo_distance_meters(
        _coerce_float(property_row.get("lat")),
        _coerce_float(property_row.get("lon")),
        _coerce_float(source_row.get("lat")),
        _coerce_float(source_row.get("lon")),
    )
    if distance is not None:
        if distance <= 15:
            score += 0.20
        elif distance <= 40:
            score += 0.10
    return score


def _numeric_similarity(left: Any, right: Any) -> float | None:
    left_num = _coerce_float(left)
    right_num = _coerce_float(right)
    if left_num is None or right_num is None or max(left_num, right_num) == 0:
        return None
    return max(0.0, 1.0 - abs(left_num - right_num) / max(abs(left_num), abs(right_num)))


def _safe_equal(left: Any, right: Any) -> bool:
    return left not in (None, "") and right not in (None, "") and str(left) == str(right)


def _is_same_house_number(left: Any, right: Any) -> bool:
    return _clean_token(left) is not None and _clean_token(left) == _clean_token(right)


def _clean_token(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip().upper() or None


def _is_suite_missing_multi_unit_risk(
    property_row: dict[str, Any],
    normalized_property: NormalizedAddress,
    normalized_source: NormalizedAddress,
) -> bool:
    group_size = int(property_row.get("multi_unit_group_size") or 0)
    if group_size <= 1:
        return False
    if not normalized_property.suite or normalized_source.suite:
        return False
    if not _is_same_house_number(normalized_property.house_number, normalized_source.house_number):
        return False
    street_similarity = _similarity(
        normalized_property.address_key_without_suite,
        normalized_source.address_key_without_suite,
    )
    return street_similarity >= 0.95


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def choose_best_match(
    property_row: dict[str, Any],
    source_rows: list[dict[str, Any]],
    *,
    fuzzy_threshold: float = 0.90,
    ambiguity_gap: float = 0.03,
) -> MatchResult | None:
    if not source_rows:
        return None

    normalized_property = normalize_property_address(property_row)
    scored: list[tuple[float, MatchResult]] = []

    for source_row in source_rows:
        normalized_source = normalize_property_address(source_row)
        result = _match_single(property_row, normalized_property, source_row, normalized_source, fuzzy_threshold)
        if result is not None:
            scored.append((result.confidence, result))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_result = scored[0]
    if len(scored) > 1 and (best_score - scored[1][0]) < ambiguity_gap:
        return MatchResult(
            canonical_location_id=best_result.canonical_location_id,
            source_record_id=best_result.source_record_id,
            match_method=best_result.match_method,
            confidence=best_result.confidence,
            ambiguous=True,
            quarantined=True,
            reason_code="ambiguous_match_candidates",
            matched_row=best_result.matched_row,
        )
    return best_result


def _match_single(
    property_row: dict[str, Any],
    normalized_property: NormalizedAddress,
    source_row: dict[str, Any],
    normalized_source: NormalizedAddress,
    fuzzy_threshold: float,
) -> MatchResult | None:
    canonical_location_id = str(property_row["canonical_location_id"])
    source_record_id = source_row.get("source_record_id") or source_row.get("record_id")

    if _is_suite_missing_multi_unit_risk(property_row, normalized_property, normalized_source):
        return MatchResult(
            canonical_location_id=canonical_location_id,
            source_record_id=str(source_record_id) if source_record_id is not None else None,
            match_method="suite_missing_multi_unit",
            confidence=0.96,
            ambiguous=True,
            quarantined=True,
            reason_code="suite_missing_multi_unit",
            matched_row=source_row,
        )

    if (
        normalized_property.full_address_key
        and normalized_property.full_address_key == normalized_source.full_address_key
    ):
        typo_normalized = (
            normalized_property.strict_full_address_key
            and normalized_source.strict_full_address_key
            and normalized_property.strict_full_address_key != normalized_source.strict_full_address_key
        )
        return MatchResult(
            canonical_location_id=canonical_location_id,
            source_record_id=str(source_record_id) if source_record_id is not None else None,
            match_method="fuzzy_address_geo" if typo_normalized else "exact_address_suite",
            confidence=0.965 if typo_normalized else 0.99,
            ambiguous=False,
            quarantined=False,
            reason_code="typo_normalized_match" if typo_normalized else None,
            matched_row=source_row,
        )

    if (
        normalized_property.legal_description
        and normalized_property.legal_description == normalized_source.legal_description
    ):
        return MatchResult(
            canonical_location_id=canonical_location_id,
            source_record_id=str(source_record_id) if source_record_id is not None else None,
            match_method="exact_legal_description",
            confidence=0.97,
            ambiguous=False,
            quarantined=False,
            reason_code=None,
            matched_row=source_row,
        )

    if not _is_same_house_number(normalized_property.house_number, normalized_source.house_number):
        return None

    street_similarity = _similarity(normalized_property.street_name or "", normalized_source.street_name or "")
    if street_similarity < max(fuzzy_threshold - 0.04, 0.84):
        return None

    address_similarity = _similarity(
        normalized_property.address_key_without_suite,
        normalized_source.address_key_without_suite,
    )

    confidence = 0.70 + (0.15 * address_similarity) + _agreement_score(property_row, source_row)
    confidence = min(confidence, 0.96)
    typo_normalized = (
        normalized_property.strict_address_key_without_suite
        and normalized_source.strict_address_key_without_suite
        and normalized_property.strict_address_key_without_suite != normalized_source.strict_address_key_without_suite
        and normalized_property.address_key_without_suite == normalized_source.address_key_without_suite
    )
    return MatchResult(
        canonical_location_id=canonical_location_id,
        source_record_id=str(source_record_id) if source_record_id is not None else None,
        match_method="fuzzy_address_geo",
        confidence=confidence,
        ambiguous=False,
        quarantined=False,
        reason_code="typo_normalized_match" if typo_normalized else None,
        matched_row=source_row,
    )
