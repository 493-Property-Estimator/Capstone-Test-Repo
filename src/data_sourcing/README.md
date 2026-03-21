# Data Sourcing Pipelines

This module ingests open datasets into a local SQLite database and runs downstream refinement pipelines.

## Quick Start

From repo root:

```bash
./ingest init-db
./ingest list-sources
```

Ingest a single source:

```bash
./ingest ingest --source-key geospatial.osm_alberta \
  --source geospatial.osm_alberta=src/data_sourcing/data/_tmp_alberta_layers/gis_osm_roads_free_1.shp
```

Ingest all enabled sources in registry:

```bash
./ingest ingest
```

Run scheduled/on-demand workflow wrapper:

```bash
./ingest run-refresh --trigger on_demand
```

## How It Works

1. Source definitions are loaded from `src/data_sourcing/sources/source_registry.json`.
2. For each requested source key, the loader validates and opens local/remote data.
3. Records are normalized via optional `field_map` and optional spatial/attribute filters.
4. Pipeline execution is chosen automatically (`geospatial`, `census`, `assessments`, `poi_standardization`, `deduplication`) with dependency expansion.
5. Data is written to staging tables, QA checks run, then promoted to production tables.
6. Run metadata, warnings, errors, and source checks are persisted.

Source check outcomes are written to `source_checks`. Run summaries are written to `run_logs` and `dataset_versions`.

## Shapefile Notes

- You only pass the `.shp` path to ingestion.
- Matching `.dbf` and `.shx` must exist in the same directory.
- Zip archives are also supported.
- For multi-layer zip archives, `shapefile_layer` in source registry selects the intended `.shp`.

## Common Sources in This Repo

### OSM Roads

- Source key: `geospatial.osm_alberta`
- Dataset target: `roads`
- Expected layer: `gis_osm_roads_free_1`
- Captures `fclass` as both:
  - `geospatial_* .raw_category`
  - `roads_* .road_type`
- Writes road entities and segments:
  - `roads_staging`, `roads_prod`
  - `road_segments_staging`, `road_segments_prod`

### OSM POIs

- Source key: `geospatial.osm_pois_alberta`
- Dataset target: `pois`
- Expected layer: `gis_osm_pois_free_1`
- Captures `fclass` as `raw_category`
- Writes geospatial POIs:
  - `geospatial_staging`, `geospatial_prod`
- Then POI typing/standardization can run:
  - `poi_standardized_staging`, `poi_standardized_prod`
  - `poi_types`

### Edmonton Property Assessment CSV

- Source key: `assessments.property_tax_csv`
- Supports file like:
  - `src/data_sourcing/data/Property_Assessment_Data_(Current_Calendar_Year)_20260320.csv`
- Maps account/address/value/class/lat/lon columns through `field_map`
- Writes:
  - compact assessment outputs: `assessments_staging`, `assessments_prod`
  - full pass-through record storage: `assessments_records_staging`, `assessments_records_prod`
- Raw source row is also preserved in `raw_record_json`.

Example:

```bash
./ingest ingest \
  --source-key assessments.property_tax_csv \
  --source 'assessments.property_tax_csv=src/data_sourcing/data/Property_Assessment_Data_(Current_Calendar_Year)_20260320.csv'
```

## Auto-Ingest Script for `data/` Folder

Script:

- `scripts/ingest_data_folder.py`

What it currently auto-detects:

- latest `Property_Assessment_Data_*.csv` -> `assessments.property_tax_csv`
- `_tmp_alberta_layers/gis_osm_roads_free_1.shp` (or Alberta zip fallback) -> `geospatial.osm_alberta`
- `_tmp_alberta_layers/gis_osm_pois_free_1.shp` (or Alberta zip fallback) -> `geospatial.osm_pois_alberta`

Usage:

```bash
python3 scripts/ingest_data_folder.py --dry-run
python3 scripts/ingest_data_folder.py
```

## Runtime Source Overrides

You can override source location at runtime without changing registry:

```bash
./ingest ingest --source-key geospatial.osm_pois_alberta \
  --source geospatial.osm_pois_alberta=src/data_sourcing/data/_tmp_alberta_layers/gis_osm_pois_free_1.shp
```

## Troubleshooting

- `shapefile ingestion requires the 'pyshp' package`:
  - install with `python3 -m pip install pyshp`
- `UNIQUE constraint failed ... geospatial_staging`:
  - duplicate OSM IDs are auto-disambiguated now; rerun with latest code
- command fails with `syntax error near unexpected token '('`:
  - wrap `--source key=path` in single quotes when filename contains parentheses
- ingest blocked by size limit:
  - raise `GEOSPATIAL_SIZE_LIMIT_BYTES` in `src/data_sourcing/config.py`

## Programmatic Use

```python
from data_sourcing.service import IngestionService

svc = IngestionService(db_path="/tmp/open_data.db")
svc.init_database()
out = svc.ingest(
    source_keys=["assessments.property_tax_csv"],
    source_overrides={
        "assessments.property_tax_csv": "src/data_sourcing/data/Property_Assessment_Data_(Current_Calendar_Year)_20260320.csv"
    },
)
```

## Data Dictionary

Key production tables and primary fields:

### Geospatial Core

- `geospatial_prod`
  - `dataset_type`: `roads`, `boundaries`, `pois`
  - `entity_id`: source entity identifier (dedup suffix may be added when needed)
  - `source_id`: source key or mapped source id
  - `name`: feature name or fallback identifier
  - `raw_category`: source-native category (for OSM, usually `fclass`)
  - `canonical_geom_type`: logical geometry type (`Point`, `MultiLineString`, `MultiPolygon`)
  - `lon`, `lat`: representative coordinate
  - `source_version`, `updated_at`

### Roads

- `roads_prod`
  - `road_id`, `source_id` (PK pair)
  - `road_name`
  - `road_type` (for OSM roads this is sourced from `fclass`)
  - `source_version`, `updated_at`
  - `metadata_json`

- `road_segments_prod`
  - `segment_id`, `source_id` (PK pair)
  - `road_id` (FK to `roads_prod`)
  - `sequence_no`
  - `segment_name`, `segment_type`
  - `lane_count`
  - `start_lon`, `start_lat`, `end_lon`, `end_lat`
  - `center_lon`, `center_lat`
  - `length_m`
  - `geometry_json` (array of coordinate pairs)
  - `source_version`, `updated_at`

### POI Standardization

- `poi_types`
  - `poi_type_id` (PK)
  - `canonical_category`
  - `canonical_subcategory`
  - `display_name`
  - `is_active`

- `poi_standardized_prod`
  - `poi_id`, `source_id` (PK pair)
  - `poi_type_id` (FK to `poi_types`)
  - `canonical_category`, `canonical_subcategory`
  - `raw_category`
  - `mapping_rule_id`, `mapping_rationale`
  - `taxonomy_version`, `mapping_version`
  - `unmapped` (0/1)

### Assessments

- `assessments_prod`
  - one selected record per canonical location
  - `canonical_location_id` (PK)
  - `assessment_year`
  - `assessment_value`
  - `chosen_record_id`
  - `confidence`

- `assessments_records_prod`
  - full pass-through record storage
  - `record_id`, `source_id` (PK pair)
  - `assessment_year`
  - `canonical_location_id`
  - `assessment_value`
  - address fields: `suite`, `house_number`, `street_name`
  - area fields: `neighbourhood_id`, `neighbourhood`, `ward`
  - classification fields: `tax_class`, `garage`, `assessment_class_1..3`, `assessment_class_pct_1..3`
  - spatial fields: `lat`, `lon`, `point_location` (`POINT (lon lat)` WKT string from source CSV)
  - QA/link fields: `link_method`, `confidence`, `ambiguous`, `quarantined`, `reason_code`
  - `raw_record_json` (original normalized source row)

### Operations and Monitoring

- `source_checks`: per-source accessibility/load checks before pipeline execution
- `run_logs`: per-pipeline run status, warnings, errors, metadata
- `dataset_versions`: promotion/version history
- `alerts`: pipeline/workflow alert events
