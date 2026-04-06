from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.data_sourcing.database import connect, init_db
from src.data_sourcing.pipelines import run_census_ingest
from src.data_sourcing.source_loader import SourcePayload


def _payload(records: list[dict], metadata: dict | None = None) -> SourcePayload:
    return SourcePayload(
        metadata=metadata or {},
        records=records,
        size_bytes=0,
        checksum="test",
    )


class CensusIngestTests(unittest.TestCase):
    def _db_connection(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "open_data.db"
        conn = connect(db_path)
        init_db(conn)
        self.addCleanup(conn.close)
        return conn

    def test_ingest_statscan_long_format_rows(self) -> None:
        conn = self._db_connection()
        records = [
            {
                "REF_DATE": "2021",
                "DGUID": "2021A000548033",
                "Population and dwelling counts": "Population, 2021",
                "Statistics": "Number",
                "VALUE": "1010899",
            },
            {
                "REF_DATE": "2021",
                "DGUID": "2021A000548033",
                "Population and dwelling counts": "Private dwellings occupied by usual residents, 2021",
                "Statistics": "Number",
                "VALUE": "413150",
            },
            {
                "REF_DATE": "2021",
                "DGUID": "2021A000548033",
                "Population and dwelling counts": "Land area in square kilometres, 2021",
                "Statistics": "Number",
                "VALUE": "767.85",
            },
        ]
        payload = _payload(records, {"collection_year": 2021})

        with patch("src.data_sourcing.pipelines.load_payload_for_source", return_value=payload):
            result = run_census_ingest(conn, trigger="manual", source_overrides=None)

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["promotion_status"], "promoted")
        self.assertIn("detected StatsCan long-format census rows", " | ".join(result["warnings"]))

        row = conn.execute(
            """
            SELECT area_id, geography_level, population, households, area_sq_km
            FROM census_prod
            WHERE area_id = '2021A000548033'
            """
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["geography_level"], "census_subdivision")
        self.assertEqual(row["population"], 1010899)
        self.assertEqual(row["households"], 413150)
        self.assertAlmostEqual(float(row["area_sq_km"]), 767.85, places=2)

    def test_ingest_pre_normalized_rows_without_area_map(self) -> None:
        conn = self._db_connection()
        payload = _payload(
            [
                {
                    "source_area_id": "AREA-EDMONTON",
                    "geography_level": "neighbourhood",
                    "population": 1000,
                    "households": 400,
                    "median_income": 80000,
                    "suppressed_income": False,
                    "area_sq_km": 2.5,
                }
            ],
            {"collection_year": 2021},
        )

        with patch("src.data_sourcing.pipelines.load_payload_for_source", return_value=payload):
            result = run_census_ingest(conn, trigger="manual", source_overrides=None)

        self.assertEqual(result["status"], "succeeded")
        row = conn.execute(
            "SELECT area_id, population, households FROM census_prod WHERE area_id='AREA-EDMONTON'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["population"], 1000)
        self.assertEqual(row["households"], 400)

    def test_ingest_edmonton_neighbourhood_builder_rows(self) -> None:
        conn = self._db_connection()
        payload = _payload(
            [
                {
                    "neighbourhood_number": 12,
                    "neighbourhood": "CANORA",
                    "ward": "sipiwiyiniwak",
                    "population_2021": 3421,
                    "households_2021": 1499,
                    "median_household_income_2020_cad": 81300,
                    "area_sq_km": 1.84,
                }
            ],
            {"collection_year": 2021},
        )

        with patch("src.data_sourcing.pipelines.load_payload_for_source", return_value=payload):
            result = run_census_ingest(conn, trigger="manual", source_overrides=None)

        self.assertEqual(result["status"], "succeeded")
        self.assertIn("Edmonton neighbourhood census rows", " | ".join(result["warnings"]))
        row = conn.execute(
            "SELECT area_id, geography_level, population, households, area_sq_km FROM census_prod WHERE area_id='N012'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["geography_level"], "neighbourhood")
        self.assertEqual(row["population"], 3421)
        self.assertEqual(row["households"], 1499)
        self.assertAlmostEqual(float(row["area_sq_km"]), 1.84, places=2)


if __name__ == "__main__":
    unittest.main()
