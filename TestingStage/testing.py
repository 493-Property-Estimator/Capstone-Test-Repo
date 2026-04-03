#!/usr/bin/env python3
"""
Edmonton Property Bed & Bath Scraper
======================================
Fetches active MLS listings from Realtor.ca for Edmonton.

Requires:  pip install curl_cffi

Usage:
  python3 edmonton_property_scraper.py --limit 200
  python3 edmonton_property_scraper.py --min-beds 3 --min-baths 2 --limit 500
  python3 edmonton_property_scraper.py --type condo --max-price 500000
  python3 edmonton_property_scraper.py --limit 1000 --output results.csv
  python3 edmonton_property_scraper.py --debug   # dump raw JSON of 1 listing
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("ERROR: curl_cffi is not installed. Run:  pip install curl_cffi")
    sys.exit(1)

# ── Edmonton bounding box ──────────────────────────────────────────────────────
EDMONTON_BBOX = {
    "LatitudeMin":  "53.3951",
    "LatitudeMax":  "53.7162",
    "LongitudeMin": "-113.7137",
    "LongitudeMax": "-113.2686",
}

SEARCH_URL  = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"
HOMEPAGE    = "https://www.realtor.ca/"
PAGE_SIZE   = 200
RETRY_DELAY = 8    # seconds to wait before retrying a 403
MAX_RETRIES = 3

BUILDING_TYPE_IDS = {
    "house":     "1",
    "condo":     "2",
    "townhouse": "16",
}

FIELDNAMES = [
    "mls_number", "listing_id", "address", "neighbourhood", "postal_code",
    "price", "bedrooms", "bathrooms", "building_type", "ownership_type",
    "size_interior_sqft", "lot_size", "year_built",
    "latitude", "longitude", "listing_url",
]


# ── Session ────────────────────────────────────────────────────────────────────

def make_session() -> cffi_requests.Session:
    s = cffi_requests.Session(impersonate="chrome120")
    s.headers.update({
        "Referer":         "https://www.realtor.ca/",
        "Origin":          "https://www.realtor.ca",
        "Accept":          "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-CA,en;q=0.9,en-US;q=0.8",
    })
    return s


def warm_up(session: cffi_requests.Session):
    """Visit the homepage first so Incapsula issues session cookies."""
    try:
        print("  [warm-up] Visiting homepage to obtain session cookies...")
        r = session.get(HOMEPAGE, timeout=20)
        print(f"  [warm-up] Homepage status: {r.status_code}")
        time.sleep(3)
    except Exception as e:
        print(f"  [warm-up] Warning: {e}")


# ── HTTP with retry ────────────────────────────────────────────────────────────

def post_search(session: cffi_requests.Session, payload: dict) -> dict:
    """POST to realtor.ca; retries on 403 with backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        resp = session.post(SEARCH_URL, data=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 403:
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY * attempt
                print(f"  [403] Rate limited. Waiting {wait}s then retrying (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
                # Re-warm session cookies
                warm_up(session)
            else:
                raise RuntimeError(f"HTTP 403 after {MAX_RETRIES} retries — too many requests. Try again later.")
        else:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    raise RuntimeError("Max retries exceeded")


# ── Payload ────────────────────────────────────────────────────────────────────

def build_payload(page: int, price_min: int, price_max: int,
                  beds_min: int, baths_min: int, building_type_id: str) -> dict:
    p = {
        "CultureId":            "1",
        "ApplicationId":        "1",
        "PropertySearchTypeId": "1",
        "TransactionTypeId":    "2",
        "PriceMin":             str(price_min) if price_min else "0",
        "PriceMax":             str(price_max) if price_max else "0",
        "BedRange":             f"{beds_min}-0" if beds_min else "0-0",
        "BathRange":            f"{baths_min}-0" if baths_min else "0-0",
        "RecordsPerPage":       str(PAGE_SIZE),
        "CurrentPage":          str(page),
        "SortBy":               "6",
        "SortOrder":            "A",
        "Version":              "7.0",
        **EDMONTON_BBOX,
    }
    if building_type_id:
        p["BuildingTypeId"] = building_type_id
    return p


# ── Parse beds/baths from every known location in the response ─────────────────

def _get(d: dict, *keys, default=""):
    """Try multiple key names, return first non-empty value found."""
    for k in keys:
        v = d.get(k)
        if v not in (None, "", "0"):
            return str(v)
    return default


def parse_listing(item: dict) -> dict:
    """
    Realtor.ca search response structure (confirmed from reverse-engineering):

      item = {
        "Id": ...,
        "MlsNumber": ...,
        "Property": {
          "Price": ...,
          "Address": { "AddressText", "Latitude", "Longitude", "PostalCode" },
          "Building": {
            "BathroomTotal",   ← bathrooms (search endpoint)
            "Bedrooms",        ← bedrooms  (search endpoint)
            "SizeInterior",    ← m² string
            "Type",            ← "House", "Apartment", etc.
            "YearBuilt"
          },
          "OwnershipType": ...,
          "Land": { "SizeTotal" }
        },
        "Individual": [ { "Name", ... } ],
        "RelativeDetailsURL": ...
      }

    Some listings omit Building entirely and put beds/baths at the item level.
    We probe every known path.
    """
    prop     = item.get("Property", {})
    addr_obj = prop.get("Address", {})
    building = prop.get("Building") or {}
    land     = prop.get("Land") or {}

    # ── Address ────────────────────────────────────────────────────────────────
    full_addr = addr_obj.get("AddressText", "")
    parts     = [p.strip() for p in full_addr.split(",")]
    addr_line = parts[0] if parts else full_addr
    hood      = parts[1] if len(parts) > 1 else ""
    postal    = addr_obj.get("PostalCode", "")

    # ── Price ──────────────────────────────────────────────────────────────────
    price_num = "".join(c for c in prop.get("Price", "") if c.isdigit())

    # ── Bedrooms — probe ALL known paths ──────────────────────────────────────
    beds = _get(building, "Bedrooms", "BedroomTotal", "Bedroom")
    if not beds:
        beds = _get(prop,     "BedroomTotal", "Bedrooms")
    if not beds:
        beds = _get(item,     "BedroomTotal", "Bedrooms")

    # ── Bathrooms — probe ALL known paths ─────────────────────────────────────
    baths = _get(building, "BathroomTotal", "Bathrooms", "BathroomTotalInteger")
    if not baths:
        baths = _get(prop,    "BathroomTotal", "Bathrooms")
    if not baths:
        baths = _get(item,    "BathroomTotal", "Bathrooms")

    # ── Size ───────────────────────────────────────────────────────────────────
    size_raw  = building.get("SizeInterior", "")
    size_sqft = ""
    if size_raw:
        try:
            num = float("".join(c for c in size_raw if c.isdigit() or c == "."))
            # Realtor.ca sometimes returns sqft directly (large numbers) or m²
            size_sqft = str(round(num * 10.764)) if num < 1000 else str(round(num))
        except ValueError:
            size_sqft = size_raw

    url_part = item.get("RelativeDetailsURL", "")

    return {
        "mls_number":         item.get("MlsNumber", ""),
        "listing_id":         item.get("Id", ""),
        "address":            addr_line,
        "neighbourhood":      hood,
        "postal_code":        postal,
        "price":              price_num,
        "bedrooms":           beds,
        "bathrooms":          baths,
        "building_type":      _get(building, "Type") or prop.get("PropertyType", ""),
        "ownership_type":     prop.get("OwnershipType", ""),
        "size_interior_sqft": size_sqft,
        "lot_size":           land.get("SizeTotal", ""),
        "year_built":         building.get("YearBuilt", ""),
        "latitude":           addr_obj.get("Latitude", ""),
        "longitude":          addr_obj.get("Longitude", ""),
        "listing_url":        f"https://www.realtor.ca{url_part}" if url_part else "",
    }


# ── Debug mode: dump raw JSON of first listing ─────────────────────────────────

def debug_mode():
    print("DEBUG MODE — dumping raw JSON of first listing\n")
    session = make_session()
    warm_up(session)
    payload = build_payload(1, 200000, 800000, 3, 2, "")
    payload["RecordsPerPage"] = "1"
    data    = post_search(session, payload)
    results = data.get("Results", [])
    if not results:
        print("No results returned.")
        return
    item = results[0]
    print(json.dumps(item, indent=2, ensure_ascii=False))
    print("\n--- All leaf paths ---")
    def show_leaves(d, path=""):
        if isinstance(d, dict):
            for k, v in d.items():
                show_leaves(v, f"{path}.{k}" if path else k)
        elif isinstance(d, list):
            for i, v in enumerate(d[:2]):
                show_leaves(v, f"{path}[{i}]")
        else:
            print(f"  {path}: {repr(d)[:70]}")
    show_leaves(item)


# ── Main fetch loop ────────────────────────────────────────────────────────────

def fetch_listings(limit: int, price_min: int, price_max: int,
                   beds_min: int, baths_min: int,
                   building_type_id: str) -> list:
    session = make_session()
    warm_up(session)

    records     = []
    page        = 1
    total_found = None

    print(f"\n[Realtor.ca] Fetching Edmonton listings (limit={limit})...")
    if beds_min:  print(f"  Min bedrooms:  {beds_min}+")
    if baths_min: print(f"  Min bathrooms: {baths_min}+")
    if price_min: print(f"  Min price:     ${price_min:,}")
    if price_max: print(f"  Max price:     ${price_max:,}")
    print()

    while len(records) < limit:
        payload = build_payload(page, price_min, price_max,
                                beds_min, baths_min, building_type_id)
        try:
            data = post_search(session, payload)
        except RuntimeError as e:
            print(f"  ✗ {e}")
            break

        if total_found is None:
            paging      = data.get("Paging", {})
            total_found = int(paging.get("TotalRecords", 0))
            total_pages = int(paging.get("TotalPages", 1))
            to_collect  = min(limit, total_found)
            print(f"  Total matching: {total_found:,} | Collecting: {to_collect:,}")
            print()

        results = data.get("Results", [])
        if not results:
            print("  No results on this page — done.")
            break

        for item in results:
            if len(records) >= limit:
                break
            records.append(parse_listing(item))

        max_page = (limit + PAGE_SIZE - 1) // PAGE_SIZE
        print(f"  Page {page}/{min(total_pages, max_page)}: "
              f"{len(results)} listings | total: {len(records)}")

        if page >= total_pages or len(records) >= limit:
            break

        page += 1
        time.sleep(2.5)  # polite delay between pages

    return records


# ── Output helpers ─────────────────────────────────────────────────────────────

def write_csv(records: list, path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(f"\n✅ Saved {len(records)} records → {path}")


def print_table(records: list, max_rows: int = 25):
    if not records:
        print("\n⚠  No records returned.")
        return
    cols = ["address", "price", "bedrooms", "bathrooms",
            "building_type", "size_interior_sqft"]
    widths = {c: max(len(c), max(
        (len(str(r.get(c, ""))) for r in records[:max_rows]), default=0))
        for c in cols}
    print("\n" + "  ".join(c.upper().ljust(widths[c]) for c in cols))
    print("-" * (sum(widths.values()) + 2 * len(cols)))
    for r in records[:max_rows]:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
    if len(records) > max_rows:
        print(f"  ... and {len(records) - max_rows} more (all in CSV)")


def print_summary(records: list):
    if not records:
        return
    bed_vals   = [int(r["bedrooms"])    for r in records if str(r.get("bedrooms","")).isdigit()]
    bath_vals  = [float(r["bathrooms"]) for r in records
                  if r.get("bathrooms") and str(r["bathrooms"]).replace(".","").isdigit()]
    price_vals = [int(r["price"])       for r in records if str(r.get("price","")).isdigit()]

    print(f"\n{'='*52}")
    print("Summary")
    print(f"{'='*52}")
    print(f"Total listings:              {len(records):,}")
    print(f"With bedroom data:           {len(bed_vals):,}")
    print(f"With bathroom data:          {len(bath_vals):,}")
    if bed_vals:
        print(f"Avg bedrooms:                {sum(bed_vals)/len(bed_vals):.1f}  "
              f"(range {min(bed_vals)}–{max(bed_vals)})")
    if bath_vals:
        print(f"Avg bathrooms:               {sum(bath_vals)/len(bath_vals):.1f}  "
              f"(range {min(bath_vals):.0f}–{max(bath_vals):.0f})")
    if price_vals:
        print(f"Avg list price:              ${sum(price_vals)//len(price_vals):,}")
        print(f"Price range:                 ${min(price_vals):,} – ${max(price_vals):,}")
    print(f"{'='*52}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Scrape Edmonton property listings (bed/bath/price) from Realtor.ca.",
    )
    p.add_argument("--limit",     type=int, default=200)
    p.add_argument("--min-beds",  type=int, default=None)
    p.add_argument("--min-baths", type=int, default=None)
    p.add_argument("--min-price", type=int, default=None)
    p.add_argument("--max-price", type=int, default=None)
    p.add_argument("--type",      choices=["all","house","condo","townhouse"], default="all")
    p.add_argument("--output",    type=str, default="")
    p.add_argument("--debug",     action="store_true",
                   help="Dump raw JSON of 1 listing to diagnose field names")
    return p.parse_args()


def main():
    args = parse_args()

    if args.debug:
        debug_mode()
        return

    print(f"\n{'='*60}")
    print("Edmonton Property Bed & Bath Scraper")
    print(f"  Source:  Realtor.ca (active MLS listings)")
    print(f"  Run at:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    records = fetch_listings(
        limit=args.limit,
        price_min=args.min_price or 0,
        price_max=args.max_price or 0,
        beds_min=args.min_beds  or 0,
        baths_min=args.min_baths or 0,
        building_type_id=BUILDING_TYPE_IDS.get(args.type, ""),
    )

    print_summary(records)
    print_table(records)

    out = args.output or f"edmonton_listings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    write_csv(records, out)


if __name__ == "__main__":
    main()
