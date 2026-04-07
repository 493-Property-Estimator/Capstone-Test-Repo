#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from estimator.property_estimator import PropertyEstimator  # noqa: E402


def _parse_money(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    cleaned = (
        text.replace("$", "")
        .replace(",", "")
        .replace(" ", "")
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _build_property_attributes(row: dict[str, str]) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    beds = _parse_float(row.get("beds"))
    baths = _parse_float(row.get("baths"))
    sqft = _parse_float(row.get("square_footage"))
    if beds is not None:
        attrs["bedrooms"] = beds
    if baths is not None:
        attrs["bathrooms"] = baths
    if sqft is not None:
        attrs["total_gross_area"] = sqft
    return attrs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate property-list-price vs estimator output comparison data."
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=REPO_ROOT / "src/estimator/cleaned_edmonton_realtor_cards.csv",
        help="Input realtor cards CSV path.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=REPO_ROOT / "src/data_sourcing/open_data.db",
        help="SQLite feature store used by PropertyEstimator.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=REPO_ROOT / "Visuals/property_estimator_comparison.csv",
        help="Output CSV file path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of properties to process.",
    )
    args = parser.parse_args()

    if not args.input_csv.exists():
        raise SystemExit(f"Input CSV not found: {args.input_csv}")
    if not args.db_path.exists():
        raise SystemExit(f"Estimator DB not found: {args.db_path}")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    estimator = PropertyEstimator(args.db_path)

    output_fields = [
        "address",
        "neighborhood",
        "list_price",
        "lat",
        "lon",
        "estimator_low",
        "estimator_final",
        "estimator_high",
        "estimator_range",
        "delta_list_minus_estimator",
        "delta_estimator_minus_list",
        "confidence_score",
        "confidence_label",
        "error",
    ]

    total_rows = 0
    success_rows = 0
    error_rows = 0

    with args.input_csv.open("r", encoding="utf-8", newline="") as infile, args.output_csv.open(
        "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=output_fields)
        writer.writeheader()

        for row in reader:
            if args.limit is not None and total_rows >= args.limit:
                break
            total_rows += 1

            address = (row.get("address") or "").strip()
            neighborhood = (row.get("neighborhood") or "").strip()
            list_price = _parse_money(row.get("price"))
            lat = _parse_float(row.get("lat"))
            lon = _parse_float(row.get("long"))

            out_row: dict[str, Any] = {
                "address": address,
                "neighborhood": neighborhood,
                "list_price": list_price,
                "lat": lat,
                "lon": lon,
                "estimator_low": None,
                "estimator_final": None,
                "estimator_high": None,
                "estimator_range": None,
                "delta_list_minus_estimator": None,
                "delta_estimator_minus_list": None,
                "confidence_score": None,
                "confidence_label": None,
                "error": "",
            }

            if list_price is None:
                out_row["error"] = "missing_or_invalid_price"
                error_rows += 1
                writer.writerow(out_row)
                continue
            if lat is None or lon is None:
                out_row["error"] = "missing_or_invalid_coordinates"
                error_rows += 1
                writer.writerow(out_row)
                continue

            try:
                attributes = _build_property_attributes(row)
                estimate = estimator.estimate(
                    lat=lat,
                    lon=lon,
                    property_attributes=attributes or None,
                )
                est_low = estimate.get("low_estimate")
                est_final = estimate.get("final_estimate")
                est_high = estimate.get("high_estimate")

                est_range = None
                if est_low is not None and est_high is not None:
                    est_range = float(est_high) - float(est_low)

                delta_list_minus_est = None
                delta_est_minus_list = None
                if est_final is not None:
                    delta_list_minus_est = float(list_price) - float(est_final)
                    delta_est_minus_list = float(est_final) - float(list_price)

                out_row.update(
                    {
                        "estimator_low": est_low,
                        "estimator_final": est_final,
                        "estimator_high": est_high,
                        "estimator_range": est_range,
                        "delta_list_minus_estimator": delta_list_minus_est,
                        "delta_estimator_minus_list": delta_est_minus_list,
                        "confidence_score": estimate.get("confidence_score"),
                        "confidence_label": estimate.get("confidence_label"),
                    }
                )
                success_rows += 1
            except Exception as exc:
                out_row["error"] = str(exc)
                error_rows += 1

            writer.writerow(out_row)

            if total_rows % 100 == 0:
                print(f"Processed {total_rows} rows...")

    print(f"Wrote comparison data: {args.output_csv}")
    print(f"Rows processed: {total_rows}")
    print(f"Estimator successes: {success_rows}")
    print(f"Rows with errors: {error_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
