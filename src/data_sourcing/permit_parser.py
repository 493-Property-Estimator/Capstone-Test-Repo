"""Permit text parsing for inferred bedroom and bathroom counts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


BEDROOM_RE = re.compile(r"(\d+)\s*(?:BED|BEDROOM)", re.IGNORECASE)
BATHROOM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:BATH|BATHROOM)", re.IGNORECASE)
HALF_BATH_RE = re.compile(r"(?:HALF[- ]?BATH|1/2\s*BATH)", re.IGNORECASE)


@dataclass(frozen=True)
class PermitInference:
    bedrooms: int | None
    bathrooms: float | None
    confidence: float
    reason_code: str | None


def parse_permit_text(text: str | None) -> PermitInference | None:
    if not text:
        return None
    bedrooms = None
    bathrooms = None

    bed_match = BEDROOM_RE.search(text)
    if bed_match:
        bedrooms = int(bed_match.group(1))

    bath_match = BATHROOM_RE.search(text)
    if bath_match:
        bathrooms = float(bath_match.group(1))
        if HALF_BATH_RE.search(text):
            bathrooms += 0.5
    elif HALF_BATH_RE.search(text):
        bathrooms = 0.5

    if bedrooms is None and bathrooms is None:
        return None

    confidence = 0.82 if bedrooms is not None and bathrooms is not None else 0.72
    return PermitInference(
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        confidence=confidence,
        reason_code=None,
    )


def parse_permit_record(record: dict[str, Any]) -> dict[str, Any] | None:
    inference = parse_permit_text(
        record.get("permit_text") or record.get("permit_description") or record.get("description")
    )
    if inference is None:
        return None
    enriched = dict(record)
    enriched["bedrooms"] = inference.bedrooms
    enriched["bathrooms"] = inference.bathrooms
    enriched["confidence"] = record.get("confidence", inference.confidence)
    enriched["reason_code"] = inference.reason_code
    return enriched
