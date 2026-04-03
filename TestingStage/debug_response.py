#!/usr/bin/env python3
"""
Run this ONCE to print the raw JSON of 1 listing.
We'll use the output to find the exact field paths for beds/baths.

  pip install curl_cffi
  python3 debug_response.py
"""
import json, time, sys

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("pip install curl_cffi"); sys.exit(1)

session = cffi_requests.Session(impersonate="chrome120")
session.headers.update({
    "Referer": "https://www.realtor.ca/",
    "Origin":  "https://www.realtor.ca",
    "Accept":  "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-CA,en;q=0.9",
})

# Short pause before hitting the API
time.sleep(2)

payload = {
    "CultureId":"1","ApplicationId":"1",
    "PropertySearchTypeId":"1","TransactionTypeId":"2",
    "PriceMin":"200000","PriceMax":"800000",
    "BedRange":"3-0","BathRange":"2-0",
    "LatitudeMin":"53.3951","LatitudeMax":"53.7162",
    "LongitudeMin":"-113.7137","LongitudeMax":"-113.2686",
    "RecordsPerPage":"3","CurrentPage":"1",
    "SortBy":"6","SortOrder":"A","Version":"7.0",
}

r = session.post(
    "https://api2.realtor.ca/Listing.svc/PropertySearch_Post",
    data=payload, timeout=30
)

print(f"HTTP status: {r.status_code}\n")

if r.status_code != 200:
    print("Error body:", r.text[:400])
    sys.exit(1)

data = r.json()
results = data.get("Results", [])
print(f"Listings returned: {len(results)}\n")

if not results:
    print("No results — check your filters or try again.")
    sys.exit(1)

item = results[0]
print("=" * 60)
print("FULL FIRST LISTING JSON:")
print("=" * 60)
print(json.dumps(item, indent=2, ensure_ascii=False))

print("\n" + "=" * 60)
print("KEY PATHS SUMMARY:")
print("=" * 60)

def find_keys(d, parent=""):
    """Recursively find all leaf values."""
    if isinstance(d, dict):
        for k, v in d.items():
            path = f"{parent}.{k}" if parent else k
            if isinstance(v, (dict, list)):
                find_keys(v, path)
            else:
                print(f"  {path}: {repr(v)[:60]}")
    elif isinstance(d, list):
        for i, v in enumerate(d[:2]):
            find_keys(v, f"{parent}[{i}]")

find_keys(item)
