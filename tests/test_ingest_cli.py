from __future__ import annotations

import io
import json
import sqlite3
import sys
import tempfile
import unittest
import csv
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_sourcing.cli import main
from src.data_sourcing.service import IngestionService


class IngestCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "open_data.db"

    def _run_cli(self, *argv: str) -> dict[str, object]:
        stdout = io.StringIO()
        original_argv = sys.argv
        sys.argv = ["ingest.py", *argv]
        self.addCleanup(self._restore_argv, original_argv)
        with redirect_stdout(stdout):
            main()
        return json.loads(stdout.getvalue())

    def _run_cli_text(self, *argv: str) -> str:
        stdout = io.StringIO()
        original_argv = sys.argv
        sys.argv = ["ingest.py", *argv]
        self.addCleanup(self._restore_argv, original_argv)
        with redirect_stdout(stdout):
            main()
        return stdout.getvalue()

    def _restore_argv(self, argv: list[str]) -> None:
        sys.argv = argv

    def test_db_path_reports_resolved_database_location(self) -> None:
        payload = self._run_cli("db-path", "--db", str(self.db_path))

        self.assertEqual(payload["db"], str(self.db_path.resolve()))

    def test_db_summary_reports_schema_and_row_counts(self) -> None:
        service = IngestionService(db_path=self.db_path)
        service.init_database()

        conn = sqlite3.connect(self.db_path)
        self.addCleanup(conn.close)
        conn.execute(
            "INSERT INTO alerts (run_id, level, message, created_at) VALUES (?, ?, ?, ?)",
            ("run-1", "warning", "test alert", "2026-04-01T00:00:00+00:00"),
        )
        conn.commit()

        output = self._run_cli_text("db-summary", "--db", str(self.db_path))

        self.assertIn(f"Database: {self.db_path.resolve()}", output)
        self.assertIn("Tables:", output)
        self.assertIn("alerts\n  Rows: 1 row\n  Columns:", output)
        self.assertIn("    - id INTEGER PK", output)
        self.assertIn("    - run_id", output)
        self.assertIn("    - created_at TEXT NOT NULL", output)

    def test_ingest_bedbath_backfills_property_location_fields_from_listings_csv(self) -> None:
        service = IngestionService(db_path=self.db_path)
        service.init_database()

        conn = sqlite3.connect(self.db_path)
        self.addCleanup(conn.close)
        conn.execute(
            """
            INSERT INTO property_locations_prod (
                canonical_location_id, house_number, street_name, lat, lon,
                source_ids_json, record_ids_json, link_method, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("loc-1", "6079", "MAYNARD WY NW", None, None, "[]", "[]", "seed", 0.99),
        )
        conn.commit()

        listings_csv = Path(self.temp_dir.name) / "cleaned_edmonton_realtor_cards.csv"
        with listings_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["address", "beds", "baths", "square_footage", "price", "link", "neighborhood", "lat", "long"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "address": "#251 6079 MAYNARD WY NW",
                    "beds": "2",
                    "baths": "2",
                    "square_footage": "1136",
                    "price": "$349,900",
                    "link": "https://www.realtor.ca/real-estate/29552551/251-6079-maynard-wy-nw-edmonton-mactaggart",
                    "neighborhood": "Mactaggart",
                    "lat": "53.4417395",
                    "long": "-113.5610437",
                }
            )

        payload = self._run_cli(
            "ingest-bedbath",
            "--db",
            str(self.db_path),
            "--listings-csv",
            str(listings_csv),
            "--backfill-location-fields",
            "--min-training-rows",
            "999999",
        )

        self.assertEqual(payload["status"], "succeeded")
        self.assertEqual(payload["location_backfill"]["rows_updated"], 1)
        self.assertEqual(payload["location_backfill"]["field_updates"]["lat"], 1)
        self.assertEqual(payload["location_backfill"]["field_updates"]["lon"], 1)

        row = conn.execute(
            "SELECT suite, house_number, street_name, lat, lon FROM property_locations_prod WHERE canonical_location_id = ?",
            ("loc-1",),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "251")
        self.assertEqual(row[1], "6079")
        self.assertEqual(row[2], "MAYNARD WY NW")
        self.assertAlmostEqual(row[3], 53.4417395, places=6)
        self.assertAlmostEqual(row[4], -113.5610437, places=6)


if __name__ == "__main__":
    unittest.main()
