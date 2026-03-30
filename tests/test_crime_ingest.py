from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from TestingStage.backend.services import DataService
from scripts.ingest_data_folder import discover_sources
from src.data_sourcing.service import IngestionService


class CrimeIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(self.temp_dir.name) / "open_data.db"

    def _write_statscan_csv(self, filename: str = "StatsCan_crime_police_service_edmonton.csv") -> Path:
        path = self.data_dir / filename
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["REF_DATE", "GEO", "Violations", "Statistics", "UOM", "VALUE"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "REF_DATE": "2024",
                    "GEO": "Edmonton Police Service",
                    "Violations": "Total Criminal Code incidents",
                    "Statistics": "Actual incidents",
                    "UOM": "Number",
                    "VALUE": "1250",
                }
            )
            writer.writerow(
                {
                    "REF_DATE": "2024",
                    "GEO": "Edmonton Police Service",
                    "Violations": "Total Criminal Code incidents",
                    "Statistics": "Rate per 100,000 population",
                    "UOM": "Rate per 100,000 population",
                    "VALUE": "980.5",
                }
            )
            writer.writerow(
                {
                    "REF_DATE": "2024",
                    "GEO": "Calgary Police Service",
                    "Violations": "Total Criminal Code incidents",
                    "Statistics": "Actual incidents",
                    "UOM": "Number",
                    "VALUE": "9999",
                }
            )
        return path

    def test_discover_sources_finds_crime_file_for_ingest_all_script(self) -> None:
        crime_file = self._write_statscan_csv()
        planned, _ = discover_sources(self.data_dir)

        matched = [item for item in planned if item.source_key == "crime.statscan_police_service"]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].file_path, crime_file)

    def test_ingest_creates_crime_summary_prod_rows(self) -> None:
        crime_file = self._write_statscan_csv()
        service = IngestionService(db_path=self.db_path)
        service.init_database()

        result = service.ingest(
            source_keys=["crime.statscan_police_service"],
            source_overrides={"crime.statscan_police_service": str(crime_file)},
            trigger="test",
        )

        self.assertEqual(result["status"], "succeeded")
        crime_result = result["pipelines"]["crime"]
        self.assertEqual(crime_result["status"], "succeeded")
        self.assertEqual(crime_result["row_count"], 1)

        data_service = DataService(self.db_path)
        payload = data_service.get_crime_summary(neighbourhood="Edmonton Police Service")
        self.assertTrue(payload["available"])
        self.assertEqual(payload["total_incidents"], 1250)
        self.assertEqual(payload["crime_types"][0]["crime_type"], "Total Criminal Code incidents")


if __name__ == "__main__":
    unittest.main()
