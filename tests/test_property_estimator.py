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


class PropertyEstimatorTests(unittest.TestCase):
    def build_service(
        self, *, include_roads: bool = True, include_library: bool = True, include_census: bool = False
    ) -> DataService:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "open_data.db"
        connection = connect(db_path)
        init_db(connection)

        properties = [
            ("loc-1", 2026, 450000.0, "100", "MAIN ST NW", "DOWNTOWN", "1090", "Ward 1", "DC1", 350.0, "180.0", 2005, "Residential", "Y", "RESIDENTIAL", 53.5460, -113.4930),
            ("loc-2", 2026, 470000.0, "102", "MAIN ST NW", "DOWNTOWN", "1090", "Ward 1", "DC1", 360.0, "182.0", 2006, "Residential", "Y", "RESIDENTIAL", 53.5460, -113.4940),
            ("loc-3", 2026, 430000.0, "104", "MAIN ST NW", "DOWNTOWN", "1090", "Ward 1", "DC1", 340.0, "176.0", 2002, "Residential", "N", "RESIDENTIAL", 53.5460, -113.4920),
            ("loc-4", 2026, 520000.0, "200", "RIVER RD NW", "OLIVER", "1020", "Ward 2", "RF3", 420.0, "210.0", 2010, "Residential", "Y", "RESIDENTIAL", 53.5470, -113.4910),
            ("loc-5", 2026, 410000.0, "300", "VALLEY RD NW", "STRATHCONA", "5480", "Ward 3", "RF1", 300.0, "160.0", 1998, "Residential", "N", "RESIDENTIAL", 53.5450, -113.4950),
            ("loc-6", 2026, 560000.0, "400", "PARK RD NW", "GLENORA", "1180", "Ward 4", "RF4", 480.0, "230.0", 2012, "Residential", "Y", "RESIDENTIAL", 53.5480, -113.4940),
            ("loc-7", 2026, 390000.0, "500", "WEST RD NW", "WESTMOUNT", "3440", "Ward 5", "RF2", 290.0, "150.0", 1995, "Residential", "N", "RESIDENTIAL", 53.5440, -113.4940),
        ]
        for row in properties:
            connection.execute(
                """
                INSERT INTO property_locations_prod (
                    canonical_location_id, assessment_year, assessment_value, house_number, street_name,
                    neighbourhood, neighbourhood_id, ward, zoning, lot_size, total_gross_area, year_built, tax_class,
                    garage, assessment_class_1, lat, lon, source_ids_json, record_ids_json, link_method, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', 'test', 1.0)
                """,
                row,
            )
            connection.execute(
                """
                INSERT INTO assessments_prod (
                    canonical_location_id, assessment_year, assessment_value, chosen_record_id, confidence
                ) VALUES (?, ?, ?, ?, 1.0)
                """,
                (row[0], row[1], row[2], f"rec-{row[0]}"),
            )

        property_attributes = [
            ("loc-1", 2, 2.0),
            ("loc-2", 2, 2.5),
            ("loc-3", 3, 1.0),
            ("loc-4", 4, 3.0),
            ("loc-5", 1, 1.0),
            ("loc-6", 5, 4.0),
            ("loc-7", None, None),
        ]
        for canonical_location_id, bedrooms, bathrooms in property_attributes:
            connection.execute(
                """
                INSERT INTO property_attributes_prod (
                    canonical_location_id, bedrooms, bathrooms, bedrooms_estimated, bathrooms_estimated,
                    source_type, source_name, source_record_id, observed_at, confidence, match_method,
                    ambiguous, quarantined, reason_code, feature_snapshot_json, raw_payload_json, updated_at
                ) VALUES (?, ?, ?, NULL, NULL, 'observed', 'test_seed', NULL, NULL, 1.0, 'seed', 0, 0, NULL, '{}', '{}', '2026-04-01T00:00:00+00:00')
                """,
                (canonical_location_id, bedrooms, bathrooms),
            )

        if include_roads:
            segments = [
                ("seg-1", "road-1", 53.5460, -113.4950, 53.5460, -113.4940),
                ("seg-2", "road-1", 53.5460, -113.4940, 53.5460, -113.4930),
                ("seg-3", "road-1", 53.5460, -113.4930, 53.5460, -113.4920),
                ("seg-4", "road-2", 53.5460, -113.4940, 53.5470, -113.4910),
                ("seg-5", "road-3", 53.5460, -113.4940, 53.5450, -113.4950),
                ("seg-6", "road-4", 53.5460, -113.4940, 53.5480, -113.4940),
                ("seg-7", "road-5", 53.5460, -113.4940, 53.5440, -113.4940),
            ]
            for road_id in {"road-1", "road-2", "road-3", "road-4", "road-5"}:
                connection.execute(
                    """
                    INSERT INTO roads_prod (
                        road_id, source_id, road_name, metadata_json
                    ) VALUES (?, 'test', ?, '{}')
                    """,
                    (road_id, road_id.upper()),
                )
            for segment_id, road_id, start_lat, start_lon, end_lat, end_lon in segments:
                center_lat = (start_lat + end_lat) / 2.0
                center_lon = (start_lon + end_lon) / 2.0
                connection.execute(
                    """
                    INSERT INTO road_segments_prod (
                        segment_id, road_id, source_id, segment_name, start_lon, start_lat, end_lon, end_lat,
                        center_lon, center_lat, length_m, geometry_json, metadata_json
                    ) VALUES (?, ?, 'test', ?, ?, ?, ?, ?, ?, ?, 100.0, ?, '{}')
                    """,
                    (
                        segment_id,
                        road_id,
                        segment_id.upper(),
                        start_lon,
                        start_lat,
                        end_lon,
                        end_lat,
                        center_lon,
                        center_lat,
                        json.dumps([[start_lon, start_lat], [end_lon, end_lat]]),
                    ),
                )

        geospatial_rows = [
            ("park-1", "geospatial.parks", "Central Park", "Park", 53.5460, -113.4920),
            ("park-2", "geospatial.parks", "River Park", "Park", 53.5480, -113.4940),
            ("park-3", "geospatial.parks", "West Park", "Park", 53.5440, -113.4940),
            ("play-1", "geospatial.playgrounds", "Playground A", "Playground", 53.5450, -113.4950),
            ("play-2", "geospatial.playgrounds", "Playground B", "Playground", 53.5460, -113.4950),
            ("play-3", "geospatial.playgrounds", "Playground C", "Playground", 53.5470, -113.4910),
            ("school-1", "geospatial.school_locations", "School A", "School", 53.5460, -113.4950),
            ("school-2", "geospatial.school_locations", "School B", "School", 53.5470, -113.4910),
            ("school-3", "geospatial.school_locations", "School C", "School", 53.5440, -113.4940),
        ]
        for entity_id, source_id, name, raw_category, lat, lon in geospatial_rows:
            connection.execute(
                """
                INSERT INTO geospatial_prod (
                    dataset_type, entity_id, source_id, name, raw_category, canonical_geom_type, lon, lat
                ) VALUES ('pois', ?, ?, ?, ?, 'point', ?, ?)
                """,
                (entity_id, source_id, name, raw_category, lon, lat),
            )

        if include_library:
            connection.execute(
                """
                INSERT INTO poi_prod (
                    canonical_poi_id, name, raw_category, raw_subcategory, address, lon, lat, neighbourhood,
                    source_dataset, source_provider, source_ids_json, source_entity_ids_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "library-1",
                    "Central Library",
                    "Business",
                    "library",
                    "1 Library Sq",
                    -113.4930,
                    53.5465,
                    "DOWNTOWN",
                    "osm",
                    "osm",
                    json.dumps(["osm"]),
                    json.dumps(["osm:library-1"]),
                    json.dumps({}),
                ),
            )

        if include_census:
            census_rows = [
                ("N1090", "neighbourhood", 25000, 11000, 2.0, 12500.0, 0),
                ("N2000", "neighbourhood", 5000, 2800, 3.0, 1666.67, 0),
            ]
            for area_id, geography_level, population, households, area_sq_km, population_density, limited_accuracy in census_rows:
                connection.execute(
                    """
                    INSERT INTO census_prod (
                        area_id, geography_level, population, households, median_income,
                        area_sq_km, population_density, limited_accuracy
                    ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?)
                    """,
                    (
                        area_id,
                        geography_level,
                        population,
                        households,
                        area_sq_km,
                        population_density,
                        limited_accuracy,
                    ),
                )

        connection.commit()
        connection.close()
        return DataService(db_path)

    def test_normal_estimate_flow_returns_expected_sections(self) -> None:
        service = self.build_service()
        payload = service.get_property_estimate(
            53.5460,
            -113.4930,
            property_attributes={"year_built": 2005, "garage": "Y", "tax_class": "Residential"},
        )

        self.assertEqual(payload["baseline"]["baseline_type"], "matched_property_assessment")
        self.assertEqual(payload["matched_property"]["canonical_location_id"], "loc-1")
        self.assertGreater(payload["final_estimate"], 0)
        self.assertLessEqual(payload["low_estimate"], payload["final_estimate"])
        self.assertGreaterEqual(payload["high_estimate"], payload["final_estimate"])
        self.assertEqual(len(payload["feature_breakdown"]["amenities"]["parks"]), 3)
        self.assertEqual(len(payload["feature_breakdown"]["amenities"]["playgrounds"]), 3)
        self.assertEqual(len(payload["feature_breakdown"]["amenities"]["schools"]), 3)
        self.assertEqual(len(payload["feature_breakdown"]["amenities"]["libraries"]), 1)

    def test_partial_data_flow_marks_missing_library_factor(self) -> None:
        service = self.build_service(include_library=False)
        payload = service.get_property_estimate(53.5460, -113.4930)

        self.assertIn("library_access", payload["missing_factors"])
        self.assertIn("libraries_unavailable", {item["code"] for item in payload["warnings"]})
        self.assertLess(payload["confidence_score"], 90)

    def test_no_crime_data_returns_warning(self) -> None:
        service = self.build_service()
        payload = service.get_property_estimate(53.5460, -113.4930)
        self.assertIn("crime_unavailable", {item["code"] for item in payload["warnings"]})

    def test_no_census_data_returns_warning(self) -> None:
        service = self.build_service()
        payload = service.get_property_estimate(53.5460, -113.4930)
        self.assertIn("census_unavailable", {item["code"] for item in payload["warnings"]})

    def test_census_data_adds_valuation_adjustment(self) -> None:
        service = self.build_service(include_census=True)
        payload = service.get_property_estimate(53.5460, -113.4930)

        warning_codes = {item["code"] for item in payload["warnings"]}
        self.assertNotIn("census_unavailable", warning_codes)
        adjustment_codes = {item["code"] for item in payload["feature_breakdown"]["valuation_adjustments"]}
        self.assertIn("census_indicators", adjustment_codes)

    def test_straight_line_fallback_sets_flag(self) -> None:
        service = self.build_service(include_roads=False)
        payload = service.get_property_estimate(53.5460, -113.4930)

        self.assertIn("straight_line_distance", payload["fallback_flags"])
        self.assertIn("straight_line_fallback", {item["code"] for item in payload["warnings"]})

    def test_point_matching_existing_property_returns_delta(self) -> None:
        service = self.build_service()
        payload = service.get_property_estimate(53.5460, -113.4930)

        self.assertIsNotNone(payload["matched_property"])
        self.assertIn("estimate_minus_assessed_delta", payload["matched_property"])

    def test_point_not_matching_existing_property_returns_null_matched_property(self) -> None:
        service = self.build_service()
        payload = service.get_property_estimate(53.5430, -113.4900)

        self.assertIsNone(payload["matched_property"])
        self.assertEqual(payload["baseline"]["baseline_type"], "nearest_neighbour_assessment")

    def test_deterministic_repeatability(self) -> None:
        service = self.build_service()
        first = service.get_property_estimate(53.5460, -113.4930)
        second = service.get_property_estimate(53.5460, -113.4930)

        self.assertEqual(first, second)

    def test_bedbath_attributes_filter_matching_comparables(self) -> None:
        service = self.build_service()
        payload = service.get_property_estimate(
            53.5460,
            -113.4930,
            property_attributes={"bedrooms": 2, "bathrooms": 2},
        )

        matching_ids = {row["canonical_location_id"] for row in payload["comparables_matching"]}
        non_matching_ids = {row["canonical_location_id"] for row in payload["comparables_non_matching"]}
        self.assertIn("loc-1", matching_ids)
        self.assertIn("loc-2", matching_ids)
        self.assertNotIn("loc-3", matching_ids)
        self.assertIn("loc-3", non_matching_ids)


if __name__ == "__main__":
    unittest.main()
