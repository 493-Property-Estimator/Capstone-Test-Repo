from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_sourcing.database import connect, init_db


PROOF_DIR = ROOT / "reports" / "bedbath_shadow_proof"
INPUT_DIR = PROOF_DIR / "input"
REVIEW_DIR = PROOF_DIR / "review_exports"
DB_PATH = PROOF_DIR / "shadow_proof.db"
LISTINGS_PATH = INPUT_DIR / "listings.json"
PERMITS_PATH = INPUT_DIR / "permits.json"
AMBIGUOUS_PATH = PROOF_DIR / "ambiguous_matches.csv"
SUMMARY_PATH = PROOF_DIR / "proof_summary.json"


def _property_row(index: int, *, house_number: str, street_name: str, suite: str | None = None) -> dict[str, object]:
    return {
        "canonical_location_id": f"loc-{index:04d}",
        "assessment_year": 2026,
        "assessment_value": float(350000 + (index * 1000)),
        "suite": suite,
        "house_number": house_number,
        "street_name": street_name,
        "legal_description": f"PLAN 1 BLK 1 LOT {index}",
        "zoning": "RF3",
        "lot_size": float(380 + index),
        "total_gross_area": str(140 + (index % 25)),
        "year_built": 1995 + (index % 20),
        "neighbourhood_id": "N1",
        "neighbourhood": "North Glenora",
        "ward": "Ward 1",
        "tax_class": "RES",
        "garage": "attached",
        "assessment_class_1": "RESIDENTIAL",
        "assessment_class_2": None,
        "assessment_class_3": None,
        "assessment_class_pct_1": 100.0,
        "assessment_class_pct_2": None,
        "assessment_class_pct_3": None,
        "lat": 53.50 + (index * 0.0001),
        "lon": -113.50 - (index * 0.0001),
        "point_location": None,
        "source_ids_json": "[]",
        "record_ids_json": "[]",
        "link_method": "seed",
        "confidence": 0.99,
        "updated_at": "2026-04-02T00:00:00+00:00",
    }


def _seed_db() -> None:
    if PROOF_DIR.exists():
        shutil.rmtree(PROOF_DIR)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect(DB_PATH)
    init_db(conn)

    properties: list[dict[str, object]] = []
    listings: list[dict[str, object]] = []
    permits: list[dict[str, object]] = []

    index = 1
    for n in range(360):
        house_number = str(1000 + n)
        properties.append(_property_row(index, house_number=house_number, street_name="MAPLE ST NW"))
        listings.append(
            {
                "source_record_id": f"listing-exact-{index}",
                "house_number": house_number,
                "street_name": "MAPLE ST NW",
                "bedrooms": 3 + (n % 3),
                "bathrooms": 2.0 + (0.5 if n % 4 == 0 else 0.0),
                "source_name": "listing_file",
            }
        )
        index += 1

    for n in range(120):
        house_number = str(2000 + n)
        properties.append(_property_row(index, house_number=house_number, street_name="ELM STREET NW"))
        listings.append(
            {
                "source_record_id": f"listing-fuzzy-{index}",
                "house_number": house_number,
                "street_name": "ELM STRET NW",
                "bedrooms": 2 + (n % 4),
                "bathrooms": 1.5 + (0.5 if n % 2 == 0 else 0.0),
                "source_name": "listing_file",
            }
        )
        index += 1

    for group in range(10):
        house_number = str(3000 + group)
        street_name = f"MAYNARD WAY NW"
        properties.append(_property_row(index, house_number=house_number, street_name=street_name, suite="101"))
        index += 1
        properties.append(_property_row(index, house_number=house_number, street_name=street_name, suite="102"))
        listings.append(
            {
                "source_record_id": f"listing-suite-{group}",
                "house_number": house_number,
                "street_name": street_name,
                "bedrooms": 2,
                "bathrooms": 2.0,
                "source_name": "listing_file",
            }
        )
        index += 1

    for n in range(20):
        house_number = str(4000 + n)
        properties.append(_property_row(index, house_number=house_number, street_name="PINE AVE NW"))
        permits.append(
            {
                "source_record_id": f"permit-{index}",
                "house_number": house_number,
                "street_name": "PINE AVE NW",
                "permit_description": "Interior renovation for 3 bedroom 2 bathroom home",
                "source_name": "permit_file",
            }
        )
        index += 1

    while index <= 600:
        house_number = str(5000 + index)
        properties.append(_property_row(index, house_number=house_number, street_name="CEDAR RD NW"))
        index += 1

    for n in range(10):
        listings.append(
            {
                "source_record_id": f"listing-unmatched-{n}",
                "house_number": str(9000 + n),
                "street_name": "UNKNOWN ST NW",
                "bedrooms": 4,
                "bathrooms": 2.5,
                "source_name": "listing_file",
            }
        )
        permits.append(
            {
                "source_record_id": f"permit-unmatched-{n}",
                "house_number": str(9500 + n),
                "street_name": "UNKNOWN AVE NW",
                "permit_description": "Development permit for 4 bedroom 3 bathroom dwelling",
                "source_name": "permit_file",
            }
        )

    conn.executemany(
        """
        INSERT INTO property_locations_prod (
            canonical_location_id, assessment_year, assessment_value, suite, house_number,
            street_name, legal_description, zoning, lot_size, total_gross_area, year_built,
            neighbourhood_id, neighbourhood, ward, tax_class, garage, assessment_class_1,
            assessment_class_2, assessment_class_3, assessment_class_pct_1,
            assessment_class_pct_2, assessment_class_pct_3, lat, lon, point_location,
            source_ids_json, record_ids_json, link_method, confidence, updated_at
        ) VALUES (
            :canonical_location_id, :assessment_year, :assessment_value, :suite, :house_number,
            :street_name, :legal_description, :zoning, :lot_size, :total_gross_area, :year_built,
            :neighbourhood_id, :neighbourhood, :ward, :tax_class, :garage, :assessment_class_1,
            :assessment_class_2, :assessment_class_3, :assessment_class_pct_1,
            :assessment_class_pct_2, :assessment_class_pct_3, :lat, :lon, :point_location,
            :source_ids_json, :record_ids_json, :link_method, :confidence, :updated_at
        )
        """,
        properties,
    )
    conn.commit()
    conn.close()

    LISTINGS_PATH.write_text(json.dumps(listings, indent=2), encoding="utf-8")
    PERMITS_PATH.write_text(json.dumps(permits, indent=2), encoding="utf-8")


def _read_csv_sample(path: Path, limit: int = 2) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))[:limit]


def main() -> None:
    _seed_db()
    command = [
        "python3",
        "-m",
        "data_sourcing.enrich_bedbath",
        "--db-path",
        str(DB_PATH),
        "--listings-json",
        str(LISTINGS_PATH),
        "--permits-json",
        str(PERMITS_PATH),
        "--shadow-mode",
        "--disable-promotion",
        "--review-export-dir",
        str(REVIEW_DIR),
        "--ambiguous-csv",
        str(AMBIGUOUS_PATH),
        "--min-training-rows",
        "25",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    conn = connect(DB_PATH)
    prod_count = conn.execute("SELECT COUNT(*) FROM property_attributes_prod").fetchone()[0]
    shadow_count = conn.execute("SELECT COUNT(*) FROM property_attributes_shadow").fetchone()[0]
    staging_count = conn.execute("SELECT COUNT(*) FROM property_attributes_staging WHERE run_id = ?", (result["run_id"],)).fetchone()[0]
    conn.close()

    review_exports = {key: Path(path) for key, path in result["report"]["review_exports"].items()}
    samples = {key: _read_csv_sample(path) for key, path in review_exports.items()}
    proof = {
        "exact_command": "PYTHONPATH=src " + " ".join(command),
        "run_id": result["run_id"],
        "promotion": result["promotion"],
        "shadow_run_summary": result["report"]["shadow_run_summary"],
        "real_feed_readiness_checklist": result["report"]["real_feed_readiness_checklist"],
        "output_files_produced": [str(DB_PATH), str(LISTINGS_PATH), str(PERMITS_PATH), str(AMBIGUOUS_PATH)]
        + [str(path) for path in review_exports.values()],
        "sample_rows": samples,
        "promotion_confirmation": {
            "promotion_disabled": result["promotion"]["promotion_disabled"],
            "prod_row_count": prod_count,
            "shadow_row_count": shadow_count,
            "staging_row_count": staging_count,
        },
    }
    SUMMARY_PATH.write_text(json.dumps(proof, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(proof, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
