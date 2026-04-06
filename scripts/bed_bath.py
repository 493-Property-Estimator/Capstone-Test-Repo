#!/usr/bin/env python3
"""
Scrape up to 15 random REALTOR.ca listings per Edmonton neighbourhood
and save neighbourhood, address, beds, baths, price, and URL to a CSV.

Notes
-----
- Uses public pages only. No DDF credentials required.
- Depends on Playwright because REALTOR.ca is JS-heavy.
- This is best-effort and may need selector/regex updates if REALTOR.ca changes.
"""

from __future__ import annotations

import csv
import json
import random
import re
import time
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional

import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# -----------------------------
# Config
# -----------------------------
OUTPUT_CSV = "edmonton_neighbourhood_beds_baths.csv"
MAX_PER_NEIGHBOURHOOD = 15
MAX_LISTING_PAGES_PER_NEIGHBOURHOOD = 3
PAGE_WAIT_MS = 4000
HEADLESS = True
REQUEST_TIMEOUT = 30

# Edmonton open data: neighbourhood centroid point dataset
NEIGHBOURHOOD_DATA_URL = "https://data.edmonton.ca/resource/3b6m-fezs.json?$limit=1000"

# REALTOR.ca neighbourhood page pattern
NEIGHBOURHOOD_URL_TEMPLATE = "https://www.realtor.ca/ab/greater-edmonton/{slug}/real-estate"
NEIGHBOURHOOD_URL_TEMPLATES = [
    "https://www.realtor.ca/ab/edmonton/{slug}/real-estate",
    "https://www.realtor.ca/ab/greater-edmonton/{slug}/real-estate",
]

# -----------------------------
# Models
# -----------------------------
@dataclass
class ListingRow:
    neighbourhood: str
    listing_url: str
    address: Optional[str]
    price: Optional[str]
    beds: Optional[str]
    baths: Optional[str]


# -----------------------------
# Helpers
# -----------------------------
def is_probably_residential(name: str) -> bool:
    blocked_terms = [
        "industrial", "energy park", "transportation", "corridor",
        "northlands", "rampart", "mistatim", "big lake"
    ]
    lower = name.lower()
    return not any(term in lower for term in blocked_terms)

def slugify(text: str) -> str:
    """
    Convert neighbourhood names to REALTOR.ca-style slugs.
    Examples:
      "Matt Berry" -> "matt-berry"
      "Wîhkwêntôwin" -> "wihkwentowin"
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def safe_get(d: dict, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def unique_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def extract_json_ld(page_html: str) -> list[dict]:
    soup = BeautifulSoup(page_html, "html.parser")
    objs: list[dict] = []
    for tag in soup.select('script[type="application/ld+json"]'):
        txt = tag.get_text(strip=True)
        if not txt:
            continue
        try:
            parsed = json.loads(txt)
            if isinstance(parsed, list):
                objs.extend([x for x in parsed if isinstance(x, dict)])
            elif isinstance(parsed, dict):
                objs.append(parsed)
        except Exception:
            continue
    return objs


def extract_listing_links_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        # Match listing pages with or without trailing slash or extra path
        if re.search(r"^/real-estate/\d+(?:/|$)", href):
            if href.startswith("/"):
                href = "https://www.realtor.ca" + href
            links.append(href)

    return unique_keep_order(links)


def extract_beds_baths_from_text(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Fall back to page-text regexes if JSON-LD is incomplete.
    """
    compact = re.sub(r"\s+", " ", text)

    bed_patterns = [
        r"(\d+(?:\.\d+)?)\s*bedrooms?\b",
        r"\b(\d+(?:\.\d+)?)\s*beds?\b",
    ]
    bath_patterns = [
        r"(\d+(?:\.\d+)?)\s*bathrooms?\b",
        r"\b(\d+(?:\.\d+)?)\s*baths?\b",
    ]

    beds = None
    baths = None

    for pat in bed_patterns:
        m = re.search(pat, compact, re.IGNORECASE)
        if m:
            beds = m.group(1)
            break

    for pat in bath_patterns:
        m = re.search(pat, compact, re.IGNORECASE)
        if m:
            baths = m.group(1)
            break

    return beds, baths


def extract_listing_details(html: str, url: str) -> ListingRow:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    address = None
    price = None
    beds = None
    baths = None

    # 1) Try JSON-LD
    for obj in extract_json_ld(html):
        typ = obj.get("@type")
        if typ in {"Residence", "SingleFamilyResidence", "Apartment", "House"}:
            address_obj = obj.get("address")
            if isinstance(address_obj, dict):
                parts = [
                    address_obj.get("streetAddress"),
                    address_obj.get("addressLocality"),
                    address_obj.get("addressRegion"),
                    address_obj.get("postalCode"),
                ]
                address = ", ".join([p for p in parts if p])

            # These fields are not always present, but worth checking
            beds = obj.get("numberOfRooms") or obj.get("numberOfBedrooms") or beds
            baths = obj.get("numberOfBathroomsTotal") or obj.get("numberOfBathrooms") or baths

        offers = obj.get("offers")
        if isinstance(offers, dict):
            price = str(offers.get("price") or "") or price

    # 2) Try meta tags / visible text
    if not address:
        title = soup.title.get_text(" ", strip=True) if soup.title else None
        if title:
            address = title.split(" - REALTOR.ca")[0].strip()

    # Price from page text
    if not price:
        m = re.search(r"\$\s?[\d,]+(?:\.\d{2})?", page_text)
        if m:
            price = m.group(0)

    # Beds / baths from visible text
    if beds is None or baths is None:
        t_beds, t_baths = extract_beds_baths_from_text(page_text)
        beds = beds or t_beds
        baths = baths or t_baths

    return ListingRow(
        neighbourhood="",
        listing_url=url,
        address=address,
        price=price,
        beds=str(beds) if beds is not None else None,
        baths=str(baths) if baths is not None else None,
    )


# -----------------------------
# Data acquisition
# -----------------------------
def fetch_edmonton_neighbourhoods() -> list[str]:
    """
    Pull neighbourhood names from Edmonton Open Data.
    """
    resp = requests.get(NEIGHBOURHOOD_DATA_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    print(f"[DEBUG] fetched {len(data)} raw rows")
    if data:
        print(f"[DEBUG] sample keys: {sorted(data[0].keys())}")

    names = []
    for row in data:
        name = (
            row.get("name_mixed")
            or row.get("neighbourhood_name")
            or row.get("name")
        )
        if name:
            names.append(name.strip())

    names = sorted(set(names))
    return names

def get_listing_links_for_neighbourhood(page, neighbourhood_name: str) -> list[str]:
    slug = slugify(neighbourhood_name)
    links: list[str] = []

    candidate_base_urls = [t.format(slug=slug) for t in NEIGHBOURHOOD_URL_TEMPLATES]

    fallback_url = find_neighbourhood_page_via_search(neighbourhood_name)
    if fallback_url and fallback_url not in candidate_base_urls:
        candidate_base_urls.insert(0, fallback_url)

    for base_url in candidate_base_urls:
        for page_num in range(1, MAX_LISTING_PAGES_PER_NEIGHBOURHOOD + 1):
            paged_url = base_url if page_num == 1 else f"{base_url}?page={page_num}"

            try:
                page.goto(paged_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(PAGE_WAIT_MS)
            except PlaywrightTimeoutError:
                print(f"[WARN] Timeout loading {paged_url}")
                continue

            html = page.content()

            if len(html) < 5000:
                debug_path = Path(f"debug_{slug}_{page_num}.html")
                debug_path.write_text(html, encoding="utf-8")
                print(f"[DEBUG] wrote small HTML response to {debug_path}")

                # If this candidate URL is bad, don't keep paging it
                if page_num == 1:
                    print(f"[INFO] Small HTML for neighbourhood: {neighbourhood_name} at {base_url}")
                break

            ids = re.findall(r'"/real-estate/(\d+)(?:/[^"]*)?"', html)
            ids += re.findall(r'https://www\.realtor\.ca/real-estate/(\d+)(?:/[^"]*)?', html)

            print(f"[DEBUG] {neighbourhood_name}: html size = {len(html)}")
            print(f"[DEBUG] {neighbourhood_name}: raw /real-estate/ matches = {len(ids)}")

            found = [f"https://www.realtor.ca/real-estate/{listing_id}" for listing_id in ids]
            found = unique_keep_order(found)

            if found:
                links.extend(found)
            else:
                if page_num == 1:
                    print(f"[INFO] No listing links found for neighbourhood: {neighbourhood_name} ({slug}) at {base_url}")
                break

            if len(unique_keep_order(links)) >= MAX_PER_NEIGHBOURHOOD:
                return unique_keep_order(links)

        if links:
            break

    return unique_keep_order(links)

# def get_listing_links_for_neighbourhood(page, neighbourhood_name: str) -> list[str]:
#     slug = slugify(neighbourhood_name)
#     links: list[str] = []

#     for template in NEIGHBOURHOOD_URL_TEMPLATES:
#         base_url = template.format(slug=slug)

#         for page_num in range(1, MAX_LISTING_PAGES_PER_NEIGHBOURHOOD + 1):
#             paged_url = base_url if page_num == 1 else f"{base_url}?page={page_num}"

#             try:
#                 page.goto(paged_url, wait_until="domcontentloaded", timeout=45000)
#                 page.wait_for_timeout(PAGE_WAIT_MS)
#             except PlaywrightTimeoutError:
#                 print(f"[WARN] Timeout loading {paged_url}")
#                 continue

#             html = page.content()

#             if len(html) < 5000:
#                 debug_path = Path(f"debug_{slug}_{page_num}.html")
#                 debug_path.write_text(html, encoding="utf-8")
#                 print(f"[DEBUG] wrote small HTML response to {debug_path}")

#             # Broad extraction from raw HTML, not just <a> tags
#             ids = re.findall(r'"/real-estate/(\d+)(?:/[^"]*)?"', html)
#             ids += re.findall(r'https://www\.realtor\.ca/real-estate/(\d+)(?:/[^"]*)?', html)

#             print(f"[DEBUG] {neighbourhood_name}: html size = {len(html)}")
#             print(f"[DEBUG] {neighbourhood_name}: raw /real-estate/ matches = {len(ids)}")

#             found = [
#                 f"https://www.realtor.ca/real-estate/{listing_id}"
#                 for listing_id in ids
#             ]
#             found = unique_keep_order(found)

#             if found:
#                 links.extend(found)
#             else:
#                 if page_num == 1:
#                     print(f"[INFO] No listing links found for neighbourhood: {neighbourhood_name} ({slug}) at {base_url}")
#                 break

#         if links:
#             break

#     return unique_keep_order(links)



def find_neighbourhood_page_via_search(neighbourhood_name: str) -> Optional[str]:
    queries = [
        f"site:realtor.ca realtor.ca {neighbourhood_name} Edmonton real estate",
        f"site:realtor.ca realtor.ca {neighbourhood_name} Edmonton houses for sale",
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
    }

    for q in queries:
        url = "https://www.google.com/search?q=" + quote(q)
        try:
            r = requests.get(url, headers=headers, timeout=20)
            html = r.text
        except Exception:
            continue

        matches = re.findall(r'https://www\\.realtor\\.ca/ab/[^"&<> ]+', html)
        cleaned = []
        for m in matches:
            m = m.replace("\\u0026", "&")
            if "/real-estate" in m and neighbourhood_name.lower().replace(" ", "-")[:6] in m.lower():
                cleaned.append(m)

        if cleaned:
            return cleaned[0]

    return None

def scrape_listing(page, listing_url: str) -> Optional[ListingRow]:
    try:
        page.goto(listing_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(PAGE_WAIT_MS)
    except PlaywrightTimeoutError:
        print(f"[WARN] Timeout loading listing: {listing_url}")
        return None

    html = page.content()
    try:
        row = extract_listing_details(html, listing_url)
        return row
    except Exception as e:
        print(f"[WARN] Failed parsing listing {listing_url}: {e}")
        return None


# -----------------------------
# Main
# -----------------------------
def main():
    random.seed()

    # neighbourhoods = fetch_edmonton_neighbourhoods()
    # print(f"[INFO] Loaded {len(neighbourhoods)} neighbourhoods from Edmonton Open Data")
    neighbourhoods = [n for n in fetch_edmonton_neighbourhoods() if is_probably_residential(n)]
    print(f"[INFO] Loaded {len(neighbourhoods)} likely residential neighbourhoods from Edmonton Open Data")

    neighbourhoods = ["Alberta Avenue", "Downtown", "Bonnie Doon"]

    rows: list[ListingRow] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        # context = browser.new_context(
        #     user_agent=(
        #         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        #         "AppleWebKit/537.36 (KHTML, like Gecko) "
        #         "Chrome/123.0.0.0 Safari/537.36"
        #     )
        # )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            locale="en-CA",
            timezone_id="America/Edmonton",
            viewport={"width": 1400, "height": 1000},
        )
        page = context.new_page()

        page.set_extra_http_headers({
            "Accept-Language": "en-CA,en;q=0.9",
        })

        for idx, neighbourhood in enumerate(neighbourhoods, start=1):
            print(f"[INFO] ({idx}/{len(neighbourhoods)}) {neighbourhood}")

            try:
                listing_links = get_listing_links_for_neighbourhood(page, neighbourhood)
            except Exception as e:
                print(f"[WARN] Failed on neighbourhood {neighbourhood}: {e}")
                continue

            if not listing_links:
                continue

            sample_links = listing_links[:]
            random.shuffle(sample_links)
            sample_links = sample_links[:MAX_PER_NEIGHBOURHOOD]

            print(f"[INFO]   Found {len(listing_links)} candidate links, sampling {len(sample_links)}")

            for link in sample_links:
                row = scrape_listing(page, link)
                if not row:
                    continue
                row.neighbourhood = neighbourhood
                rows.append(row)

                # Small sleep to reduce hammering the site
                time.sleep(1.0)

            # Pause between neighbourhoods
            time.sleep(1.5)

        context.close()
        browser.close()

    out_path = Path(OUTPUT_CSV)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["neighbourhood", "listing_url", "address", "price", "beds", "baths"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    print(f"[DONE] Wrote {len(rows)} rows to {out_path.resolve()}")


if __name__ == "__main__":
    main()