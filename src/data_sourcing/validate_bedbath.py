"""Validation helper for bed/bath enrichment output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .database import connect


def validate_bedbath(db_path: str | Path, *, run_id: str | None = None, limit: int = 10) -> dict:
    conn = connect(Path(db_path))
    try:
        counts = dict(
            conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM property_locations_prod) AS candidate_properties,
                    (SELECT COUNT(*) FROM property_attributes_staging) AS staging_rows,
                    (SELECT COUNT(*) FROM property_attributes_prod) AS prod_rows,
                    (SELECT COUNT(*) FROM property_attributes_prod WHERE source_type='observed') AS observed_fills,
                    (SELECT COUNT(*) FROM property_attributes_prod WHERE source_type='inferred') AS inferred_fills,
                    (SELECT COUNT(*) FROM property_attributes_prod WHERE source_type='imputed') AS imputed_fills
                """
            ).fetchone()
        )
        counts["remaining_nulls"] = counts["candidate_properties"] - counts["prod_rows"]

        if run_id:
            samples = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT canonical_location_id, bedrooms, bathrooms, bedrooms_estimated,
                           bathrooms_estimated, source_type, source_name, confidence
                    FROM property_attributes_staging
                    WHERE run_id = ?
                    ORDER BY confidence DESC, canonical_location_id
                    LIMIT ?
                    """,
                    (run_id, limit),
                ).fetchall()
            ]
        else:
            samples = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT canonical_location_id, bedrooms, bathrooms, bedrooms_estimated,
                           bathrooms_estimated, source_type, source_name, confidence
                    FROM property_attributes_prod
                    ORDER BY confidence DESC, canonical_location_id
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            ]
        return {"counts": counts, "samples": samples}
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate property attribute bed/bath enrichment output.")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(validate_bedbath(args.db_path, run_id=args.run_id, limit=args.limit), indent=2))


if __name__ == "__main__":
    main()
