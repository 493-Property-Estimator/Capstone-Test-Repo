from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from backend.src.config import EDMONTON_BOUNDS


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    reason: str
    correction: str
    severity: int = 1


def validate_coordinates(coords: dict[str, Any] | Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if coords is None:
        issues.append(ValidationIssue("coordinates", "missing", "Provide both lat and lng."))
        return issues
    if not isinstance(coords, dict):
        issues.append(
            ValidationIssue("coordinates", "invalid_type", "Coordinates must be an object with lat and lng.")
        )
        return issues
    lat = coords.get("lat") if coords else None
    lng = coords.get("lng") if coords else None
    if lat is None or lng is None:
        issues.append(ValidationIssue("coordinates", "missing", "Provide both lat and lng."))
        return issues
    try:
        lat_val = float(lat)
    except Exception:
        issues.append(ValidationIssue("coordinates.lat", "not_numeric", "Latitude must be numeric."))
        lat_val = None
    try:
        lng_val = float(lng)
    except Exception:
        issues.append(ValidationIssue("coordinates.lng", "not_numeric", "Longitude must be numeric."))
        lng_val = None
    if lat_val is not None and (lat_val < -90 or lat_val > 90):
        issues.append(
            ValidationIssue("coordinates.lat", "out_of_range", "Latitude must be between -90 and 90.")
        )
    if lng_val is not None and (lng_val < -180 or lng_val > 180):
        issues.append(
            ValidationIssue("coordinates.lng", "out_of_range", "Longitude must be between -180 and 180.")
        )
    return issues


def validate_address(address: str | None) -> list[ValidationIssue]:
    if not address or not address.strip():
        return [ValidationIssue("address", "missing", "Provide a street address.")]
    if len(address.strip()) < 5 or any(ch.isdigit() for ch in address) is False:
        return [
            ValidationIssue(
                "address",
                "invalid_format",
                "Include street number and street name.",
            )
        ]
    return []


def coords_in_bounds(coords: dict[str, float]) -> bool:
    return (
        EDMONTON_BOUNDS["west"] <= coords["lng"] <= EDMONTON_BOUNDS["east"]
        and EDMONTON_BOUNDS["south"] <= coords["lat"] <= EDMONTON_BOUNDS["north"]
    )


def validate_location_payload(payload: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    location = payload.get("location") if payload else None
    if not location:
        return [ValidationIssue("location", "missing", "Provide a location selector.")]
    if not isinstance(location, dict):
        return [
            ValidationIssue(
                "location",
                "invalid_type",
                "Location must be an object containing address, coordinates, or canonical_location_id.",
            )
        ]
    has_coordinates = bool(location.get("coordinates"))
    has_canonical = bool(location.get("canonical_location_id") or location.get("property_id"))
    has_polygon = bool(location.get("polygon"))
    if has_coordinates:
        issues.extend(validate_coordinates(location.get("coordinates")))
    # Only enforce street-address format when address is the sole selector.
    if location.get("address") and not (has_coordinates or has_canonical or has_polygon):
        issues.extend(validate_address(location.get("address")))
    if has_polygon:
        issues.extend(validate_polygon(location.get("polygon")))
    if not (
        has_coordinates
        or location.get("address")
        or has_canonical
        or has_polygon
    ):
        issues.append(
            ValidationIssue(
                "location",
                "missing_selector",
                "Provide address, coordinates, polygon, property_id, or canonical_location_id.",
            )
        )
    return issues


def validate_property_details(payload: dict[str, Any]) -> list[ValidationIssue]:
    details = payload.get("property_details") if payload else None
    if not isinstance(details, dict):
        return []

    issues: list[ValidationIssue] = []
    numeric_min = {
        "bedrooms": 0.0,
        "bathrooms": 0.0,
        "floor_area_sqft": 1.0,
        "total_gross_area": 1.0,
    }
    for field, minimum in numeric_min.items():
        if field not in details or details[field] in (None, ""):
            continue
        try:
            value = float(details[field])
        except Exception:
            issues.append(
                ValidationIssue(
                    f"property_details.{field}",
                    "not_numeric",
                    f"{field} must be numeric.",
                )
            )
            continue
        if value < minimum:
            comparator = "non-negative" if minimum == 0.0 else "greater than 0"
            issues.append(
                ValidationIssue(
                    f"property_details.{field}",
                    "out_of_range",
                    f"{field} must be {comparator}.",
                )
            )
    return issues


def validate_polygon(polygon: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(polygon, dict):
        return [ValidationIssue("location.polygon", "invalid_format", "Polygon must be a GeoJSON object.")]

    if str(polygon.get("type") or "").lower() != "polygon":
        return [ValidationIssue("location.polygon.type", "invalid_format", "Polygon type must be 'Polygon'.")]

    coordinates = polygon.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates or not isinstance(coordinates[0], list):
        return [
            ValidationIssue(
                "location.polygon.coordinates",
                "invalid_format",
                "Polygon coordinates must contain at least one linear ring.",
            )
        ]
    ring = coordinates[0]
    if len(ring) < 4:
        return [
            ValidationIssue(
                "location.polygon.coordinates",
                "invalid_format",
                "Polygon linear ring must contain at least 4 points (including closure).",
            )
        ]

    normalized: list[tuple[float, float]] = []
    for index, point in enumerate(ring):
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            issues.append(
                ValidationIssue(
                    f"location.polygon.coordinates[{index}]",
                    "invalid_format",
                    "Each polygon point must be [lng, lat].",
                )
            )
            continue
        try:
            lng = float(point[0])
            lat = float(point[1])
        except Exception:
            issues.append(
                ValidationIssue(
                    f"location.polygon.coordinates[{index}]",
                    "not_numeric",
                    "Polygon coordinates must be numeric.",
                )
            )
            continue
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            issues.append(
                ValidationIssue(
                    f"location.polygon.coordinates[{index}]",
                    "out_of_range",
                    "Polygon coordinates are out of range.",
                )
            )
            continue
        normalized.append((lng, lat))

    if issues:
        return issues
    if normalized[0] != normalized[-1]:
        issues.append(
            ValidationIssue(
                "location.polygon.coordinates",
                "invalid_format",
                "Polygon linear ring must be closed (first point equals last point).",
            )
        )
        return issues
    if _has_self_intersection(normalized):
        issues.append(
            ValidationIssue(
                "location.polygon.coordinates",
                "self_intersection",
                "Polygon is self-intersecting. Provide a valid non-self-intersecting polygon.",
            )
        )
    return issues


def _has_self_intersection(ring: list[tuple[float, float]]) -> bool:
    segments = []
    for i in range(len(ring) - 1):
        segments.append((ring[i], ring[i + 1], i))
    for (a1, a2, i), (b1, b2, j) in combinations(segments, 2):
        if abs(i - j) <= 1:
            continue
        if i == 0 and j == len(segments) - 1:
            continue
        if _segments_intersect(a1, a2, b1, b2):
            return True
    return False


def _segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    o1 = orient(p1, p2, p3)
    o2 = orient(p1, p2, p4)
    o3 = orient(p3, p4, p1)
    o4 = orient(p3, p4, p2)
    return (o1 * o2 < 0) and (o3 * o4 < 0)
