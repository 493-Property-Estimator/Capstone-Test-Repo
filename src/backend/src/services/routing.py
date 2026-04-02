from __future__ import annotations

import math
from dataclasses import dataclass

from backend.src.services.metrics import Metrics

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class DistanceResult:
    distance_m: float
    mode: str
    fallback_used: bool
    reason: str | None


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def compute_distance(
    origin: tuple[float, float],
    target: tuple[float, float],
    routing_enabled: bool,
    metrics: Metrics | None = None,
) -> DistanceResult:
    # Routing not implemented: always use straight-line fallback when routing_enabled is False
    if not routing_enabled:
        distance = haversine_m(origin[0], origin[1], target[0], target[1])
        if metrics:
            metrics.record_routing_fallback()
        return DistanceResult(distance_m=distance, mode="straight_line", fallback_used=True, reason="routing_disabled")

    # Placeholder: no routing provider configured; use straight-line fallback
    distance = haversine_m(origin[0], origin[1], target[0], target[1])
    if metrics:
        metrics.record_routing_fallback()
    return DistanceResult(distance_m=distance, mode="straight_line", fallback_used=True, reason="routing_unavailable")
