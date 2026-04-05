from __future__ import annotations

from dataclasses import dataclass
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
    if location.get("coordinates"):
        issues.extend(validate_coordinates(location.get("coordinates")))
    if location.get("address"):
        issues.extend(validate_address(location.get("address")))
    if location.get("polygon"):
        issues.append(
            ValidationIssue(
                "location.polygon",
                "unsupported",
                "Polygon input is not supported in this backend yet.",
            )
        )
    if not (location.get("coordinates") or location.get("address") or location.get("canonical_location_id")):
        issues.append(
            ValidationIssue(
                "location",
                "missing_selector",
                "Provide address, coordinates, or canonical_location_id.",
            )
        )
    return issues
