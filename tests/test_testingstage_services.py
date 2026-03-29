from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from TestingStage.backend.services import DataService, OsrmService
from src.data_sourcing.database import connect, init_db


class _MockResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class TestingStageServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "open_data.db"
        connection = connect(self.db_path)
        init_db(connection)
        connection.execute(
            """
            INSERT INTO property_locations_prod (
                canonical_location_id, assessment_year, assessment_value, house_number, street_name,
                neighbourhood, ward, lat, lon, source_ids_json, record_ids_json, link_method, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', 'test', 1.0)
            """,
            (
                "loc-1",
                2026,
                450000.0,
                "100",
                "MAIN ST NW",
                "DOWNTOWN",
                "Ward 1",
                53.5461,
                -113.4938,
            ),
        )
        connection.execute(
            """
            INSERT INTO assessments_records_prod (
                record_id, source_id, assessment_year, canonical_location_id, assessment_value,
                house_number, street_name, neighbourhood, ward, lat, lon, link_method,
                confidence, ambiguous, quarantined, raw_record_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
            """,
            (
                "rec-1",
                "assessments.property_tax_csv",
                2026,
                "loc-1",
                450000.0,
                "100",
                "MAIN ST NW",
                "DOWNTOWN",
                "Ward 1",
                53.5461,
                -113.4938,
                "test",
                1.0,
                json.dumps({"beds": 3, "baths": 2}),
            ),
        )
        connection.execute(
            """
            INSERT INTO poi_prod (
                canonical_poi_id, name, raw_category, raw_subcategory, address, lon, lat, neighbourhood,
                source_dataset, source_provider, source_ids_json, source_entity_ids_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "poi-1",
                "Central Rec Centre",
                "Recreation",
                "Arena",
                "101 Main St NW",
                -113.4930,
                53.5465,
                "DOWNTOWN",
                "Recreation Facilities",
                "City of Edmonton Open Data",
                json.dumps(["geospatial.recreation_facilities"]),
                json.dumps(["geospatial.recreation_facilities:poi-1"]),
                json.dumps({"sources": {"geospatial.recreation_facilities": {"entity_id": "poi-1"}}}),
            ),
        )
        connection.commit()
        connection.close()
        self.service = DataService(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_nearest_property_uses_application_database(self) -> None:
        payload = self.service.get_nearest_property(53.5462, -113.4937)
        self.assertEqual(payload["selected_property"]["canonical_location_id"], "loc-1")
        self.assertEqual(payload["selected_property"]["address"], "100 MAIN ST NW")

    def test_poi_query_filters_by_source_neighbourhood_and_type(self) -> None:
        payload = self.service.query_pois(
            source="geospatial.recreation_facilities",
            neighbourhood="DOWNTOWN",
            category="Recreation",
            poi_type="Arena",
            lat=53.5461,
            lon=-113.4938,
            radius_m=500,
        )
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["name"], "Central Rec Centre")

    def test_neighbourhood_summary_returns_age_size_and_garage_metrics(self) -> None:
        payload = self.service.get_neighborhood_summary("DOWNTOWN")
        self.assertIsNone(payload["average_house_age_years"])
        self.assertIsNone(payload["average_house_size"])
        self.assertIsNone(payload["garage_percentage"])
        self.assertEqual(payload["garage_known_row_count"], 0)

    def test_crime_summary_returns_clear_unavailable_payload_without_dataset(self) -> None:
        payload = self.service.get_crime_summary(neighbourhood="DOWNTOWN")
        self.assertFalse(payload["available"])
        self.assertIn("Crime summary data is not available", payload["message"])


class OsrmServiceTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_route_parses_distance_and_duration(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = _MockResponse(
            {
                "code": "Ok",
                "routes": [
                    {
                        "distance": 1234.56,
                        "duration": 321.0,
                        "geometry": {"type": "LineString", "coordinates": [[-113.49, 53.54]]},
                    }
                ],
                "waypoints": [
                    {"name": "Start", "distance": 5.1, "location": [-113.4938, 53.5461]},
                    {"name": "End", "distance": 4.9, "location": [-113.469, 53.5585]},
                ],
            }
        )
        service = OsrmService(base_url="http://127.0.0.1:5000")
        payload = service.route(53.5461, -113.4938, 53.5585, -113.4690, "driving")
        self.assertEqual(payload["distance_m"], 1234.56)
        self.assertEqual(payload["duration_s"], 321.0)
        self.assertEqual(payload["start_waypoint"]["name"], "Start")

    @patch("urllib.request.urlopen")
    def test_matrix_parses_both_durations_and_distances(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = _MockResponse(
            {
                "code": "Ok",
                "durations": [[0, 60.1], [61.2, 0]],
                "distances": [[0, 500.4], [501.5, 0]],
                "sources": [
                    {"name": "A", "distance": 1.0, "location": [-113.49, 53.54]},
                    {"name": "B", "distance": 1.0, "location": [-113.47, 53.55]},
                ],
                "destinations": [
                    {"name": "A", "distance": 1.0, "location": [-113.49, 53.54]},
                    {"name": "B", "distance": 1.0, "location": [-113.47, 53.55]},
                ],
            }
        )
        service = OsrmService(base_url="http://127.0.0.1:5000")
        payload = service.matrix(
            [{"lat": 53.54, "lon": -113.49}, {"lat": 53.55, "lon": -113.47}],
            "walking",
        )
        self.assertEqual(payload["durations_s"][0][1], 60.1)
        self.assertEqual(payload["distances_m"][1][0], 501.5)


if __name__ == "__main__":
    unittest.main()
