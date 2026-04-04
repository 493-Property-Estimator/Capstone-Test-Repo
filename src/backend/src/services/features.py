from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from estimator import proximity


@dataclass
class FactorResult:
    factor_id: str
    label: str
    value: float
    status: str
    summary: str


def _distance_to_factor(distance_m: float, positive: bool = True) -> float:
    if distance_m <= 500:
        return 5000 if positive else -5000
    if distance_m <= 1000:
        return 2000 if positive else -2000
    if distance_m <= 2000:
        return 500 if positive else -500
    return 0.0


def compute_proximity_factors(point: tuple[float, float], db_path) -> tuple[list[FactorResult], list[str]]:
    missing: list[str] = []
    results: list[FactorResult] = []

    schools = proximity.get_nearest_schools(point, limit=1, distance_mode="manhattan", db_path=db_path)
    if schools:
        dist = float(schools[0].get("distance_m") or 0.0)
        results.append(
            FactorResult(
                factor_id="school_distance",
                label="Distance to schools",
                value=_distance_to_factor(dist, positive=True),
                status="available",
                summary="Nearby schools impact value.",
            )
        )
    else:
        missing.append("schools")
        results.append(
            FactorResult(
                factor_id="school_distance",
                label="Distance to schools",
                value=0.0,
                status="missing",
                summary="School dataset unavailable.",
            )
        )

    parks = proximity.get_nearest_parks(point, limit=1, distance_mode="manhattan", db_path=db_path)
    if parks:
        dist = float(parks[0].get("distance_m") or 0.0)
        results.append(
            FactorResult(
                factor_id="green_space",
                label="Green space proximity",
                value=_distance_to_factor(dist, positive=True),
                status="available",
                summary="Nearby parks increase livability.",
            )
        )
    else:
        missing.append("parks")
        results.append(
            FactorResult(
                factor_id="green_space",
                label="Green space proximity",
                value=0.0,
                status="missing",
                summary="Park dataset unavailable.",
            )
        )

    police = proximity.get_nearest_police_stations(point, limit=1, distance_mode="manhattan", db_path=db_path)
    if police:
        dist = float(police[0].get("distance_m") or 0.0)
        results.append(
            FactorResult(
                factor_id="crime_proxy",
                label="Crime proxy (police distance)",
                value=_distance_to_factor(dist, positive=False),
                status="available",
                summary="Closer police stations may indicate higher incident density.",
            )
        )
    else:
        missing.append("crime_statistics")
        results.append(
            FactorResult(
                factor_id="crime_proxy",
                label="Crime proxy (police distance)",
                value=0.0,
                status="missing",
                summary="Crime dataset unavailable.",
            )
        )

    playgrounds = proximity.get_nearest_playgrounds(point, limit=1, distance_mode="manhattan", db_path=db_path)
    if playgrounds:
        dist = float(playgrounds[0].get("distance_m") or 0.0)
        results.append(
            FactorResult(
                factor_id="playgrounds",
                label="Playgrounds",
                value=_distance_to_factor(dist, positive=True),
                status="available",
                summary="Playgrounds add neighborhood value.",
            )
        )
    else:
        missing.append("playgrounds")
        results.append(
            FactorResult(
                factor_id="playgrounds",
                label="Playgrounds",
                value=0.0,
                status="missing",
                summary="Playground dataset unavailable.",
            )
        )

    comparables = proximity.get_top_closest_properties(point, limit=5, distance_mode="manhattan", db_path=db_path)
    if not comparables:
        missing.append("comparables")
    return results, missing


def compute_comparable_adjustment(point: tuple[float, float], baseline: float, db_path) -> float:
    comps = proximity.get_top_closest_properties(point, limit=5, distance_mode="manhattan", db_path=db_path)
    values = [row.get("assessment_value") for row in comps if row.get("assessment_value") is not None]
    if not values:
        return 0.0
    avg = sum(values) / len(values)
    return (avg - baseline) * 0.2
