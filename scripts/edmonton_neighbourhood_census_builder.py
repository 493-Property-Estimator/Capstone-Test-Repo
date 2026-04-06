#!/usr/bin/env python3
"""
Build a combined Edmonton neighbourhood census dataset from official City of Edmonton
open data (Socrata) resources.

Outputs a CSV with one row per neighbourhood and fields such as:
- neighbourhood
- neighbourhood_number
- ward
- source_area_id
- geography_level
- population_2021
- households_2021
- median_household_income_2020_cad (best-effort match)
- area_sq_km (if geometry libraries are available)

Usage:
    python edmonton_neighbourhood_census_builder.py
    python edmonton_neighbourhood_census_builder.py --out edmonton_neighbourhood_census.csv

Notes:
- This uses official Edmonton open data endpoints, so scraping HTML is not necessary.
- Income characteristic labels can vary. The script searches the income-related rows and
  picks the best median-household-income style label it can find, while also exporting a
  helper CSV listing all income characteristics encountered.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

BASE = "https://data.edmonton.ca/resource"
TIMEOUT = 60
PAGE_SIZE = 50000

# Official Socrata dataset IDs discovered from Edmonton Open Data portal.
DATASETS = {
    "population": "eg3i-f4bj",        # 2021 Federal Census: Population
    "households": "xgkv-ii9t",        # 2021 Federal Census: Households and Families
    "boundaries_2021": "5bk4-5txu",   # 2021 Federal Census: Neighbourhoods as of Official Census Day
    "neighbourhoods_current": "65fr-66s6",  # City of Edmonton - Neighbourhoods
}

LIKELY_MEDIAN_INCOME_PATTERNS = [
    r"median.*household.*income",
    r"median.*total income.*household",
    r"median.*income.*household",
]

session = requests.Session()
session.headers.update({"User-Agent": "edmonton-neighbourhood-census-builder/1.0"})


def fetch_socrata_all(dataset_id: str, select: str | None = None, where: str | None = None) -> pd.DataFrame:
    rows: list[dict] = []
    offset = 0
    while True:
        params = {"$limit": PAGE_SIZE, "$offset": offset}
        if select:
            params["$select"] = select
        if where:
            params["$where"] = where
        url = f"{BASE}/{dataset_id}.json"
        resp = session.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return pd.DataFrame(rows)


def to_numeric(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip()).lower()


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def choose_population(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = [c.lower() for c in work.columns]
    work = to_numeric(work, ["value", "year", "neighbourhood_number", "total_population"])
    number_col = first_existing_column(work, ["neighbourhood_number", "neighbourhood_no", "neighbourh"])
    neighbourhood_col = first_existing_column(work, ["neighbourhood", "name"])
    ward_col = first_existing_column(work, ["ward", "civic_ward_name"])
    characteristic_col = first_existing_column(work, ["characteristic"])
    question_type_col = first_existing_column(work, ["question_type"])
    gender_col = first_existing_column(work, ["gender"])
    value_col = first_existing_column(work, ["value", "total_population"])
    if number_col is None or value_col is None:
        return pd.DataFrame(columns=["neighbourhood_number", "population_2021", "population_characteristic"])

    if characteristic_col is None and value_col == "total_population":
        out = work[[c for c in [neighbourhood_col, number_col, ward_col, value_col] if c is not None]].copy()
        out = out.rename(
            columns={
                neighbourhood_col: "neighbourhood",
                number_col: "neighbourhood_number",
                ward_col: "ward",
                value_col: "population_2021",
            }
        )
        out["population_characteristic"] = "total_population"
        out = out.dropna(subset=["neighbourhood_number"]).drop_duplicates(subset=["neighbourhood_number"], keep="first")
        return out

    # Prefer total population rows at neighbourhood level.
    candidates = work[
        work[characteristic_col].fillna("").str.contains("population", case=False)
    ].copy()
    if gender_col and gender_col in candidates.columns:
        candidates = candidates[candidates[gender_col].fillna("").str.contains("total", case=False)]
    if question_type_col and question_type_col in candidates.columns:
        candidates = candidates[candidates[question_type_col].fillna("").str.contains("population", case=False)]

    # Rank exact-ish labels first.
    rank_map = {
        "population, 2021": 0,
        "population": 1,
        "total - population, 2021": 2,
        "total population": 3,
    }
    candidates["_rank"] = candidates[characteristic_col].map(lambda x: rank_map.get(normalize_text(x), 50))
    candidates = candidates.sort_values([number_col, "_rank", characteristic_col])
    out = candidates.groupby(number_col, as_index=False).first()
    out = out[[c for c in [neighbourhood_col, number_col, ward_col, value_col, characteristic_col] if c is not None]]
    return out.rename(
        columns={
            neighbourhood_col: "neighbourhood",
            number_col: "neighbourhood_number",
            ward_col: "ward",
            value_col: "population_2021",
            characteristic_col: "population_characteristic",
        }
    )


def choose_households(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = [c.lower() for c in work.columns]
    work = to_numeric(work, ["value", "year", "neighbourhood_number"])
    number_col = first_existing_column(work, ["neighbourhood_number", "neighbourhood_no", "neighbourh"])
    neighbourhood_col = first_existing_column(work, ["neighbourhood", "name"])
    ward_col = first_existing_column(work, ["ward", "civic_ward_name"])
    question_type_col = first_existing_column(work, ["question_type"])
    characteristic_col = first_existing_column(work, ["characteristic"])
    gender_col = first_existing_column(work, ["gender"])
    value_col = first_existing_column(work, ["value"])
    if not all([number_col, characteristic_col, value_col]):
        return pd.DataFrame(columns=["neighbourhood_number", "households_2021", "households_characteristic"])

    # Preferred path for current Edmonton schema: derive total households by summing
    # household-size buckets.
    if question_type_col and question_type_col in work.columns:
        household_size = work[work[question_type_col].fillna("").str.contains("household size", case=False)].copy()
        if not household_size.empty:
            bucket_re = re.compile(r"^(1 person|2 persons|3 persons|4 persons|5 or more persons)$", flags=re.I)
            buckets = household_size[household_size[characteristic_col].fillna("").str.match(bucket_re)].copy()
            if not buckets.empty:
                keep_cols = [c for c in [number_col, neighbourhood_col, ward_col, value_col] if c is not None]
                grouped = (
                    buckets[keep_cols]
                    .groupby(number_col, as_index=False)
                    .agg(
                        {
                            value_col: "sum",
                            **({neighbourhood_col: "first"} if neighbourhood_col else {}),
                            **({ward_col: "first"} if ward_col else {}),
                        }
                    )
                )
                grouped["households_characteristic"] = "sum_household_size_distribution"
                return grouped.rename(
                    columns={
                        neighbourhood_col: "neighbourhood",
                        number_col: "neighbourhood_number",
                        ward_col: "ward",
                        value_col: "households_2021",
                    }
                )

    candidates = work.copy()
    if question_type_col and question_type_col in candidates.columns:
        candidates = candidates[candidates[question_type_col].fillna("").str.contains("household|family", case=False)]
    candidates = candidates[candidates[characteristic_col].fillna("").str.contains("private households|households", case=False)]
    if gender_col and gender_col in candidates.columns:
        total_mask = candidates[gender_col].isna() | candidates[gender_col].astype(str).str.contains("total", case=False)
        candidates = candidates[total_mask]

    rankers = [
        "private households occupied by usual residents",
        "private households",
        "households",
    ]
    def rank(x: str) -> int:
        n = normalize_text(x)
        for i, pat in enumerate(rankers):
            if pat in n:
                return i
        return 50

    candidates["_rank"] = candidates[characteristic_col].map(rank)
    candidates = candidates.sort_values([number_col, "_rank", characteristic_col])
    out = candidates.groupby(number_col, as_index=False).first()
    out = out[[c for c in [neighbourhood_col, number_col, ward_col, value_col, characteristic_col] if c is not None]]
    return out.rename(
        columns={
            neighbourhood_col: "neighbourhood",
            number_col: "neighbourhood_number",
            ward_col: "ward",
            value_col: "households_2021",
            characteristic_col: "households_characteristic",
        }
    )


def choose_income(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = df.copy()
    work.columns = [c.lower() for c in work.columns]
    work = to_numeric(work, ["value", "year", "neighbourhood_number"])
    number_col = first_existing_column(work, ["neighbourhood_number", "neighbourhood_no", "neighbourh"])
    neighbourhood_col = first_existing_column(work, ["neighbourhood", "name"])
    ward_col = first_existing_column(work, ["ward", "civic_ward_name"])
    characteristic_col = first_existing_column(work, ["characteristic"])
    question_type_col = first_existing_column(work, ["question_type"])
    gender_col = first_existing_column(work, ["gender"])
    value_col = first_existing_column(work, ["value"])
    if not all([number_col, characteristic_col, value_col]):
        helper = pd.DataFrame(columns=["question_type", "characteristic"])
        return pd.DataFrame(columns=["neighbourhood_number", "median_household_income_2020_cad", "income_characteristic"]), helper

    income_rows = work[work[characteristic_col].fillna("").str.contains("income", case=False)].copy()
    if gender_col and gender_col in income_rows.columns:
        total_mask = income_rows[gender_col].isna() | income_rows[gender_col].astype(str).str.contains("total", case=False)
        income_rows = income_rows[total_mask]

    helper = (
        income_rows[[c for c in [question_type_col, characteristic_col] if c is not None and c in income_rows.columns]]
        .drop_duplicates()
        .sort_values([c for c in [question_type_col, characteristic_col] if c is not None and c in income_rows.columns])
    )

    if income_rows.empty:
        return pd.DataFrame(columns=["neighbourhood_number", "median_household_income_2020_cad", "income_characteristic"]), helper

    def pattern_rank(text: str) -> int:
        n = normalize_text(text)
        for i, pat in enumerate(LIKELY_MEDIAN_INCOME_PATTERNS):
            if re.search(pat, n):
                return i
        if "income" in n and "household" in n and "median" in n:
            return 10
        if "income" in n and "household" in n:
            return 20
        return 50

    income_rows["_rank"] = income_rows[characteristic_col].map(pattern_rank)
    income_rows = income_rows.sort_values([number_col, "_rank", characteristic_col])
    best = income_rows.groupby(number_col, as_index=False).first()
    out = best[[c for c in [neighbourhood_col, number_col, ward_col, value_col, characteristic_col] if c is not None and c in best.columns]]
    out = out.rename(
        columns={
            neighbourhood_col: "neighbourhood",
            number_col: "neighbourhood_number",
            ward_col: "ward",
            value_col: "median_household_income_2020_cad",
            characteristic_col: "income_characteristic",
        }
    )
    return out, helper


def compute_area_sq_km(boundaries: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower(): c for c in boundaries.columns}
    number_col = cols.get("neighbourhood_number") or cols.get("neighbourhood_no") or cols.get("neighbourh")
    name_col = cols.get("neighbourhood") or cols.get("name")
    geom_col = cols.get("the_geom") or cols.get("multipolygon") or cols.get("geometry")

    if not number_col or not geom_col:
        return pd.DataFrame(columns=["neighbourhood_number", "area_sq_km"])

    shape = None
    transform = None
    transformers = []
    try:
        from shapely.geometry import shape as shp_shape
        from shapely.ops import transform as shp_transform
        from pyproj import Transformer

        shape = shp_shape
        transform = shp_transform
        # Alberta / 3TM ref meridian 114 or fallback to Statistics Canada Albers.
        transformers = [
            Transformer.from_crs("EPSG:4326", "EPSG:3776", always_xy=True),
            Transformer.from_crs("EPSG:4326", "EPSG:3347", always_xy=True),
        ]
    except Exception:
        pass

    areas = []
    for _, row in boundaries.iterrows():
        geom_raw = row.get(geom_col)
        if not geom_raw:
            continue
        try:
            area_m2 = math.nan
            if shape and transform and transformers:
                geom = shape(geom_raw)
                for t in transformers:
                    try:
                        projected = transform(t.transform, geom)
                        area_m2 = projected.area
                        if area_m2 and area_m2 > 0:
                            break
                    except Exception:
                        continue
            if not (area_m2 and area_m2 > 0):
                area_m2 = _approx_geojson_area_m2(geom_raw)
            if area_m2 and area_m2 > 0:
                areas.append({
                    "neighbourhood_number": pd.to_numeric(row.get(number_col), errors="coerce"),
                    "neighbourhood": row.get(name_col),
                    "area_sq_km": area_m2 / 1_000_000,
                })
        except Exception:
            continue
    out = pd.DataFrame(areas)
    if not out.empty:
        out = out.groupby("neighbourhood_number", as_index=False).first()
    return out


def _approx_geojson_area_m2(geometry: dict) -> float:
    if not isinstance(geometry, dict):
        return 0.0
    geom_type = str(geometry.get("type") or "")
    coords = geometry.get("coordinates")
    if not coords:
        return 0.0

    if geom_type == "Polygon":
        return _polygon_area_m2(coords)
    if geom_type == "MultiPolygon":
        return sum(_polygon_area_m2(poly) for poly in coords if poly)
    return 0.0


def _polygon_area_m2(rings: list) -> float:
    if not rings:
        return 0.0
    shell = _ring_area_m2(rings[0])
    holes = sum(_ring_area_m2(ring) for ring in rings[1:] if ring)
    return max(0.0, shell - holes)


def _ring_area_m2(ring: list) -> float:
    if not ring or len(ring) < 3:
        return 0.0
    lat0 = sum(float(pt[1]) for pt in ring) / len(ring)
    km_per_deg_lat = 110.574
    km_per_deg_lon = 111.320 * math.cos(math.radians(lat0))
    pts = [(float(pt[0]) * km_per_deg_lon, float(pt[1]) * km_per_deg_lat) for pt in ring]
    area_km2 = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        area_km2 += (x1 * y2) - (x2 * y1)
    return abs(area_km2) * 0.5 * 1_000_000.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="edmonton_neighbourhood_census.csv")
    parser.add_argument("--income-helper", default="edmonton_income_characteristics.csv")
    args = parser.parse_args()

    print("Downloading population table...")
    population_raw = fetch_socrata_all(DATASETS["population"])
    population = choose_population(population_raw)

    print("Downloading households/families table...")
    households_raw = fetch_socrata_all(DATASETS["households"])
    households = choose_households(households_raw)

    print("Scanning population table for income-related characteristics...")
    income, income_helper = choose_income(population_raw)

    print("Downloading boundary geometry for area calculation...")
    boundaries = fetch_socrata_all(DATASETS["boundaries_2021"])
    areas = compute_area_sq_km(boundaries)

    print("Downloading current neighbourhood reference table...")
    current = fetch_socrata_all(DATASETS["neighbourhoods_current"])
    current.columns = [c.lower() for c in current.columns]
    current = to_numeric(current, [c for c in ["neighbourhood_number", "neighbourhood_no"] if c in current.columns])
    rename_map = {}
    if "name" in current.columns and "neighbourhood" not in current.columns:
        rename_map["name"] = "neighbourhood"
    if "civic_ward_name" in current.columns and "ward" not in current.columns:
        rename_map["civic_ward_name"] = "ward"
    if rename_map:
        current = current.rename(columns=rename_map)
    keep = [c for c in ["neighbourhood", "neighbourhood_number", "ward"] if c in current.columns]
    current = current[keep].drop_duplicates(subset=["neighbourhood_number"] if "neighbourhood_number" in keep else None)

    df = current.copy()
    for piece in [population, households, income, areas]:
        if not piece.empty:
            piece = piece.copy()
            if "neighbourhood_number" in piece.columns:
                piece["neighbourhood_number"] = pd.to_numeric(piece["neighbourhood_number"], errors="coerce")
                df = df.merge(piece, on="neighbourhood_number", how="left", suffixes=("", "_dup"))
                dup_cols = [c for c in df.columns if c.endswith("_dup")]
                if dup_cols:
                    df = df.drop(columns=dup_cols)

    # Prefer neighbourhood/ward from the current neighbourhood reference table, but backfill if missing.
    if "neighbourhood_x" in df.columns and "neighbourhood_y" in df.columns:
        df["neighbourhood"] = df["neighbourhood_x"].fillna(df["neighbourhood_y"])
        df = df.drop(columns=["neighbourhood_x", "neighbourhood_y"])
    if "ward_x" in df.columns and "ward_y" in df.columns:
        df["ward"] = df["ward_x"].fillna(df["ward_y"])
        df = df.drop(columns=["ward_x", "ward_y"])

    preferred_order = [
        "source_area_id",
        "geography_level",
        "neighbourhood_number",
        "neighbourhood",
        "ward",
        "population_2021",
        "households_2021",
        "median_household_income_2020_cad",
        "area_sq_km",
        "population_characteristic",
        "households_characteristic",
        "income_characteristic",
    ]
    extra_cols = [c for c in df.columns if c not in preferred_order]
    df = df[[c for c in preferred_order if c in df.columns] + extra_cols]
    df = df.sort_values([c for c in ["neighbourhood_number", "neighbourhood"] if c in df.columns]).reset_index(drop=True)

    if "neighbourhood_number" in df.columns:
        nums = pd.to_numeric(df["neighbourhood_number"], errors="coerce")
        df["source_area_id"] = nums.map(lambda x: f"N{int(x):03d}" if pd.notna(x) else None)
        df["geography_level"] = "neighbourhood"

    out_path = Path(args.out)
    helper_path = Path(args.income_helper)
    df.to_csv(out_path, index=False)
    income_helper.to_csv(helper_path, index=False)

    print(f"Wrote {out_path.resolve()}")
    print(f"Wrote {helper_path.resolve()}")
    if "area_sq_km" in df.columns and df["area_sq_km"].notna().sum() == 0:
        print("Area could not be calculated because shapely/pyproj or geometry fields were unavailable.")
    if "median_household_income_2020_cad" in df.columns and df["median_household_income_2020_cad"].notna().sum() == 0:
        print("No income rows were auto-selected. Inspect the helper CSV and adjust choose_income() if needed.")


if __name__ == "__main__":
    main()
