#!/usr/bin/env python3
"""
Semi-manual REALTOR.ca map-card scraper (Playwright + CDP).

This script connects to a locally running Chromium-based browser (Chrome/Brave)
over the DevTools protocol and scrapes the currently visible listing “cards” on
the REALTOR.ca map search page.

Quick start
-----------
1) Install dependencies (not part of the core app requirements):
   - `pip install playwright requests`
   - `python3 -m playwright install chromium`

2) Start a browser with remote debugging enabled (example):
   - `brave-browser --remote-debugging-port=9222`

3) Open a REALTOR.ca map search and ensure listing cards are visible.

4) Run from the repo root:
   - `python3 scripts/manual_bed_bath.py --help`

Outputs
-------
- CSV (default `edmonton_manual_realtor_cards.csv`)
- Progress file (default `completed_neighbourhoods.txt`) to resume runs
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Iterable

import requests
from playwright.sync_api import sync_playwright

OUT_CSV = "edmonton_manual_realtor_cards.csv"
DEBUG_HTML = "debug_visible_map.html"
CDP_URL = "http://127.0.0.1:9222"
REQUEST_TIMEOUT = 30
PROGRESS_FILE = "completed_neighbourhoods.txt"

# Resume controls
# START_FROM = "Evergreen"      # set to None to start from the beginning of remaining
START_FROM = ""      # set to None to start from the beginning of remaining
FORCE_REDO = {}     # neighbourhoods to ask again even if already completed

NEIGHBOURHOOD_DATA_URL = "https://data.edmonton.ca/resource/3b6m-fezs.json?$limit=1000"

CSV_FIELDS = [
    "neighbourhood",
    "price",
    "address",
    "beds",
    "baths",
    "sqft",
    "listing_url",
    "raw_text",
]


def clean_text(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def unique_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def is_probably_residential(name: str) -> bool:
    blocked_terms = [
        "industrial",
        "energy park",
        "transportation",
        "corridor",
        "northlands",
        "rampart",
        "mistatim",
        "big lake",
    ]
    lower = name.lower()
    return not any(term in lower for term in blocked_terms)


def fetch_edmonton_neighbourhoods() -> list[str]:
    resp = requests.get(NEIGHBOURHOOD_DATA_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    names = []
    for row in data:
        name = row.get("name_mixed") or row.get("neighbourhood_name") or row.get("name")
        if name:
            names.append(name.strip())

    names = sorted(set(names))
    return [n for n in names if is_probably_residential(n)]


def ensure_csv_exists(path: Path) -> None:
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()


def load_existing_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_existing_keys(path: Path) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    if not path.exists():
        return keys

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keys.add((
                clean_text(row.get("neighbourhood")),
                clean_text(row.get("listing_url")),
                clean_text(row.get("address")),
            ))
    return keys


def rewrite_csv_without_neighbourhoods(path: Path, neighbourhoods_to_remove: set[str]) -> None:
    if not path.exists() or not neighbourhoods_to_remove:
        return

    rows = load_existing_rows(path)
    kept = [
        row for row in rows
        if clean_text(row.get("neighbourhood")) not in neighbourhoods_to_remove
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(kept)


def load_completed_progress(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        clean_text(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if clean_text(line)
    }


def write_completed_progress(path: Path, completed: set[str]) -> None:
    lines = sorted(completed)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def append_completed_progress(path: Path, neighbourhood: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(neighbourhood + "\n")


def append_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerows(rows)


def parse_card_text(text: str) -> tuple[str, str, str, str, str]:
    price_match = re.search(r"\$\s?[\d,]+(?:\.\d{2})?", text)
    bed_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:bed|beds|bedroom|bedrooms)\b", text, re.I)
    bath_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:bath|baths|bathroom|bathrooms)\b", text, re.I)
    sqft_match = re.search(r"([\d,]+)\s*(?:sq\.?\s*ft\.?|sqft)", text, re.I)

    lines = [clean_text(x) for x in text.split("\n") if clean_text(x)]
    address = ""

    if lines:
        for i, line in enumerate(lines):
            if "$" in line and i + 1 < len(lines):
                address = lines[i + 1]
                break

    price = price_match.group(0) if price_match else ""
    beds = bed_match.group(1) if bed_match else ""
    baths = bath_match.group(1) if bath_match else ""
    sqft = sqft_match.group(1).replace(",", "") if sqft_match else ""

    return price, address, beds, baths, sqft


def extract_rows_from_current_page(page, neighbourhood: str) -> list[dict]:
    Path(DEBUG_HTML).write_text(page.content(), encoding="utf-8")

    rows: list[dict] = []
    local_seen: set[tuple[str, str, str]] = set()

    cards = page.locator("div").filter(has_text=re.compile(r"\$")).all()

    for card in cards:
        try:
            text = card.inner_text(timeout=1000)
        except Exception:
            continue

        text = clean_text(text)
        if not text or "$" not in text:
            continue

        href = ""
        try:
            links = card.locator("a").evaluate_all(
                """els => els.map(a => a.href).filter(Boolean)"""
            )
            for link in links:
                if "/real-estate/" in link:
                    href = link
                    break
        except Exception:
            pass

        price, address, beds, baths, sqft = parse_card_text(text)

        signal_count = sum(bool(x) for x in [price, address, beds, baths, sqft, href])
        if signal_count < 2:
            continue

        key = (neighbourhood, href, address)
        if key in local_seen:
            continue
        local_seen.add(key)

        rows.append({
            "neighbourhood": neighbourhood,
            "price": price,
            "address": address,
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "listing_url": href,
            "raw_text": text,
        })

    return rows


def build_remaining_list(
    all_neighbourhoods: list[str],
    completed: set[str],
    start_from: str | None,
    force_redo: set[str],
) -> list[str]:
    remaining = [n for n in all_neighbourhoods if (n not in completed) or (n in force_redo)]

    if start_from:
        try:
            start_idx = remaining.index(start_from)
            remaining = remaining[start_idx:]
        except ValueError:
            print(f"[WARN] START_FROM '{start_from}' not found in remaining list; starting from first remaining.")

    return remaining


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Connect to a local Chromium CDP session and scrape visible REALTOR.ca listing cards."
    )
    parser.add_argument("--cdp-url", default=CDP_URL, help="Chrome DevTools Protocol URL (default: http://127.0.0.1:9222)")
    parser.add_argument("--out-csv", default=OUT_CSV, help="Output CSV path")
    parser.add_argument("--progress-file", default=PROGRESS_FILE, help="Progress marker file (one neighbourhood per line)")
    parser.add_argument(
        "--start-from",
        default=START_FROM,
        help="Resume starting at this neighbourhood name (empty means start at first remaining)",
    )
    parser.add_argument(
        "--force-redo",
        action="append",
        default=[],
        help="Neighbourhood name to redo even if already completed (repeatable)",
    )
    parser.add_argument(
        "--force-redo-json",
        default="",
        help="JSON array of neighbourhood names to redo (alternative to repeating --force-redo)",
    )
    return parser.parse_args()


def _parse_force_redo(raw_values: list[str], raw_json: str) -> set[str]:
    forced = {clean_text(item) for item in (raw_values or []) if clean_text(item)}
    if raw_json:
        payload = json.loads(raw_json)
        if not isinstance(payload, list):
            raise ValueError("--force-redo-json must be a JSON array of strings")
        forced.update(clean_text(item) for item in payload if clean_text(item))
    return {item for item in forced if item}


def main() -> None:
    args = _parse_args()
    out_path = Path(args.out_csv)
    progress_path = Path(args.progress_file)
    start_from = clean_text(args.start_from) or None
    force_redo = _parse_force_redo(args.force_redo, args.force_redo_json)

    ensure_csv_exists(out_path)

    # Remove old rows for any forced-redo neighbourhoods, then clear their progress markers
    if force_redo:
        rewrite_csv_without_neighbourhoods(out_path, force_redo)

    existing_keys = load_existing_keys(out_path)
    completed_neighbourhoods = load_completed_progress(progress_path)

    if force_redo:
        completed_neighbourhoods -= force_redo
        write_completed_progress(progress_path, completed_neighbourhoods)
        existing_keys = load_existing_keys(out_path)

    all_neighbourhoods = fetch_edmonton_neighbourhoods()
    remaining = build_remaining_list(
        all_neighbourhoods,
        completed_neighbourhoods,
        start_from,
        force_redo,
    )

    print(f"Loaded {len(all_neighbourhoods)} residential Edmonton neighbourhoods")
    print(f"Already completed: {len(completed_neighbourhoods)}")
    print(f"Remaining in this run: {len(remaining)}")
    print(f"Appending into: {out_path.resolve()}")
    print(f"Progress file: {progress_path.resolve()}")
    print()

    print(remaining)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()

        print("Connected to:", page.url)
        print(page.title())
        print()

        for idx, neighbourhood in enumerate(remaining, start=1):
            print("=" * 80)
            print(f"Next neighbourhood ({idx}/{len(remaining)}): {neighbourhood}")
            print("In Brave, search this neighbourhood on the REALTOR map page.")
            print("Wait for the left-side list of homes to load.")
            action = input("Press Enter to scrape, 's' to skip, or 'q' to quit: ").strip().lower()

            if action == "q":
                print("Stopping.")
                break

            if action == "s":
                print(f"Skipped {neighbourhood}")
                continue

            page.wait_for_timeout(2500)

            rows = extract_rows_from_current_page(page, neighbourhood)

            new_rows = []
            for row in rows:
                key = (
                    clean_text(row["neighbourhood"]),
                    clean_text(row["listing_url"]),
                    clean_text(row["address"]),
                )
                if key in existing_keys:
                    continue
                existing_keys.add(key)
                new_rows.append(row)

            append_rows(out_path, new_rows)

            if neighbourhood not in completed_neighbourhoods:
                append_completed_progress(progress_path, neighbourhood)
                completed_neighbourhoods.add(neighbourhood)

            print(f"Found {len(rows)} rows on page")
            print(f"Appended {len(new_rows)} new rows to CSV")
            print(f"Marked complete: {neighbourhood}")

    print()
    print(f"Done. CSV is at: {out_path.resolve()}")
    print(f"Progress is at: {progress_path.resolve()}")


if __name__ == "__main__":
    main()
