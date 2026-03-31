from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from TestingStage.backend.services import DataService
from src.data_sourcing.database import connect, init_db


class TransitServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "transit.db"
        connection = connect(self.db_path)
        init_db(connection)

        connection.execute(
            """
            INSERT INTO property_locations_prod (
                canonical_location_id, assessment_year, assessment_value, house_number, street_name,
                neighbourhood, ward, lat, lon, source_ids_json, record_ids_json, link_method, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', 'test', 1.0)
            """,
            ("loc-1", 2026, 450000.0, "100", "MAIN ST NW", "DOWNTOWN", "Ward 1", 53.5000, -113.0000),
        )
        connection.execute(
            """
            INSERT INTO property_locations_prod (
                canonical_location_id, assessment_year, assessment_value, house_number, street_name,
                neighbourhood, ward, lat, lon, source_ids_json, record_ids_json, link_method, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', 'test', 1.0)
            """,
            ("loc-2", 2026, 550000.0, "200", "SOUTH AVE NW", "DOWNTOWN", "Ward 1", 53.5100, -112.9800),
        )

        stops = [
            ("S1", "1001", "Stop 1", 53.5000, -113.0000),
            ("S2", "1002", "Stop 2", 53.5000, -112.9900),
            ("S3", "1003", "Stop 3", 53.5000, -112.9800),
            ("S4", "1004", "Stop 4", 53.5100, -112.9800),
        ]
        for stop_id, stop_code, stop_name, lat, lon in stops:
            connection.execute(
                """
                INSERT INTO transit_prod (
                    transit_type, entity_id, source_id, name, stop_id, stop_code, stop_name,
                    stop_lat, stop_lon, lat, lon, geometry_json, raw_record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "stops",
                    stop_id,
                    "transit.ets_stops",
                    stop_name,
                    stop_id,
                    stop_code,
                    stop_name,
                    lat,
                    lon,
                    lat,
                    lon,
                    json.dumps([[lon, lat]]),
                    "{}",
                ),
            )

        connection.execute(
            """
            INSERT INTO transit_prod (
                transit_type, entity_id, source_id, name, route_id, trip_id, trip_headsign,
                direction_id, shape_id, geometry_json, raw_record_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "trips",
                "T1",
                "transit.ets_trips",
                "Northbound",
                "R1",
                "T1",
                "Northbound",
                0,
                "shape-r1",
                json.dumps([[-113.0000, 53.5000], [-112.9900, 53.5000], [-112.9800, 53.5000]]),
                "{}",
            ),
        )
        connection.execute(
            """
            INSERT INTO transit_prod (
                transit_type, entity_id, source_id, name, route_id, trip_id, trip_headsign,
                direction_id, shape_id, geometry_json, raw_record_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "trips",
                "T2",
                "transit.ets_trips",
                "East Connector",
                "R2",
                "T2",
                "East Connector",
                1,
                "shape-r2",
                json.dumps([[-112.9800, 53.5000], [-112.9800, 53.5100]]),
                "{}",
            ),
        )

        connection.commit()
        connection.close()
        self.service = DataService(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_list_transit_routes_returns_loaded_routes(self) -> None:
        payload = self.service.list_transit_routes()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["route_count"], 2)
        self.assertEqual([route["route_id"] for route in payload["routes"]], ["R1", "R2"])

    def test_route_details_include_route_stops(self) -> None:
        payload = self.service.get_transit_route_details("R1")
        self.assertEqual(payload["route_id"], "R1")
        self.assertEqual(payload["stop_count"], 3)
        self.assertEqual([stop["stop_id"] for stop in payload["stops"]], ["S1", "S2", "S3"])

    def test_plan_transit_journey_supports_address_and_coordinates(self) -> None:
        payload = self.service.plan_transit_journey(
            {"text": "100 MAIN ST NW"},
            {"lat": 53.5100, "lon": -112.9800, "label": "Destination"},
        )
        self.assertEqual(payload["summary"]["route_count"], 2)
        self.assertEqual(payload["summary"]["transfer_count"], 1)
        self.assertEqual(payload["summary"]["routes_used"], ["R1", "R2"])
        transit_legs = [leg for leg in payload["legs"] if leg["mode"] == "transit"]
        self.assertEqual(len(transit_legs), 2)
        self.assertEqual(transit_legs[0]["route_id"], "R1")
        self.assertEqual(transit_legs[1]["route_id"], "R2")


if __name__ == "__main__":
    unittest.main()
