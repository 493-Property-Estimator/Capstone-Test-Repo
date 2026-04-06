#!/usr/bin/env python3
"""Merge and clean REALTOR card CSVs, deduplicate by address, and enrich location fields.

Default inputs:
- edmonton_manual_realtor_cards.csv
- first_pass_edmonton_manual_realtor_cards.csv

Output columns:
- address, beds, baths, square_footage, price, link, neighborhood, lat, long
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import math
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

PRICE_RE = re.compile(r"\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?")
SQFT_RE = re.compile(r"(\d{2,6})\s*(?:sq\.?\s*ft|sqft)\b", re.IGNORECASE)
BED_BATH_NEAR_SQFT_RE = re.compile(
    r"(\d{1,2}(?:\.\d)?)\s+(\d{1,2}(?:\.\d)?)\s+(\d{2,6})\s*(?:sq\.?\s*ft|sqft)",
    re.IGNORECASE,
)
ADDRESS_RE = re.compile(
    r"(?:\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\s+)?(?:Apr\s+\d{1,2}\s+)?(?:False\s+)?"
    r"(?P<address>[^,]{4,160}?),\s*Edmonton,\s*Alberta",
    re.IGNORECASE,
)
BED_LABEL_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*(?:bed|beds|bedroom|bedrooms)\b", re.IGNORECASE)
BATH_LABEL_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*(?:bath|baths|bathroom|bathrooms)\b", re.IGNORECASE)
LAST_HTTP_ERROR = ""
ROAD_ABBREVIATIONS = {
    "AV": "AVENUE",
    "AVE": "AVENUE",
    "ST": "STREET",
    "RD": "ROAD",
    "DR": "DRIVE",
    "PL": "PLACE",
    "WY": "WAY",
    "BV": "BOULEVARD",
    "BLVD": "BOULEVARD",
    "CM": "COMMON",
    "CR": "CRESCENT",
    "PT": "POINT",
    "LI": "LINK",
    "LO": "LOOP",
    "LD": "LANDING",
    "TC": "TERRACE",
    "BA": "BAY",
    "CO": "COVE",
    "WD": "WOOD",
    "VG": "VILLAGE",
    "CL": "CLOSE",
    "CT": "COURT",
    "TR": "TRAIL",
    "GR": "GROVE",
    "PR": "PARK",
    "BN": "BEND",
    "LN": "LANE",
}


@dataclass
class CleanRow:
    address: str
    beds: str
    baths: str
    square_footage: str
    price: str
    link: str
    neighborhood: str
    lat: str
    long: str


def clean_spaces(text: str) -> str:
    return " ".join((text or "").replace("\n", " ").split()).strip()


def generate_address_variants(address: str) -> list[str]:
    base = clean_spaces(address).upper()
    if not base:
        return []
    base = base.replace(" - ", " ")
    base = re.sub(r"^\s*UNIT\s+\d+\s+", "", base)
    base = base.replace(" NORTH WEST ", " NW ")
    base = base.replace(" NORTH EAST ", " NE ")
    base = base.replace(" SOUTH WEST ", " SW ")
    base = base.replace(" SOUTH EAST ", " SE ")
    base = re.sub(r"\b([NS])\s+([EW])\b", r"\1\2", base)
    base = re.sub(
        r"\b(\d+)(AVENUE|AVE|AV|STREET|ST|ROAD|RD|DRIVE|DR|PLACE|PL|WAY|WY|BOULEVARD|BLVD|BV|"
        r"CRESCENT|CR|COURT|CT|TRAIL|TR|LINK|LI|LOOP|LO|LANDING|LD|TERRACE|TC|BAY|BA|COVE|CO|"
        r"WOOD|WD|CLOSE|CL|LANE|LN|POINT|PT|VILLAGE|VG|GROVE|GR|PARK|PR|BEND|BN)\b",
        r"\1 \2",
        base,
    )
    base = re.sub(r"\b(NW|NE|SW|SE)\s+\1\b", r"\1", base)
    base = re.sub(r"\b(AVENUE|AVE|AV)\s+(AVENUE|AVE|AV)\b", r"\1", base)
    base = re.sub(r"\s+", " ", base).strip()

    variants: list[str] = []

    def add_variant(v: str) -> None:
        candidate = clean_spaces(v).upper()
        candidate = re.sub(r"\b(NW|NE|SW|SE)\s+\1\b", r"\1", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate and candidate not in variants:
            variants.append(candidate)

    add_variant(base)

    # Expand common road abbreviations (e.g., AV -> AVENUE, WY -> WAY).
    tokens = base.split()
    expanded_tokens = [ROAD_ABBREVIATIONS.get(tok, tok) for tok in tokens]
    add_variant(" ".join(expanded_tokens))

    # Expand slash house numbers like 12041/43 67 ST NW into multiple civic variants.
    slash_match = re.match(r"^(?P<head>\d+)(?P<tail>(?:\s*/\s*\d+)+)\s+(?P<rest>.+)$", base)
    if slash_match:
        head = slash_match.group("head")
        rest = slash_match.group("rest")
        nums = [head] + re.findall(r"\d+", slash_match.group("tail"))
        for n in nums:
            candidate = f"{n} {rest}"
            add_variant(candidate)
            add_variant(" ".join(ROAD_ABBREVIATIONS.get(tok, tok) for tok in candidate.split()))

    # Expand hyphen civic ranges like 5607-5615 118 AVENUE.
    range_match = re.match(r"^(?P<a>\d+)-(?P<b>\d+)\s+(?P<rest>.+)$", base)
    if range_match:
        for n in [range_match.group("a"), range_match.group("b")]:
            candidate = f"{n} {range_match.group('rest')}"
            add_variant(candidate)
            add_variant(" ".join(ROAD_ABBREVIATIONS.get(tok, tok) for tok in candidate.split()))

    # Expand multiple leading civic numbers, use each as candidate house number.
    many_nums = re.match(r"^#?(?P<numlist>(?:\d+\s+){2,})(?P<rest>.+)$", base)
    if many_nums:
        nums = re.findall(r"\d+", many_nums.group("numlist"))
        rest = many_nums.group("rest").strip()
        for n in nums:
            candidate = f"{n} {rest}"
            add_variant(candidate)
            add_variant(" ".join(ROAD_ABBREVIATIONS.get(tok, tok) for tok in candidate.split()))

    # If unit-prefixed (e.g. #251 6079 MAYNARD WY NW), also try base address without unit.
    no_unit = re.sub(r"^#\s*[A-Z0-9-]+\s+", "", base)
    add_variant(no_unit)
    if no_unit:
        no_unit_expanded = " ".join(ROAD_ABBREVIATIONS.get(tok, tok) for tok in no_unit.split())
        add_variant(no_unit_expanded)

    # For some malformed records that repeat city quadrants or noise tokens.
    simplified = re.sub(r"\bNW NW\b", "NW", base)
    simplified = re.sub(r"\bNE NE\b", "NE", simplified)
    simplified = re.sub(r"\bSW SW\b", "SW", simplified)
    simplified = re.sub(r"\bSE SE\b", "SE", simplified)
    add_variant(simplified)

    # Remove solitary direction letters that often appear as noise before quadrant (e.g., "AV S NW").
    remove_single_cardinal = re.sub(r"\b([NSEW])\s+(NW|NE|SW|SE)\b", r"\2", base)
    add_variant(remove_single_cardinal)

    # Remove mobile-home park descriptors when present; keep civic portion.
    mh_stripped = re.sub(r"\s+-\s+.*$", "", base)
    mh_stripped = re.sub(r"\b(MH|MHP|PA|PARK|VILLAGE)\b.*$", "", mh_stripped).strip()
    add_variant(mh_stripped)
    if mh_stripped:
        add_variant(" ".join(ROAD_ABBREVIATIONS.get(tok, tok) for tok in mh_stripped.split()))

    return variants


def base_address_key(address: str) -> str:
    variants = generate_address_variants(address)
    if not variants:
        return ""
    return normalize_address_key(variants[0])


def normalize_address_key(address: str) -> str:
    x = clean_spaces(address).upper()
    x = re.sub(r"\bEDMONTON\b", "", x)
    x = re.sub(r"\bALBERTA\b", "", x)
    x = re.sub(r"[^A-Z0-9# ]+", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x


def clean_price(value: str) -> str:
    v = clean_spaces(value)
    if not v:
        return ""
    m = PRICE_RE.search(v)
    return m.group(0).replace(" ", "") if m else ""


def parse_address(raw_text: str, listing_url: str, existing_address: str) -> str:
    if clean_spaces(existing_address):
        return clean_spaces(existing_address)

    text = clean_spaces(raw_text)
    m = ADDRESS_RE.search(text)
    if m:
        address = clean_spaces(m.group("address"))
        if address.lower() != "address not available":
            return address

    # Fallback from REALTOR URL slug:
    # /real-estate/<id>/<address-part>-edmonton-<neighbourhood>
    slug = ""
    if listing_url and "/real-estate/" in listing_url:
        try:
            slug = listing_url.rstrip("/").split("/")[-1]
        except Exception:
            slug = ""
    if slug and "-edmonton-" in slug:
        address_slug = slug.split("-edmonton-")[0]
        address = address_slug.replace("-", " ").upper()
        address = re.sub(r"\s+", " ", address).strip()
        if address:
            return address

    return ""


def parse_beds_baths_sqft(raw_text: str, beds: str, baths: str, sqft: str) -> tuple[str, str, str]:
    beds_v = clean_spaces(str(beds))
    baths_v = clean_spaces(str(baths))
    sqft_v = clean_spaces(str(sqft))
    text = clean_spaces(raw_text)

    near = BED_BATH_NEAR_SQFT_RE.search(text)
    if near:
        if not beds_v:
            beds_v = near.group(1)
        if not baths_v:
            baths_v = near.group(2)
        if not sqft_v:
            sqft_v = near.group(3)

    if not sqft_v:
        sq = SQFT_RE.search(text)
        if sq:
            sqft_v = sq.group(1)

    if not beds_v:
        b = BED_LABEL_RE.search(text)
        if b:
            beds_v = b.group(1)

    if not baths_v:
        b = BATH_LABEL_RE.search(text)
        if b:
            baths_v = b.group(1)

    return beds_v, baths_v, sqft_v


def parse_price(raw_text: str, price: str) -> str:
    out = clean_price(price)
    if out:
        return out
    return clean_price(raw_text)


def pick_better_row(existing: CleanRow, incoming: CleanRow) -> CleanRow:
    def score(r: CleanRow) -> int:
        return sum(
            1
            for v in [
                r.address,
                r.beds,
                r.baths,
                r.square_footage,
                r.price,
                r.link,
            ]
            if clean_spaces(v)
        )

    s1 = score(existing)
    s2 = score(incoming)
    if s2 > s1:
        return incoming
    if s2 < s1:
        return existing
    # Tie-break: prefer row with link.
    if incoming.link and not existing.link:
        return incoming
    return existing


def http_get_json(url: str, timeout: float, retries: int = 3) -> Optional[dict]:
    global LAST_HTTP_ERROR
    req = Request(url, headers={"User-Agent": "realtor-cleaner/1.0"})
    max_attempts = max(1, retries + 1)
    for attempt in range(max_attempts):
        try:
            with urlopen(req, timeout=timeout) as resp:
                payload = resp.read().decode("utf-8", errors="replace")
                LAST_HTTP_ERROR = ""
                return json.loads(payload)
        except HTTPError as exc:
            LAST_HTTP_ERROR = f"HTTP {exc.code}: {exc.reason}"
            should_retry = exc.code == 429 or 500 <= exc.code < 600
            if should_retry and attempt < max_attempts - 1:
                retry_after = exc.headers.get("Retry-After") if getattr(exc, "headers", None) else None
                try:
                    wait_s = float(retry_after) if retry_after else min(30.0, 2.0**attempt)
                except Exception:
                    wait_s = min(30.0, 2.0**attempt)
                time.sleep(max(0.25, wait_s))
                continue
            return None
        except URLError as exc:
            LAST_HTTP_ERROR = f"URL error: {exc.reason}"
            if attempt < max_attempts - 1:
                time.sleep(min(10.0, 1.5**attempt))
                continue
            return None
        except Exception as exc:
            LAST_HTTP_ERROR = f"{type(exc).__name__}: {exc}"
            return None
    return None


def geocode_address(address: str, geocode_url_template: str, timeout: float, http_retries: int) -> tuple[Optional[float], Optional[float]]:
    query = quote_plus(f"{address}, Edmonton, Alberta")
    url = geocode_url_template.format(query=query)
    payload = http_get_json(url, timeout, retries=http_retries)
    if payload is None:
        return None, None

    if isinstance(payload, list) and payload:
        first = payload[0]
        lat = first.get("lat")
        lon = first.get("lon")
        try:
            return float(lat), float(lon)
        except Exception:
            return None, None

    if isinstance(payload, dict):
        lat = payload.get("lat")
        lon = payload.get("lon")
        try:
            return float(lat), float(lon)
        except Exception:
            return None, None

    return None, None


def resolve_address_local(address: str, resolve_url_template: str, timeout: float, http_retries: int) -> tuple[Optional[float], Optional[float]]:
    if not clean_spaces(resolve_url_template):
        return None, None
    query = quote_plus(address)
    url = resolve_url_template.format(query=query)
    payload = http_get_json(url, timeout, retries=http_retries)
    if not isinstance(payload, dict):
        return None, None

    location = payload.get("location")
    if isinstance(location, dict):
        coords = location.get("coordinates")
        if isinstance(coords, dict):
            lat = coords.get("lat")
            lng = coords.get("lng")
            try:
                return float(lat), float(lng)
            except Exception:
                pass

    candidates = payload.get("candidates")
    if isinstance(candidates, list) and candidates:
        coords = candidates[0].get("coordinates")
        if isinstance(coords, dict):
            lat = coords.get("lat")
            lng = coords.get("lng")
            try:
                return float(lat), float(lng)
            except Exception:
                return None, None
    return None, None


def split_house_and_street(variant: str) -> tuple[str, str]:
    text = clean_spaces(variant).upper()
    if not text:
        return "", ""
    # Remove leading suite markers like "#1 & 2" while keeping civic number.
    text = re.sub(r"^UNIT\s+\d+\s+", "", text)
    text = re.sub(r"^\d+\s*-\s+", "", text)
    text = re.sub(r"^#\s*[0-9A-Z]+(?:\s*&\s*[0-9A-Z]+)*\s+", "", text)
    parts = text.split()
    if not parts:
        return "", ""
    numeric_tokens = [(i, t) for i, t in enumerate(parts) if re.match(r"^\d+[A-Z]?$", t)]
    house_index = -1
    house = ""
    if numeric_tokens:
        # Prefer likely civic number over suite-like leading small number.
        if len(numeric_tokens) >= 2:
            i0, t0 = numeric_tokens[0]
            i1, t1 = numeric_tokens[1]
            if len(re.sub(r"[A-Z]+$", "", t0)) <= 3 and len(re.sub(r"[A-Z]+$", "", t1)) >= 4:
                house_index, house = i1, t1
            else:
                house_index, house = i0, t0
        else:
            house_index, house = numeric_tokens[0]
    if house_index < 0:
        return "", ""
    street = " ".join(parts[house_index + 1 :]).strip()
    return house, street


def normalize_street_for_match(street: str) -> str:
    s = clean_spaces(street).upper()
    s = s.replace(".", "")
    s = re.sub(r"\bNORTH WEST\b", "NW", s)
    s = re.sub(r"\bNORTH EAST\b", "NE", s)
    s = re.sub(r"\bSOUTH WEST\b", "SW", s)
    s = re.sub(r"\bSOUTH EAST\b", "SE", s)
    toks = [ROAD_ABBREVIATIONS.get(tok, tok) for tok in s.split()]
    s = " ".join(toks)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def resolve_address_sqlite(variant: str, conn: sqlite3.Connection) -> tuple[Optional[float], Optional[float], str]:
    house, street = split_house_and_street(variant)
    if not house or not street:
        return None, None, "not_a_civic_address"
    street_norm = normalize_street_for_match(street)
    house_numeric = re.sub(r"[A-Z]+$", "", house)

    queries = [
        ("exact", "SELECT lat, lon FROM property_locations_prod WHERE house_number = ? AND UPPER(street_name) = ? LIMIT 1", (house, street_norm)),
        ("exact_numeric_house", "SELECT lat, lon FROM property_locations_prod WHERE house_number = ? AND UPPER(street_name) = ? LIMIT 1", (house_numeric, street_norm)),
    ]
    # Fallback: if variant has directional suffix, also try matching without suffix.
    street_no_quad = re.sub(r"\s+(NW|NE|SW|SE)$", "", street).strip()
    if street_no_quad and street_no_quad != street:
        queries.append(
            (
                "prefix_no_quad",
                "SELECT lat, lon FROM property_locations_prod WHERE house_number = ? AND UPPER(street_name) LIKE ? LIMIT 1",
                (house_numeric or house, f"{normalize_street_for_match(street_no_quad)}%"),
            )
        )

    for label, sql, params in queries:
        row = conn.execute(sql, params).fetchone()
        if row and row[0] is not None and row[1] is not None:
            return float(row[0]), float(row[1]), f"sqlite:{label}"

    # Fuzzy fallback on same house number.
    candidates = conn.execute(
        "SELECT DISTINCT UPPER(street_name), lat, lon FROM property_locations_prod WHERE house_number = ?",
        (house_numeric or house,),
    ).fetchall()
    best = None
    best_score = 0.0
    for cand_street, lat, lon in candidates:
        cand_norm = normalize_street_for_match(cand_street or "")
        if not cand_norm:
            continue
        score = difflib.SequenceMatcher(None, street_norm, cand_norm).ratio()
        if street_norm.split() and cand_norm.split() and street_norm.split()[0] == cand_norm.split()[0]:
            score += 0.15
        if score > best_score:
            best_score = score
            best = (lat, lon, cand_norm)
    if best and best[0] is not None and best[1] is not None and best_score >= 0.74:
        return float(best[0]), float(best[1]), f"sqlite:fuzzy:{best_score:.2f}:{best[2]}"
    return None, None, "sqlite:no_match"


def snap_with_osrm(lat: float, lon: float, osrm_nearest_url_template: str, timeout: float, http_retries: int) -> tuple[float, float]:
    if not clean_spaces(osrm_nearest_url_template):
        return lat, lon
    url = osrm_nearest_url_template.format(lat=lat, lon=lon)
    payload = http_get_json(url, timeout, retries=http_retries)
    if not isinstance(payload, dict):
        return lat, lon
    waypoints = payload.get("waypoints")
    if not isinstance(waypoints, list) or not waypoints:
        return lat, lon
    location = waypoints[0].get("location")
    if not isinstance(location, list) or len(location) < 2:
        return lat, lon
    try:
        snapped_lon = float(location[0])
        snapped_lat = float(location[1])
        return snapped_lat, snapped_lon
    except Exception:
        return lat, lon


def reverse_neighborhood(lat: float, lon: float, reverse_url_template: str, timeout: float, http_retries: int) -> str:
    url = reverse_url_template.format(lat=lat, lon=lon)
    payload = http_get_json(url, timeout, retries=http_retries)
    if not isinstance(payload, dict):
        return ""

    addr = payload.get("address")
    if not isinstance(addr, dict):
        return ""

    for key in [
        "neighbourhood",
        "neighborhood",
        "suburb",
        "city_district",
        "quarter",
        "residential",
        "hamlet",
    ]:
        value = addr.get(key)
        if value:
            return clean_spaces(str(value))
    return ""


def add_enrich_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--local-db-path",
        default="src/data_sourcing/open_data.db",
        help="Local SQLite DB path used for offline address->lat/lon resolution.",
    )
    parser.add_argument(
        "--skip-local-db-resolver",
        action="store_true",
        help="Skip local SQLite resolver and only use API-based resolvers.",
    )
    parser.add_argument(
        "--skip-external-geocoder",
        action="store_true",
        help="Do not call external HTTP resolvers/geocoders; only use imputation + local SQLite resolver.",
    )
    parser.add_argument(
        "--skip-geocode-fallback",
        action="store_true",
        help="Skip public geocode endpoint fallback but still allow --resolve-url-template.",
    )
    parser.add_argument(
        "--resolve-url-template",
        default="",
        help="Optional local address resolver template with {query}, e.g. http://localhost:8000/api/v1/search/resolve?q={query}&provider=db",
    )
    parser.add_argument(
        "--geocode-url-template",
        default="https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q={query}",
        help="Forward geocode endpoint template. Must include {query} placeholder.",
    )
    parser.add_argument(
        "--reverse-url-template",
        default="https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}",
        help="Reverse geocode endpoint template. Must include {lat} and {lon} placeholders.",
    )
    parser.add_argument(
        "--osrm-nearest-url-template",
        default="http://localhost:5000/nearest/v1/driving/{lon},{lat}?number=1",
        help="OSRM nearest endpoint template (optional). Must include {lat} and {lon}.",
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=1.2,
        help="Delay between enrichment calls to avoid rate limiting.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=8.0,
        help="HTTP timeout per request.",
    )
    parser.add_argument(
        "--max-enrich",
        type=int,
        default=0,
        help="If > 0, enrich only this many rows (for quick tests).",
    )
    parser.add_argument(
        "--no-neighborhood-update",
        action="store_true",
        help="Only fill lat/long; do not overwrite the neighborhood column from reverse geocoding.",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=100,
        help="Checkpoint save frequency in processed rows during enrich (0 disables periodic checkpoints).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip rows that already have both lat and long set.",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=3,
        help="Retries per HTTP call for transient errors (429/5xx/network).",
    )
    parser.add_argument(
        "--geocode-failures-output",
        default="",
        help="Optional CSV path for addresses that failed to resolve coordinates.",
    )
    parser.add_argument(
        "--retry-failures-from",
        default="",
        help="Optional geocode-failures CSV path from a previous run; enrich will target only those addresses.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean and merge Edmonton REALTOR CSV rows.")
    subparsers = parser.add_subparsers(dest="command")

    parse_cmd = subparsers.add_parser("parse", help="Stage 1: parse + clean + dedupe input listing CSVs.")
    parse_cmd.add_argument(
        "--input",
        nargs="+",
        default=["edmonton_manual_realtor_cards.csv", "first_pass_edmonton_manual_realtor_cards.csv"],
        help="Input raw listing CSV files to merge.",
    )
    parse_cmd.add_argument(
        "--output",
        default="cleaned_edmonton_realtor_cards.csv",
        help="Output parsed CSV path.",
    )

    enrich_cmd = subparsers.add_parser("enrich", help="Stage 2: read parsed CSV and fill lat/long (and neighborhood).")
    enrich_cmd.add_argument(
        "--input",
        default="cleaned_edmonton_realtor_cards.csv",
        help="Input parsed CSV path.",
    )
    enrich_cmd.add_argument(
        "--output",
        default="cleaned_edmonton_realtor_cards.csv",
        help="Output enriched CSV path.",
    )
    add_enrich_args(enrich_cmd)

    all_cmd = subparsers.add_parser("all", help="Run stage 1 parse then stage 2 enrich in sequence.")
    all_cmd.add_argument(
        "--input",
        nargs="+",
        default=["edmonton_manual_realtor_cards.csv", "first_pass_edmonton_manual_realtor_cards.csv"],
        help="Input raw listing CSV files to merge.",
    )
    all_cmd.add_argument(
        "--parsed-output",
        default="cleaned_edmonton_realtor_cards.csv",
        help="Output path for parsed stage result.",
    )
    all_cmd.add_argument(
        "--output",
        default="cleaned_edmonton_realtor_cards.csv",
        help="Final output path for enriched CSV.",
    )
    add_enrich_args(all_cmd)
    return parser


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [dict(row) for row in reader]


def read_clean_rows(path: Path) -> list[CleanRow]:
    rows = read_rows(path)
    out: list[CleanRow] = []
    for row in rows:
        out.append(
            CleanRow(
                address=clean_spaces(row.get("address", "") or ""),
                beds=clean_spaces(row.get("beds", "") or ""),
                baths=clean_spaces(row.get("baths", "") or ""),
                square_footage=clean_spaces(row.get("square_footage", "") or row.get("sqft", "") or ""),
                price=clean_spaces(row.get("price", "") or ""),
                link=clean_spaces(row.get("link", "") or row.get("listing_url", "") or ""),
                neighborhood=clean_spaces(row.get("neighborhood", "") or row.get("neighbourhood", "") or ""),
                lat=clean_spaces(row.get("lat", "") or ""),
                long=clean_spaces(row.get("long", "") or row.get("lon", "") or ""),
            )
        )
    return out


def write_rows(path: Path, rows: list[CleanRow]) -> None:
    fieldnames = ["address", "beds", "baths", "square_footage", "price", "link", "neighborhood", "lat", "long"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "address": row.address,
                    "beds": row.beds,
                    "baths": row.baths,
                    "square_footage": row.square_footage,
                    "price": row.price,
                    "link": row.link,
                    "neighborhood": row.neighborhood,
                    "lat": row.lat,
                    "long": row.long,
                }
            )


def write_failures(path: Path, failures: list[dict[str, str]]) -> None:
    fieldnames = [
        "address",
        "normalized_address",
        "db_error",
        "resolver_error",
        "geocode_error",
        "error",
        "attempted_queries",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in failures:
            writer.writerow(
                {
                    "address": row.get("address", ""),
                    "normalized_address": row.get("normalized_address", ""),
                    "db_error": row.get("db_error", ""),
                    "resolver_error": row.get("resolver_error", ""),
                    "geocode_error": row.get("geocode_error", ""),
                    "error": row.get("error", ""),
                    "attempted_queries": row.get("attempted_queries", ""),
                }
            )


def load_failure_address_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.exists():
        return keys
    for row in read_rows(path):
        normalized = clean_spaces(row.get("normalized_address", "") or "")
        address = clean_spaces(row.get("address", "") or "")
        if normalized:
            keys.add(normalized.upper())
        elif address:
            keys.add(normalize_address_key(address))
    return keys


def run_parse(input_paths: list[Path], output_path: Path) -> tuple[int, int, int]:
    missing = [str(p) for p in input_paths if not p.exists()]
    if missing:
        print(f"Missing input files: {', '.join(missing)}", file=sys.stderr)
        return 1, 0, 0

    total_input_rows = 0
    dedup_map: dict[str, CleanRow] = {}
    dropped_no_address = 0

    for path in input_paths:
        rows = read_rows(path)
        total_input_rows += len(rows)

        for raw in rows:
            raw_text = raw.get("raw_text", "") or ""
            listing_url = clean_spaces(raw.get("listing_url", "") or "")
            address = parse_address(raw_text, listing_url, raw.get("address", "") or "")
            beds, baths, sqft = parse_beds_baths_sqft(
                raw_text,
                raw.get("beds", "") or "",
                raw.get("baths", "") or "",
                raw.get("sqft", "") or "",
            )
            price = parse_price(raw_text, raw.get("price", "") or "")
            neighborhood = clean_spaces(raw.get("neighbourhood", "") or raw.get("neighborhood", "") or "")

            if not address:
                dropped_no_address += 1
                continue

            cleaned = CleanRow(
                address=address,
                beds=beds,
                baths=baths,
                square_footage=sqft,
                price=price,
                link=listing_url,
                neighborhood=neighborhood,
                lat="",
                long="",
            )

            key = normalize_address_key(address)
            if key in dedup_map:
                dedup_map[key] = pick_better_row(dedup_map[key], cleaned)
            else:
                dedup_map[key] = cleaned

    dedup_rows = list(dedup_map.values())
    write_rows(output_path, dedup_rows)
    print(f"Parse stage input rows total: {total_input_rows}")
    print(f"Parse stage rows dropped (could not parse address): {dropped_no_address}")
    print(f"Parse stage rows after dedupe (saved): {len(dedup_rows)}")
    print(f"Parse stage output file: {output_path}")
    return 0, total_input_rows, len(dedup_rows)


def run_enrich(
    input_path: Path,
    output_path: Path,
    local_db_path: str,
    skip_local_db_resolver: bool,
    skip_external_geocoder: bool,
    skip_geocode_fallback: bool,
    resolve_url_template: str,
    geocode_url_template: str,
    reverse_url_template: str,
    osrm_nearest_url_template: str,
    request_delay_seconds: float,
    timeout_seconds: float,
    max_enrich: int,
    no_neighborhood_update: bool,
    save_every: int,
    resume: bool,
    http_retries: int,
    geocode_failures_output: str,
    retry_failures_from: str,
) -> int:
    if not input_path.exists():
        print(f"Missing input file: {input_path}", file=sys.stderr)
        return 1

    dedup_rows = read_clean_rows(input_path)
    enriched = 0
    imputed_from_existing = 0
    geocode_failures = 0
    reverse_failures = 0
    printed_first_geocode_error = False
    failure_rows: list[dict[str, str]] = []
    failure_path = (
        Path(geocode_failures_output)
        if clean_spaces(geocode_failures_output)
        else output_path.with_name(f"{output_path.stem}_geocode_failures.csv")
    )
    retry_only_keys: set[str] = set()
    if clean_spaces(retry_failures_from):
        retry_path = Path(retry_failures_from)
        if not retry_path.exists():
            print(f"Missing retry-failures file: {retry_path}", file=sys.stderr)
            return 1
        retry_only_keys = load_failure_address_keys(retry_path)
        print(f"Loaded {len(retry_only_keys)} failed addresses from {retry_path}", flush=True)

    db_conn: Optional[sqlite3.Connection] = None
    if not skip_local_db_resolver:
        db_path = Path(local_db_path)
        if db_path.exists():
            db_conn = sqlite3.connect(str(db_path))
        else:
            print(f"Local DB not found at {db_path}; continuing without local DB resolver.", flush=True)
    def has_coords(row: CleanRow) -> bool:
        return bool(clean_spaces(row.lat) and clean_spaces(row.long))

    known_coords_by_base: dict[str, tuple[str, str]] = {}
    for row in dedup_rows:
        if not has_coords(row):
            continue
        key = base_address_key(row.address)
        if key and key not in known_coords_by_base:
            known_coords_by_base[key] = (row.lat, row.long)

    candidate_indexes = []
    for idx, row in enumerate(dedup_rows):
        if not row.address:
            continue
        if retry_only_keys:
            addr_key = normalize_address_key(row.address)
            if addr_key not in retry_only_keys:
                continue
        if resume and has_coords(row):
            continue
        candidate_indexes.append(idx)

    total_to_enrich = len(candidate_indexes) if max_enrich <= 0 else min(max_enrich, len(candidate_indexes))
    selected_indexes = candidate_indexes[:total_to_enrich]

    enrich_start = time.time()
    print(f"Enrichment progress: 0/{total_to_enrich} processed | remaining: {total_to_enrich}", flush=True)

    try:
        for processed_idx, row_index in enumerate(selected_indexes, start=1):
            row = dedup_rows[row_index]
            resolver_error = ""
            geocoder_error = ""
            db_error = ""
            attempt_logs: list[str] = []
            lat: Optional[float] = None
            lon: Optional[float] = None
            variants = generate_address_variants(row.address)

            # First attempt: infer coordinates from already-resolved rows with same base civic address.
            row_base_key = base_address_key(row.address)
            if row_base_key and row_base_key in known_coords_by_base:
                cached_lat, cached_lon = known_coords_by_base[row_base_key]
                row.lat = cached_lat
                row.long = cached_lon
                imputed_from_existing += 1
                enriched += 1
                attempt_logs.append(f"impute:ok:{row_base_key}")
                elapsed = max(time.time() - enrich_start, 1e-6)
                rate = processed_idx / elapsed
                remaining = total_to_enrich - processed_idx
                eta_seconds = int(math.ceil(remaining / rate)) if rate > 0 else 0
                print(
                    f"Enrichment progress: {processed_idx}/{total_to_enrich} processed | "
                    f"remaining: {remaining} | enriched: {enriched} | geocode_failures: {geocode_failures} | "
                    f"reverse_fallbacks: {reverse_failures} | ETA: ~{eta_seconds}s",
                    flush=True,
                )
                if save_every > 0 and (processed_idx % save_every == 0):
                    write_rows(output_path, dedup_rows)
                    print(f"Checkpoint saved at {processed_idx}/{total_to_enrich}: {output_path}", flush=True)
                continue

            if db_conn is not None:
                for variant in variants:
                    lat, lon, db_status = resolve_address_sqlite(variant, db_conn)
                    if lat is not None and lon is not None:
                        attempt_logs.append(f"{db_status}:ok:{variant}")
                        break
                    db_error = db_status
                    attempt_logs.append(f"{db_status}:fail:{variant}")

            if (not skip_external_geocoder) and clean_spaces(resolve_url_template):
                for variant in variants:
                    lat, lon = resolve_address_local(variant, resolve_url_template, timeout_seconds, http_retries)
                    if lat is not None and lon is not None:
                        attempt_logs.append(f"resolver:ok:{variant}")
                        break
                    reason = LAST_HTTP_ERROR or "No match"
                    resolver_error = reason
                    attempt_logs.append(f"resolver:fail:{variant}:{reason}")

            if (not skip_external_geocoder) and (not skip_geocode_fallback) and (lat is None or lon is None):
                for variant in variants:
                    lat, lon = geocode_address(variant, geocode_url_template, timeout_seconds, http_retries)
                    if lat is not None and lon is not None:
                        attempt_logs.append(f"geocoder:ok:{variant}")
                        break
                    reason = LAST_HTTP_ERROR or "No match"
                    geocoder_error = reason
                    attempt_logs.append(f"geocoder:fail:{variant}:{reason}")
            if lat is None or lon is None:
                geocode_failures += 1
                final_error = geocoder_error or resolver_error or db_error or "No coordinates returned"
                failure_rows.append(
                    {
                        "address": row.address,
                        "normalized_address": normalize_address_key(row.address),
                        "db_error": db_error,
                        "resolver_error": resolver_error,
                        "geocode_error": geocoder_error,
                        "error": final_error,
                        "attempted_queries": " | ".join(attempt_logs),
                    }
                )
                if not printed_first_geocode_error and LAST_HTTP_ERROR:
                    print(f"First geocode error: {LAST_HTTP_ERROR}", flush=True)
                    printed_first_geocode_error = True
                elapsed = max(time.time() - enrich_start, 1e-6)
                rate = processed_idx / elapsed
                remaining = total_to_enrich - processed_idx
                eta_seconds = int(math.ceil(remaining / rate)) if rate > 0 else 0
                print(
                    f"Enrichment progress: {processed_idx}/{total_to_enrich} processed | "
                    f"remaining: {remaining} | enriched: {enriched} | geocode_failures: {geocode_failures} | "
                    f"reverse_fallbacks: {reverse_failures} | ETA: ~{eta_seconds}s",
                    flush=True,
                )
                if save_every > 0 and (processed_idx % save_every == 0):
                    write_rows(output_path, dedup_rows)
                    print(f"Checkpoint saved at {processed_idx}/{total_to_enrich}: {output_path}", flush=True)
                continue

            # Snap to nearest road node using OSRM (if endpoint is reachable).
            lat, lon = snap_with_osrm(lat, lon, osrm_nearest_url_template, timeout_seconds, http_retries)
            row.lat = f"{lat:.7f}"
            row.long = f"{lon:.7f}"
            if row_base_key:
                known_coords_by_base[row_base_key] = (row.lat, row.long)

            if not no_neighborhood_update:
                neighborhood = reverse_neighborhood(lat, lon, reverse_url_template, timeout_seconds, http_retries)
                if neighborhood:
                    row.neighborhood = neighborhood
                else:
                    reverse_failures += 1

            enriched += 1
            if request_delay_seconds > 0:
                time.sleep(request_delay_seconds)

            elapsed = max(time.time() - enrich_start, 1e-6)
            rate = processed_idx / elapsed
            remaining = total_to_enrich - processed_idx
            eta_seconds = int(math.ceil(remaining / rate)) if rate > 0 else 0
            print(
                f"Enrichment progress: {processed_idx}/{total_to_enrich} processed | "
                f"remaining: {remaining} | enriched: {enriched} | geocode_failures: {geocode_failures} | "
                f"reverse_fallbacks: {reverse_failures} | ETA: ~{eta_seconds}s",
                flush=True,
            )
            if save_every > 0 and (processed_idx % save_every == 0):
                write_rows(output_path, dedup_rows)
                print(f"Checkpoint saved at {processed_idx}/{total_to_enrich}: {output_path}", flush=True)
    except KeyboardInterrupt:
        write_rows(output_path, dedup_rows)
        if db_conn is not None:
            db_conn.close()
        print(f"Interrupted. Progress saved to: {output_path}", flush=True)
        return 130

    write_rows(output_path, dedup_rows)
    write_failures(failure_path, failure_rows)
    if db_conn is not None:
        db_conn.close()
    print(f"Enrich stage input rows: {len(dedup_rows)}")
    print(f"Rows targeted for enrichment: {total_to_enrich}")
    print(f"Rows enriched with lat/long: {enriched}")
    print(f"Rows imputed from existing coordinates: {imputed_from_existing}")
    print(f"Geocode failures: {geocode_failures}")
    print(f"Geocode failures file: {failure_path}")
    if not no_neighborhood_update:
        print(f"Reverse-neighborhood fallbacks: {reverse_failures}")
    print(f"Enrich stage output file: {output_path}")
    return 0


def main() -> int:
    parser = build_parser()
    argv = sys.argv[1:]
    if not argv or argv[0] not in {"parse", "enrich", "all"}:
        # Default behavior: run both stages when no subcommand is provided.
        argv = ["all", *argv]
    args = parser.parse_args(argv)
    command = args.command or "all"
    if command == "parse":
        status, _, _ = run_parse([Path(p) for p in args.input], Path(args.output))
        return status
    if command == "enrich":
        return run_enrich(
            input_path=Path(args.input),
            output_path=Path(args.output),
            local_db_path=args.local_db_path,
            skip_local_db_resolver=args.skip_local_db_resolver,
            skip_external_geocoder=args.skip_external_geocoder,
            skip_geocode_fallback=args.skip_geocode_fallback,
            resolve_url_template=args.resolve_url_template,
            geocode_url_template=args.geocode_url_template,
            reverse_url_template=args.reverse_url_template,
            osrm_nearest_url_template=args.osrm_nearest_url_template,
            request_delay_seconds=args.request_delay_seconds,
            timeout_seconds=args.timeout_seconds,
            max_enrich=args.max_enrich,
            no_neighborhood_update=args.no_neighborhood_update,
            save_every=args.save_every,
            resume=args.resume,
            http_retries=args.http_retries,
            geocode_failures_output=args.geocode_failures_output,
            retry_failures_from=args.retry_failures_from,
        )
    if command == "all":
        status, _, _ = run_parse([Path(p) for p in args.input], Path(args.parsed_output))
        if status != 0:
            return status
        return run_enrich(
            input_path=Path(args.parsed_output),
            output_path=Path(args.output),
            local_db_path=args.local_db_path,
            skip_local_db_resolver=args.skip_local_db_resolver,
            skip_external_geocoder=args.skip_external_geocoder,
            skip_geocode_fallback=args.skip_geocode_fallback,
            resolve_url_template=args.resolve_url_template,
            geocode_url_template=args.geocode_url_template,
            reverse_url_template=args.reverse_url_template,
            osrm_nearest_url_template=args.osrm_nearest_url_template,
            request_delay_seconds=args.request_delay_seconds,
            timeout_seconds=args.timeout_seconds,
            max_enrich=args.max_enrich,
            no_neighborhood_update=args.no_neighborhood_update,
            save_every=args.save_every,
            resume=args.resume,
            http_retries=args.http_retries,
            geocode_failures_output=args.geocode_failures_output,
            retry_failures_from=args.retry_failures_from,
        )
    print(f"Unknown command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
