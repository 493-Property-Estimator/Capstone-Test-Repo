from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_sourcing.address_normalization import normalize_property_address
from src.data_sourcing.database import connect, init_db
from src.data_sourcing.enrich_bedbath import EnrichmentConfig, run_bedbath_enrichment
from src.data_sourcing.promotion import choose_preferred_record, precedence_key
from src.data_sourcing.property_matcher import choose_best_match
from src.data_sourcing.source_clients import SourceClients


class AddressNormalizationTests(unittest.TestCase):
    def test_normalizes_suite_street_and_legal_description(self) -> None:
        normalized = normalize_property_address(
            {
                "suite": "Suite #204",
                "house_number": "101A",
                "street_name": "Main Street Northwest",
                "legal_description": "Lot 12 Block 3 Plan 9988",
                "neighbourhood": "Downtown",
                "zoning": "rf3",
                "lat": "53.54",
                "lon": "-113.49",
            }
        )

        self.assertEqual(normalized.suite, "204")
        self.assertEqual(normalized.street_name, "MAIN ST NW")
        self.assertEqual(normalized.legal_description, "LT 12 BLK 3 PLAN 9988")
        self.assertEqual(normalized.full_address_key, "101A MAIN ST NW 204")

    def test_normalizes_common_suffix_typos_and_direction_spacing(self) -> None:
        normalized = normalize_property_address(
            {
                "house_number": "616",
                "street_name": "176  Stret  S W.",
                "suite": "Unit 112",
            }
        )

        self.assertEqual(normalized.street_name, "176 ST SW")
        self.assertEqual(normalized.strict_street_name, "176 STRET SW")
        self.assertEqual(normalized.suite, "112")


class PropertyMatcherTests(unittest.TestCase):
    def test_exact_address_beats_fuzzy_candidate(self) -> None:
        property_row = {
            "canonical_location_id": "loc-1",
            "house_number": "101",
            "street_name": "Main Street Northwest",
            "suite": "2",
            "legal_description": None,
            "lat": 53.546,
            "lon": -113.493,
            "year_built": 2005,
            "total_gross_area": "180",
        }
        candidates = [
            {
                "source_record_id": "fuzzy",
                "house_number": "101",
                "street_name": "Main Str Northwest",
                "suite": "3",
                "lat": 53.5461,
                "lon": -113.4931,
                "year_built": 2005,
                "total_gross_area": "179",
                "bedrooms": 3,
                "bathrooms": 2.0,
            },
            {
                "source_record_id": "exact",
                "house_number": "101",
                "street_name": "Main Street NW",
                "suite": "2",
                "lat": 53.546,
                "lon": -113.493,
                "year_built": 2005,
                "total_gross_area": "180",
                "bedrooms": 4,
                "bathrooms": 2.5,
            },
        ]

        result = choose_best_match(property_row, candidates, fuzzy_threshold=0.80)

        self.assertIsNotNone(result)
        self.assertEqual(result.source_record_id, "exact")
        self.assertEqual(result.match_method, "exact_address_suite")

    def test_typo_normalized_street_match_is_recovered_as_safe_fuzzy(self) -> None:
        property_row = {
            "canonical_location_id": "loc-typo",
            "house_number": "616",
            "street_name": "176 STREET SW",
            "suite": None,
            "legal_description": None,
            "lat": 53.45,
            "lon": -113.61,
            "year_built": 2018,
            "total_gross_area": "150",
            "multi_unit_group_size": 1,
        }
        candidates = [
            {
                "source_record_id": "listing-typo",
                "house_number": "616",
                "street_name": "176 STRET SW",
                "suite": None,
                "lat": 53.45,
                "lon": -113.61,
                "year_built": 2018,
                "total_gross_area": "150",
                "bedrooms": 4,
                "bathrooms": 2.5,
            }
        ]

        result = choose_best_match(property_row, candidates, fuzzy_threshold=0.90)

        self.assertIsNotNone(result)
        self.assertEqual(result.match_method, "fuzzy_address_geo")
        self.assertEqual(result.reason_code, "typo_normalized_match")
        self.assertFalse(result.quarantined)

    def test_suite_missing_multi_unit_is_quarantined_instead_of_guessed(self) -> None:
        property_row = {
            "canonical_location_id": "loc-suite",
            "house_number": "6083",
            "street_name": "MAYNARD WAY NW",
            "suite": "112",
            "legal_description": None,
            "lat": 53.61,
            "lon": -113.43,
            "year_built": 2020,
            "total_gross_area": "95",
            "multi_unit_group_size": 2,
        }
        candidates = [
            {
                "source_record_id": "listing-suite-missing",
                "house_number": "6083",
                "street_name": "MAYNARD WAY NW",
                "suite": None,
                "lat": 53.61,
                "lon": -113.43,
                "year_built": 2020,
                "total_gross_area": "95",
                "bedrooms": 2,
                "bathrooms": 2.0,
            }
        ]

        result = choose_best_match(property_row, candidates, fuzzy_threshold=0.90)

        self.assertIsNotNone(result)
        self.assertTrue(result.quarantined)
        self.assertEqual(result.reason_code, "suite_missing_multi_unit")
        self.assertEqual(result.match_method, "suite_missing_multi_unit")


class PromotionRuleTests(unittest.TestCase):
    def test_promotion_precedence_prefers_observed_exact(self) -> None:
        inferred = {
            "canonical_location_id": "loc-1",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "bedrooms_estimated": None,
            "bathrooms_estimated": None,
            "source_type": "inferred",
            "source_name": "permit_text",
            "source_record_id": "permit-1",
            "observed_at": None,
            "confidence": 0.84,
            "match_method": "permit_text",
            "ambiguous": 0,
            "quarantined": 0,
            "reason_code": None,
            "feature_snapshot_json": "{}",
            "raw_payload_json": "{}",
            "updated_at": "2026-04-02T00:00:00+00:00",
        }
        observed = dict(inferred)
        observed.update(
            {
                "source_type": "observed",
                "source_name": "listing_api",
                "source_record_id": "listing-1",
                "match_method": "exact_address_suite",
                "confidence": 0.99,
                "bedrooms": 4,
                "bathrooms": 3.0,
            }
        )

        preferred = choose_preferred_record(inferred, observed)

        self.assertEqual(preferred["source_type"], "observed")
        self.assertEqual(preferred["bedrooms"], 4)
        self.assertGreater(precedence_key(preferred), precedence_key(inferred))

    def test_no_downgrade_keeps_observed_when_imputed_arrives(self) -> None:
        existing = {
            "canonical_location_id": "loc-2",
            "bedrooms": 5,
            "bathrooms": 3.5,
            "bedrooms_estimated": None,
            "bathrooms_estimated": None,
            "source_type": "observed",
            "source_name": "listing_api",
            "source_record_id": "listing-2",
            "observed_at": "2026-04-01T00:00:00+00:00",
            "confidence": 0.98,
            "match_method": "exact_address_suite",
            "ambiguous": 0,
            "quarantined": 0,
            "reason_code": None,
            "feature_snapshot_json": "{}",
            "raw_payload_json": "{}",
            "updated_at": "2026-04-01T00:00:00+00:00",
        }
        imputed = {
            "canonical_location_id": "loc-2",
            "bedrooms": None,
            "bathrooms": None,
            "bedrooms_estimated": 3,
            "bathrooms_estimated": 2.0,
            "source_type": "imputed",
            "source_name": "bedbath-grouped-v1",
            "source_record_id": None,
            "observed_at": None,
            "confidence": 0.74,
            "match_method": "model_imputation",
            "ambiguous": 0,
            "quarantined": 0,
            "reason_code": None,
            "feature_snapshot_json": "{}",
            "raw_payload_json": "{}",
            "updated_at": "2026-04-02T00:00:00+00:00",
        }

        preferred = choose_preferred_record(existing, imputed)

        self.assertEqual(preferred["bedrooms"], 5)
        self.assertEqual(preferred["bathrooms"], 3.5)
        self.assertEqual(preferred["bedrooms_estimated"], 3)
        self.assertEqual(preferred["source_type"], "observed")


class SchemaMigrationTests(unittest.TestCase):
    def test_init_db_creates_property_attribute_tables(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "bedbath.db"
        conn = connect(db_path)

        init_db(conn)

        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'property_attributes_%'"
            ).fetchall()
        }
        self.assertEqual(tables, {"property_attributes_staging", "property_attributes_prod", "property_attributes_shadow"})


class FreshRunImputationTests(unittest.TestCase):
    def test_single_fresh_run_uses_same_run_staged_rows_for_training(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "fresh-bedbath.db"
        conn = connect(db_path)
        init_db(conn)
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
            [
                {
                    "canonical_location_id": "loc-1",
                    "assessment_year": 2026,
                    "assessment_value": 410000.0,
                    "suite": None,
                    "house_number": "101",
                    "street_name": "MAPLE ST NW",
                    "legal_description": "PLAN 1 BLK 1 LOT 1",
                    "zoning": "RF3",
                    "lot_size": 400.0,
                    "total_gross_area": "160",
                    "year_built": 2005,
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
                    "lat": 53.55,
                    "lon": -113.50,
                    "point_location": None,
                    "source_ids_json": "[]",
                    "record_ids_json": "[]",
                    "link_method": "seed",
                    "confidence": 0.99,
                    "updated_at": "2026-04-02T00:00:00+00:00",
                },
                {
                    "canonical_location_id": "loc-2",
                    "assessment_year": 2026,
                    "assessment_value": 420000.0,
                    "suite": None,
                    "house_number": "102",
                    "street_name": "MAPLE ST NW",
                    "legal_description": "PLAN 1 BLK 1 LOT 2",
                    "zoning": "RF3",
                    "lot_size": 410.0,
                    "total_gross_area": "165",
                    "year_built": 2006,
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
                    "lat": 53.5505,
                    "lon": -113.5005,
                    "point_location": None,
                    "source_ids_json": "[]",
                    "record_ids_json": "[]",
                    "link_method": "seed",
                    "confidence": 0.99,
                    "updated_at": "2026-04-02T00:00:00+00:00",
                },
                {
                    "canonical_location_id": "loc-3",
                    "assessment_year": 2026,
                    "assessment_value": 430000.0,
                    "suite": None,
                    "house_number": "103",
                    "street_name": "MAPLE ST NW",
                    "legal_description": "PLAN 1 BLK 1 LOT 3",
                    "zoning": "RF3",
                    "lot_size": 420.0,
                    "total_gross_area": "170",
                    "year_built": 2007,
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
                    "lat": 53.551,
                    "lon": -113.501,
                    "point_location": None,
                    "source_ids_json": "[]",
                    "record_ids_json": "[]",
                    "link_method": "seed",
                    "confidence": 0.99,
                    "updated_at": "2026-04-02T00:00:00+00:00",
                },
                {
                    "canonical_location_id": "loc-4",
                    "assessment_year": 2026,
                    "assessment_value": 425000.0,
                    "suite": None,
                    "house_number": "104",
                    "street_name": "MAPLE ST NW",
                    "legal_description": "PLAN 1 BLK 1 LOT 4",
                    "zoning": "RF3",
                    "lot_size": 415.0,
                    "total_gross_area": "168",
                    "year_built": 2008,
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
                    "lat": 53.5515,
                    "lon": -113.5015,
                    "point_location": None,
                    "source_ids_json": "[]",
                    "record_ids_json": "[]",
                    "link_method": "seed",
                    "confidence": 0.99,
                    "updated_at": "2026-04-02T00:00:00+00:00",
                },
            ],
        )
        conn.commit()
        conn.close()

        result = run_bedbath_enrichment(
            db_path,
            listing_records=[
                {
                    "house_number": "101",
                    "street_name": "MAPLE ST NW",
                    "bedrooms": 3,
                    "bathrooms": 2.0,
                    "source_record_id": "listing-1",
                    "observed_at": "2026-04-02T01:00:00+00:00",
                },
                {
                    "house_number": "102",
                    "street_name": "MAPLE ST NW",
                    "bedrooms": 4,
                    "bathrooms": 2.5,
                    "source_record_id": "listing-2",
                    "observed_at": "2026-04-02T01:05:00+00:00",
                },
            ],
            permit_records=[
                {
                    "house_number": "103",
                    "street_name": "MAPLE ST NW",
                    "permit_description": "Interior renovation for 3 bedroom 2 bathroom home",
                    "source_record_id": "permit-1",
                    "observed_at": "2026-04-02T01:10:00+00:00",
                }
            ],
            config=EnrichmentConfig(
                training_min_confidence=0.80,
                min_training_rows=3,
                ambiguous_export_path=str(Path(temp_dir.name) / "ambiguous.csv"),
            ),
        )

        conn = connect(db_path)
        self.addCleanup(conn.close)
        metadata = json.loads(
            conn.execute("SELECT metadata_json FROM run_logs WHERE run_id = ?", (result["run_id"],)).fetchone()[0]
        )
        prod_rows = {
            row["canonical_location_id"]: dict(row)
            for row in conn.execute(
                """
                SELECT canonical_location_id, bedrooms, bathrooms, bedrooms_estimated,
                       bathrooms_estimated, source_type, source_name, confidence
                FROM property_attributes_prod
                """
            ).fetchall()
        }

        self.assertEqual(metadata["training"]["training_rows"], 3)
        self.assertTrue(metadata["training"]["imputation_enabled"])
        self.assertEqual(len(prod_rows), 4)
        self.assertEqual(prod_rows["loc-1"]["source_type"], "observed")
        self.assertEqual(prod_rows["loc-2"]["source_type"], "observed")
        self.assertEqual(prod_rows["loc-3"]["source_type"], "inferred")
        self.assertEqual(prod_rows["loc-4"]["source_type"], "imputed")
        self.assertIsNotNone(prod_rows["loc-4"]["bedrooms_estimated"])
        self.assertIsNotNone(prod_rows["loc-4"]["bathrooms_estimated"])


class SourceClientLoaderTests(unittest.TestCase):
    def test_csv_loader_applies_field_map_and_address_parsing(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        csv_path = Path(temp_dir.name) / "listings.csv"
        map_path = Path(temp_dir.name) / "map.json"
        csv_path.write_text(
            "\n".join(
                [
                    "property_address,beds,baths,listing_id,listed_at",
                    "5713 141 Avenue NW,4,2.5,listing-001,2026-03-31T12:00:00+00:00",
                ]
            ),
            encoding="utf-8",
        )
        map_path.write_text(
            json.dumps(
                {
                    "address": "property_address",
                    "bedrooms": "beds",
                    "bathrooms": "baths",
                    "source_record_id": "listing_id",
                    "observed_at": "listed_at",
                }
            ),
            encoding="utf-8",
        )

        temp_db = Path(temp_dir.name) / "loader.db"
        conn = connect(temp_db)
        init_db(conn)
        client = SourceClients(conn, listing_json_path=csv_path, listing_field_map_path=map_path)

        records = client.load_listing_candidates()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["house_number"], "5713")
        self.assertEqual(records[0]["street_name"], "141 AVE NW")
        self.assertEqual(records[0]["bedrooms"], "4")
        self.assertEqual(records[0]["source_record_id"], "listing-001")


class ShadowModeTests(unittest.TestCase):
    def _seed_property_locations(self, conn) -> None:
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
            [
                {
                    "canonical_location_id": "loc-1",
                    "assessment_year": 2026,
                    "assessment_value": 410000.0,
                    "suite": None,
                    "house_number": "101",
                    "street_name": "MAPLE ST NW",
                    "legal_description": "PLAN 1 BLK 1 LOT 1",
                    "zoning": "RF3",
                    "lot_size": 400.0,
                    "total_gross_area": "160",
                    "year_built": 2005,
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
                    "lat": 53.55,
                    "lon": -113.50,
                    "point_location": None,
                    "source_ids_json": "[]",
                    "record_ids_json": "[]",
                    "link_method": "seed",
                    "confidence": 0.99,
                    "updated_at": "2026-04-02T00:00:00+00:00",
                },
                {
                    "canonical_location_id": "loc-2",
                    "assessment_year": 2026,
                    "assessment_value": 420000.0,
                    "suite": None,
                    "house_number": "102",
                    "street_name": "MAPLE ST NW",
                    "legal_description": "PLAN 1 BLK 1 LOT 2",
                    "zoning": "RF3",
                    "lot_size": 410.0,
                    "total_gross_area": "165",
                    "year_built": 2006,
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
                    "lat": 53.5505,
                    "lon": -113.5005,
                    "point_location": None,
                    "source_ids_json": "[]",
                    "record_ids_json": "[]",
                    "link_method": "seed",
                    "confidence": 0.99,
                    "updated_at": "2026-04-02T00:00:00+00:00",
                },
                {
                    "canonical_location_id": "loc-3",
                    "assessment_year": 2026,
                    "assessment_value": 430000.0,
                    "suite": None,
                    "house_number": "103",
                    "street_name": "MAPLE ST NW",
                    "legal_description": "PLAN 1 BLK 1 LOT 3",
                    "zoning": "RF3",
                    "lot_size": 420.0,
                    "total_gross_area": "170",
                    "year_built": 2007,
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
                    "lat": 53.551,
                    "lon": -113.501,
                    "point_location": None,
                    "source_ids_json": "[]",
                    "record_ids_json": "[]",
                    "link_method": "seed",
                    "confidence": 0.99,
                    "updated_at": "2026-04-02T00:00:00+00:00",
                },
                {
                    "canonical_location_id": "loc-4",
                    "assessment_year": 2026,
                    "assessment_value": 435000.0,
                    "suite": None,
                    "house_number": "104",
                    "street_name": "MAPLE ST NW",
                    "legal_description": "PLAN 1 BLK 1 LOT 4",
                    "zoning": "RF3",
                    "lot_size": 430.0,
                    "total_gross_area": "172",
                    "year_built": 2008,
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
                    "lat": 53.5515,
                    "lon": -113.5015,
                    "point_location": None,
                    "source_ids_json": "[]",
                    "record_ids_json": "[]",
                    "link_method": "seed",
                    "confidence": 0.99,
                    "updated_at": "2026-04-02T00:00:00+00:00",
                },
            ],
        )

    def test_shadow_mode_disables_prod_promotion_and_writes_review_exports(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "shadow.db"
        conn = connect(db_path)
        init_db(conn)
        self._seed_property_locations(conn)
        conn.commit()
        conn.close()

        result = run_bedbath_enrichment(
            db_path,
            listing_records=[
                {
                    "house_number": "101",
                    "street_name": "MAPLE ST NW",
                    "bedrooms": 3,
                    "bathrooms": 2.0,
                    "source_record_id": "listing-1",
                },
                {
                    "house_number": "102",
                    "street_name": "MAPL ST NW",
                    "bedrooms": 4,
                    "bathrooms": 2.5,
                    "source_record_id": "listing-2",
                },
            ],
            permit_records=[
                {
                    "house_number": "103",
                    "street_name": "MAPLE ST NW",
                    "permit_description": "New layout for 3 bedroom 2 bathroom home",
                    "source_record_id": "permit-1",
                }
            ],
            config=EnrichmentConfig(
                shadow_mode=True,
                promotion_target="disabled",
                review_export_dir=str(Path(temp_dir.name) / "review"),
                ambiguous_export_path=str(Path(temp_dir.name) / "ambiguous.csv"),
                min_training_rows=3,
                training_min_confidence=0.80,
            ),
        )

        conn = connect(db_path)
        self.addCleanup(conn.close)
        prod_count = conn.execute("SELECT COUNT(*) FROM property_attributes_prod").fetchone()[0]
        staging_count = conn.execute("SELECT COUNT(*) FROM property_attributes_staging WHERE run_id = ?", (result["run_id"],)).fetchone()[0]

        self.assertEqual(prod_count, 0)
        self.assertGreater(staging_count, 0)
        self.assertTrue(result["report"]["real_feed_readiness_checklist"]["promotion_still_disabled"])
        self.assertIn("confidence_buckets", result["report"])
        self.assertIn("shadow_run_summary", result["report"])
        for path in result["report"]["review_exports"].values():
            self.assertTrue(Path(path).exists(), path)

    def test_shadow_target_table_is_isolated_from_prod(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "shadow-target.db"
        conn = connect(db_path)
        init_db(conn)
        self._seed_property_locations(conn)
        conn.commit()
        conn.close()

        result = run_bedbath_enrichment(
            db_path,
            listing_records=[
                {
                    "house_number": "101",
                    "street_name": "MAPLE ST NW",
                    "bedrooms": 3,
                    "bathrooms": 2.0,
                    "source_record_id": "listing-1",
                }
            ],
            config=EnrichmentConfig(
                shadow_mode=True,
                promotion_target="shadow",
                shadow_table_name="property_attributes_shadow",
                review_export_dir=str(Path(temp_dir.name) / "review"),
                ambiguous_export_path=str(Path(temp_dir.name) / "ambiguous.csv"),
            ),
        )

        conn = connect(db_path)
        self.addCleanup(conn.close)
        prod_count = conn.execute("SELECT COUNT(*) FROM property_attributes_prod").fetchone()[0]
        shadow_count = conn.execute("SELECT COUNT(*) FROM property_attributes_shadow").fetchone()[0]

        self.assertEqual(prod_count, 0)
        self.assertGreater(shadow_count, 0)
        self.assertEqual(result["report"]["real_feed_readiness_checklist"]["promotion_still_disabled"], False)


if __name__ == "__main__":
    unittest.main()
