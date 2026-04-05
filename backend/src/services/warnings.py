from __future__ import annotations

from typing import Iterable


def build_missing_data_warning(missing_factors: list[str]) -> list[dict]:
    if not missing_factors:
        return []
    return [
        {
            "code": "MISSING_DATA",
            "severity": "warning",
            "title": "Some data is missing",
            "message": "One or more valuation factors were unavailable.",
            "affected_factors": missing_factors,
            "dismissible": True,
        }
    ]


def build_routing_warning(affected_factors: Iterable[str], reason: str | None) -> dict | None:
    return {
        "code": "ROUTING_FALLBACK_USED",
        "severity": "warning",
        "title": "Approximate distances used",
        "message": "Routing was unavailable, so straight-line distance was used.",
        "affected_factors": list(affected_factors),
        "dismissible": True,
        "reason": reason,
    }
