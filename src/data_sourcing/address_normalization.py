"""Address normalization helpers for Edmonton property matching."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


_PUNCT_RE = re.compile(r"[^A-Z0-9 ]+")
_SPACE_RE = re.compile(r"\s+")
_SUITE_RE = re.compile(r"\b(?:SUITE|UNIT|APT|APARTMENT|#)\s*([A-Z0-9-]+)\b")
_ADDRESS_RE = re.compile(
    r"^\s*(?:(?:SUITE|UNIT|APT|APARTMENT|#)\s*(?P<prefix_suite>[A-Z0-9-]+)\s+)?"
    r"(?P<house_number>\d+[A-Z0-9-]*)?\s*"
    r"(?P<street_name>.*?)"
    r"(?:\s+(?:SUITE|UNIT|APT|APARTMENT|#)\s*(?P<suffix_suite>[A-Z0-9-]+))?\s*$",
    re.IGNORECASE,
)
_STREET_TYPE_MAP = {
    "ST": "ST",
    "STREET": "ST",
    "STRT": "ST",
    "STRET": "ST",
    "STRRET": "ST",
    "AVE": "AVE",
    "AVENUE": "AVE",
    "AVNUE": "AVE",
    "AVENEU": "AVE",
    "AVENUEE": "AVE",
    "RD": "RD",
    "ROAD": "RD",
    "DR": "DR",
    "DRIVE": "DR",
    "DRV": "DR",
    "BLVD": "BLVD",
    "BOULEVARD": "BLVD",
    "BOULVARD": "BLVD",
    "CRT": "CRT",
    "COURT": "CRT",
    "CRES": "CRES",
    "CRESCENT": "CRES",
    "CRESCANT": "CRES",
    "PL": "PL",
    "PLACE": "PL",
    "TER": "TER",
    "TERRACE": "TER",
    "TERACE": "TER",
    "LN": "LN",
    "LANE": "LN",
    "LAEN": "LN",
    "TRL": "TRL",
    "TRAIL": "TRL",
    "TRAL": "TRL",
    "WAY": "WAY",
    "CLOSE": "CLOSE",
    "LINK": "LINK",
}
_DIRECTION_MAP = {
    "N": "N",
    "S": "S",
    "E": "E",
    "W": "W",
    "NORTH": "N",
    "SOUTH": "S",
    "EAST": "E",
    "WEST": "W",
    "NORTHWEST": "NW",
    "NORTHEAST": "NE",
    "SOUTHWEST": "SW",
    "SOUTHEAST": "SE",
}
_COMBINED_DIRECTIONS = {
    ("N", "W"): "NW",
    ("W", "N"): "NW",
    ("N", "E"): "NE",
    ("E", "N"): "NE",
    ("S", "W"): "SW",
    ("W", "S"): "SW",
    ("S", "E"): "SE",
    ("E", "S"): "SE",
}


@dataclass(frozen=True)
class NormalizedAddress:
    suite: str | None
    house_number: str | None
    street_name: str | None
    strict_street_name: str | None
    legal_description: str | None
    full_address_key: str
    strict_full_address_key: str
    address_key_without_suite: str
    strict_address_key_without_suite: str
    neighbourhood: str | None
    zoning: str | None
    lat: float | None
    lon: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_token(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text or None


def normalize_suite(value: Any) -> str | None:
    cleaned = _clean_token(value)
    if cleaned is None:
        return None
    match = _SUITE_RE.search(cleaned)
    if match:
        return match.group(1)
    return cleaned.removeprefix("UNIT ").removeprefix("SUITE ").strip() or None


def _normalize_direction_tokens(tokens: list[str]) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        token = _DIRECTION_MAP.get(tokens[index], tokens[index])
        if index + 1 < len(tokens):
            next_token = _DIRECTION_MAP.get(tokens[index + 1], tokens[index + 1])
            combined = _COMBINED_DIRECTIONS.get((token, next_token))
            if combined is not None:
                normalized.append(combined)
                index += 2
                continue
        normalized.append(token)
        index += 1
    return normalized


def normalize_street_name(value: Any, *, correct_typos: bool = True) -> str | None:
    cleaned = _clean_token(value)
    if cleaned is None:
        return None
    tokens = cleaned.split()
    normalized_tokens = _normalize_direction_tokens(tokens)
    if correct_typos:
        normalized_tokens = [_STREET_TYPE_MAP.get(token, token) for token in normalized_tokens]
    return " ".join(normalized_tokens)


def normalize_legal_description(value: Any) -> str | None:
    cleaned = _clean_token(value)
    if cleaned is None:
        return None
    tokens = cleaned.split()
    normalized_tokens = []
    for token in tokens:
        if token == "BLOCK":
            normalized_tokens.append("BLK")
        elif token == "LOT":
            normalized_tokens.append("LT")
        else:
            normalized_tokens.append(token)
    return " ".join(normalized_tokens)


def normalize_property_address(row: dict[str, Any]) -> NormalizedAddress:
    parsed_address = parse_address_components(row.get("address"))
    suite = normalize_suite(row.get("suite") or parsed_address.get("suite"))
    house_number = _clean_token(row.get("house_number") or parsed_address.get("house_number"))
    street_name = normalize_street_name(row.get("street_name") or parsed_address.get("street_name"))
    strict_street_name = normalize_street_name(
        row.get("street_name") or parsed_address.get("street_name"),
        correct_typos=False,
    )
    legal_description = normalize_legal_description(row.get("legal_description"))
    neighbourhood = _clean_token(row.get("neighbourhood"))
    zoning = _clean_token(row.get("zoning"))
    lat = _coerce_float(row.get("lat"))
    lon = _coerce_float(row.get("lon"))

    parts = [part for part in (house_number, street_name, suite) if part]
    full_address_key = " ".join(parts)
    strict_parts = [part for part in (house_number, strict_street_name, suite) if part]
    strict_full_address_key = " ".join(strict_parts)
    no_suite_parts = [part for part in (house_number, street_name) if part]
    address_key_without_suite = " ".join(no_suite_parts)
    strict_no_suite_parts = [part for part in (house_number, strict_street_name) if part]
    strict_address_key_without_suite = " ".join(strict_no_suite_parts)

    return NormalizedAddress(
        suite=suite,
        house_number=house_number,
        street_name=street_name,
        strict_street_name=strict_street_name,
        legal_description=legal_description,
        full_address_key=full_address_key,
        strict_full_address_key=strict_full_address_key,
        address_key_without_suite=address_key_without_suite,
        strict_address_key_without_suite=strict_address_key_without_suite,
        neighbourhood=neighbourhood,
        zoning=zoning,
        lat=lat,
        lon=lon,
    )


def parse_address_components(value: Any) -> dict[str, str | None]:
    cleaned = _clean_token(value)
    if cleaned is None:
        return {"suite": None, "house_number": None, "street_name": None}
    match = _ADDRESS_RE.match(cleaned)
    if not match:
        return {"suite": None, "house_number": None, "street_name": cleaned}
    street_name = normalize_street_name(match.group("street_name"))
    suite = normalize_suite(match.group("prefix_suite") or match.group("suffix_suite"))
    return {
        "suite": suite,
        "house_number": _clean_token(match.group("house_number")),
        "street_name": street_name,
    }


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
