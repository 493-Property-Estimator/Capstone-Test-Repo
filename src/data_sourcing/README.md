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
4. Pipeline execution is chosen automatically (`geospatial`, `transit`, `census`, `assessments`, `poi_standardization`, `deduplication`) with dependency expansion.
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
- Also writes merged POI entities for later application use:
  - `poi_staging`, `poi_prod`
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
  - merged per-location property rows: `property_locations_staging`, `property_locations_prod`
- Raw source row is also preserved in `raw_record_json`.

### Edmonton Property Information

- Source key: `assessments.property_information`
- Supports the downloaded city shapefile export or CSV override
- Merges into `property_locations_*`
- Intended to be loaded alongside `assessments.property_tax_csv` so address-matched rows are enriched instead of duplicated

### Edmonton Amenity Sources

- `geospatial.school_locations`
  - supports EPSB school locations ZIP or CSV
  - writes school POIs into `geospatial_prod`
- `geospatial.police_stations`
  - supports police station ZIP or CSV
  - writes police station POIs into `geospatial_prod`
- `geospatial.playgrounds`
  - supports playground ZIP or CSV
  - writes playground POIs into `geospatial_prod`
- `geospatial.parks`
  - supports parks ZIP or CSV
  - writes park POIs into `geospatial_prod`
- `geospatial.business_census`
  - supports Edmonton Business Census ZIP or CSV
  - writes business POIs into `geospatial_prod` and `poi_prod`
  - preserves neighbourhood, raw subcategory, dataset/provider, and source metadata for filtering
- `geospatial.recreation_facilities`
  - supports Recreation Facilities ZIP or CSV
  - writes recreation POIs into `geospatial_prod` and `poi_prod`
  - preserves category/type details for POI filtering
- `geospatial.roads`
  - uses the bundled `src/data_sourcing/sources/geospatial_roads.json` snapshot by default
  - writes `roads_prod` and `road_segments_prod`

### ETS Transit Feeds

- Source keys:
  - `transit.ets_stops`
  - `transit.ets_trips`
- Writes:
  - `transit_staging`, `transit_prod`

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

- matches by stable dataset name text in the path, not by the specific date suffix
- searches recursively under the chosen `data/` directory, so extracted shapefiles inside dated folders are also eligible
- latest `Property_Assessment_Data_*.csv` -> `assessments.property_tax_csv`
- latest `Property Information*.csv` or `Property Information*.zip` -> `assessments.property_information`
- latest `Edmonton Public School Board (EPSB)_School Locations_*.csv` or `.zip` -> `geospatial.school_locations`
- latest `Police Stations_*.csv` or `.zip` -> `geospatial.police_stations`
- latest `Playgrounds_*.csv` or `.zip` -> `geospatial.playgrounds`
- latest `Parks_*.csv` or `.zip` -> `geospatial.parks`
- latest `Edmonton Business Census*.csv` or `.zip` -> `geospatial.business_census`
- latest `Recreation Facilities*.csv` or `.zip` -> `geospatial.recreation_facilities`
- bundled `src/data_sourcing/sources/geospatial_roads.json` -> `geospatial.roads`
- latest `ETS Bus Schedule GTFS Data Feed - Stops*.zip` -> `transit.ets_stops`
- latest `ETS Bus Schedule GTFS Data Feed - Trips*.zip` -> `transit.ets_trips`
- optional with `--include-osm`:
  - `_tmp_alberta_layers/gis_osm_roads_free_1.shp` (or Alberta zip fallback) -> `geospatial.osm_alberta`
  - `_tmp_alberta_layers/gis_osm_pois_free_1.shp` (or Alberta zip fallback) -> `geospatial.osm_pois_alberta`

Usage:

```bash
python3 scripts/ingest_data_folder.py --dry-run
python3 scripts/ingest_data_folder.py
python3 scripts/ingest_data_folder.py --include-osm
python3 scripts/init_and_ingest_open_data.py
python3 scripts/init_and_ingest_open_data.py --dry-run
python3 scripts/init_and_ingest_open_data.py --include-osm
```

## Utility Scripts

- `scripts/init_and_ingest_open_data.py`
  - initializes the DB, discovers recognized local files under `src/data_sourcing/data`, and ingests them one-by-one
  - discovery now includes Edmonton property, amenity, roads, and transit datasets
  - use `--include-osm` to also pick up OSM roads/POIs when present
- `scripts/create_db_sample.py`
  - creates a smaller SQLite DB containing sampled rows from:
  - `property_locations_prod`
  - `assessments_prod`
  - `assessments_records_prod`
  - `poi_prod`
  - `poi_standardized_prod`
  - POI rows from `geospatial_prod`

Example:

```bash
python3 scripts/create_db_sample.py \
  --source-db src/data_sourcing/open_data.db \
  --output-db /tmp/open_data_sample.db \
  --property-limit 100 \
  --poi-limit 200
```

## Runtime Source Overrides

You can override source location at runtime without changing registry:

```bash
./ingest ingest --source-key geospatial.osm_pois_alberta \
  --source geospatial.osm_pois_alberta=src/data_sourcing/data/_tmp_alberta_layers/gis_osm_pois_free_1.shp
```

CSV overrides are now supported for local sources even when the registry entry is configured as a shapefile, as long as the CSV columns map cleanly to the source field map. For example:

```bash
./ingest ingest --source-key geospatial.parks \
  --source 'geospatial.parks=src/data_sourcing/data/Parks_20260324.csv'
```

```bash
./ingest ingest --source-key geospatial.playgrounds \
  --source 'geospatial.playgrounds=src/data_sourcing/data/Playgrounds_20260324.csv'
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
  - `official_road_name`, `jurisdiction`, `functional_class`, `quadrant`
  - `source_version`, `updated_at`
  - `metadata_json`

- `road_segments_prod`
  - `segment_id`, `source_id` (PK pair)
  - `road_id` (FK to `roads_prod`)
  - `sequence_no`
  - `segment_name`, `segment_type`
  - `lane_count`
  - `municipal_segment_id`
  - `official_road_name`, `roadway_category`, `surface_type`
  - `jurisdiction`, `functional_class`, `travel_direction`, `quadrant`
  - `from_intersection_id`, `to_intersection_id`
  - `start_lon`, `start_lat`, `end_lon`, `end_lat`
  - `center_lon`, `center_lat`
  - `length_m`
  - `geometry_json` (array of coordinate pairs)
  - `metadata_json`
  - `source_version`, `updated_at`

### POI Standardization

- `poi_prod`
  - `canonical_poi_id` (PK)
  - merged place row for later application use
  - `name`, `raw_category`, `address`, `lon`, `lat`
  - `source_ids_json`, `source_entity_ids_json`
  - `source_version`, `updated_at`

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

- `property_locations_prod`
  - merged one-row-per-location property table
  - `canonical_location_id` (PK)
  - assessment fields plus property-information enrichment fields
  - `legal_description`, `zoning`, `lot_size`, `total_gross_area`, `year_built`
  - address fields, classes, `lat`, `lon`, `point_location`
  - `source_ids_json`, `record_ids_json`, `link_method`, `confidence`, `updated_at`

### Transit

- `transit_prod`
  - `transit_type`, `entity_id`, `source_id` (PK triple)
  - supports `stops` and `trips`
  - stop fields (`stop_name`, `stop_code`, `stop_lat`, `stop_lon`, etc.)
  - trip fields (`route_id`, `service_id`, `trip_headsign`, `shape_id`, etc.)
  - representative `lon`, `lat`, and `geometry_json`

### Operations and Monitoring

- `source_checks`: per-source accessibility/load checks before pipeline execution
- `run_logs`: per-pipeline run status, warnings, errors, metadata
- `dataset_versions`: promotion/version history
- `alerts`: pipeline/workflow alert events
