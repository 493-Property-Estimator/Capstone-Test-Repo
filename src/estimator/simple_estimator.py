"""Simple summary statistics for nearby property assessment values."""

from __future__ import annotations

from statistics import median, multimode
from typing import Iterable


def summarize_property_cluster(properties: Iterable[dict]) -> dict:
    values = [
        float(property_row["assessment_value"])
        for property_row in properties
        if property_row.get("assessment_value") is not None
    ]

    if not values:
        return {
            "sample_size": 0,
            "mean": None,
            "median": None,
            "mode": [],
        }

    sample_size = len(values)
    mean_value = sum(values) / sample_size
    mode_values = multimode(values)

    return {
        "sample_size": sample_size,
        "mean": round(mean_value, 2),
        "median": round(float(median(values)), 2),
        "mode": sorted(round(float(value), 2) for value in mode_values),
    }
