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

from src.data_sourcing.database import connect, init_db
from src.data_sourcing.pipelines import run_geospatial_ingest
from src.data_sourcing.source_loader import SourcePayload


class RoadEnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "roads.db"
        conn = connect(self.db_path)
        init_db(conn)
        conn.execute(
            """
            INSERT INTO roads_prod (
                road_id, source_id, road_name, road_type, metadata_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("1001", "geospatial.osm_alberta", "1001", "residential", "{}"),
        )
        conn.execute(
            """
            INSERT INTO road_segments_prod (
                segment_id, road_id, source_id, sequence_no, segment_name, segment_type, lane_count,
                start_lon, start_lat, end_lon, end_lat, center_lon, center_lat, length_m, geometry_json,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "seg-1",
                "1001",
                "geospatial.osm_alberta",
                1,
                "52 Avenue NW",
                "residential",
                None,
                -113.5000,
                53.5400,
                -113.4990,
                53.5400,
                -113.4995,
                53.5400,
                65.5,
                json.dumps([[-113.5000, 53.5400], [-113.4990, 53.5400]]),
                "{}",
            ),
        )
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("src.data_sourcing.pipelines.get_source_spec")
    @patch("src.data_sourcing.pipelines.load_payload_for_source")
    def test_edmonton_road_source_enriches_existing_rows_without_new_rows(
        self,
        mocked_load_payload,
        mocked_get_source_spec,
    ) -> None:
        mocked_get_source_spec.return_value = {
            "pipeline": "geospatial",
            "target_dataset": "roads",
            "promotion_mode": "enrich_existing",
        }
        mocked_load_payload.return_value = SourcePayload(
            metadata={"version": "2026.03", "publish_date": "2026-03-28"},
            records=[
                {
                    "entity_id": "rd-1",
                    "official_road_name": "52 Ave NW",
                    "municipal_segment_id": "RD-1290689",
                    "roadway_category": "Road",
                    "surface_type": "Roadway (Standard)",
                    "functional_class": "Local-Residential",
                    "jurisdiction": "City of Edmonton",
                    "quadrant": "NW",
                    "travel_direction": "2-way Road Segment (Default)",
                    "from_intersection_id": "INT-258471",
                    "to_intersection_id": "INT-271317",
                    "geometry_points": [
                        [-113.5000, 53.5400],
                        [-113.4990, 53.5400],
                    ],
                }
            ],
            size_bytes=256,
            checksum="test",
        )

        conn = connect(self.db_path)
        result = run_geospatial_ingest(conn, source_keys=["geospatial.roads"])

        road_count = conn.execute("SELECT COUNT(*) FROM roads_prod").fetchone()[0]
        segment_count = conn.execute("SELECT COUNT(*) FROM road_segments_prod").fetchone()[0]
        road_row = conn.execute(
            """
            SELECT road_name, official_road_name, jurisdiction, functional_class, quadrant, metadata_json
            FROM roads_prod
            WHERE road_id='1001' AND source_id='geospatial.osm_alberta'
            """
        ).fetchone()
        segment_row = conn.execute(
            """
            SELECT segment_name, municipal_segment_id, official_road_name, roadway_category,
                   surface_type, jurisdiction, functional_class, travel_direction,
                   quadrant, from_intersection_id, to_intersection_id, metadata_json
            FROM road_segments_prod
            WHERE segment_id='seg-1' AND source_id='geospatial.osm_alberta'
            """
        ).fetchone()
        conn.close()

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(road_count, 1)
        self.assertEqual(segment_count, 1)
        self.assertEqual(road_row["road_name"], "52 Ave NW")
        self.assertEqual(road_row["official_road_name"], "52 Ave NW")
        self.assertEqual(road_row["jurisdiction"], "City of Edmonton")
        self.assertEqual(road_row["functional_class"], "Local-Residential")
        self.assertEqual(road_row["quadrant"], "NW")
        self.assertEqual(segment_row["segment_name"], "52 Avenue NW")
        self.assertEqual(segment_row["municipal_segment_id"], "RD-1290689")
        self.assertEqual(segment_row["official_road_name"], "52 Ave NW")
        self.assertEqual(segment_row["roadway_category"], "Road")
        self.assertEqual(segment_row["surface_type"], "Roadway (Standard)")
        self.assertEqual(segment_row["jurisdiction"], "City of Edmonton")
        self.assertEqual(segment_row["functional_class"], "Local-Residential")
        self.assertEqual(segment_row["travel_direction"], "2-way Road Segment (Default)")
        self.assertEqual(segment_row["quadrant"], "NW")
        self.assertEqual(segment_row["from_intersection_id"], "INT-258471")
        self.assertEqual(segment_row["to_intersection_id"], "INT-271317")
        self.assertIn("edmonton", json.loads(road_row["metadata_json"]))
        self.assertIn("edmonton", json.loads(segment_row["metadata_json"]))


if __name__ == "__main__":
    unittest.main()
