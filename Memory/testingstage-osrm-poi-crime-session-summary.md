# TestingStage Session Summary

## Scope

Extended the `TestingStage` app to add OSRM routing features, broader POI querying, a crime page abstraction, richer neighbourhood summaries, and ingest support for new Edmonton POI datasets.

## Backend Changes

- Split `TestingStage/backend/server.py` into a thinner HTTP layer plus reusable services in `TestingStage/backend/services.py`.
- Added OSRM-backed service methods and API endpoints for:
  - nearest routable point
  - route between two points
  - travel matrix
- OSRM is used only for routing, not reverse geocoding or property lookup.
- Added database-backed nearest property lookup on the OSRM page using existing property tables.
- Added `POST /api/pois/query` for broader POI filtering.
- Added `POST /api/crime-summary` with a clean provider abstraction.
- Added support for neighbourhood summary detail levels:
  - `high`
  - `detailed`
- Detailed neighbourhood mode returns road length grouped by road type below the main summary.

## Frontend Changes

- Added new pages:
  - `TestingStage/frontend/osrm.html`
  - `TestingStage/frontend/crime.html`
- Added scripts:
  - `TestingStage/frontend/osrm-page.js`
  - `TestingStage/frontend/crime-page.js`
- Updated navigation across the existing pages to include `OSRM` and `Crime`.
- Changed the OSRM page layout from a 2x2 grid to a vertical stack of panels.
- Fixed dropdown population issues on `Crime` and `Top X nearby POIs`.
- `Crime` neighbourhood input is now a dropdown using `/api/neighborhoods`.
- `Top X nearby POIs` neighbourhood filter is now a dropdown with:
  - `No neighbourhood filter`
  - followed by all neighbourhoods

## Neighbourhood Summary Metrics

Original bed/bath plan was dropped because the current dataset does not yet contain those values reliably.

Neighbourhood summary now reports:

- average house age
- average house size
- rows used in average age
- rows used in average size
- garage yes row count
- garage known row count
- garage percentage
- total rows considered

Important implementation detail:

- `average_house_size` currently uses `lot_size` first
- if `lot_size` is missing, it falls back to `total_gross_area`
- user explicitly confirmed to continue using lot size for now

## Road Data

- Confirmed the road dataset includes road type/category values.
- These are stored through the ingest pipeline in:
  - `roads_prod.road_type`
  - `road_segments_prod.segment_type`
- A direct SQLite summary was generated later in the session to show total Edmonton road length by road type.

## Ingest / Schema Changes

- Extended POI schema in `src/data_sourcing/database.py` to include:
  - `raw_subcategory`
  - `neighbourhood`
  - `source_dataset`
  - `source_provider`
  - `metadata_json`
- Extended geospatial POI ingest in `src/data_sourcing/pipelines.py` to preserve source-specific metadata.
- Added registry entries in `src/data_sourcing/sources/source_registry.json` for:
  - `geospatial.business_census`
  - `geospatial.recreation_facilities`
- Updated `scripts/ingest_data_folder.py` to auto-detect:
  - `Edmonton Business Census*.csv|.zip`
  - `Recreation Facilities*.csv|.zip`
- Updated POI mapping rules in `src/data_sourcing/sources/poi_mapping.json`.

## Important Bug Fixes

- Fixed a JSON serialization crash during `business_census` ingest:
  - cause: source metadata included Python `date` values
  - fix: use `json.dumps(..., default=str)` for stored POI metadata
- Verified `geospatial.recreation_facilities` registry key exists and can ingest successfully.
- Observed SQLite `database is locked` when ingests were run in parallel against the same DB.
  - Recommendation: run ingests serially, not concurrently.

## Commands / Operational Notes

### Server

```bash
python3 TestingStage/backend/server.py
```

### OSRM env vars

```bash
export TESTING_STAGE_OSRM_BASE_URL=http://127.0.0.1:5000
export TESTING_STAGE_OSRM_PROFILE_DRIVING=car
export TESTING_STAGE_OSRM_PROFILE_WALKING=foot
export TESTING_STAGE_OSRM_PROFILE_BIKING=bicycle
```

These profile overrides are only needed if the local OSRM server uses `car/foot/bicycle` instead of `driving/walking/biking`.

### Ingest commands

```bash
./ingest init-db
./ingest ingest --source-key geospatial.business_census --source 'geospatial.business_census=src/data_sourcing/data/Edmonton Business Census_20260320.zip'
./ingest ingest --source-key geospatial.recreation_facilities --source 'geospatial.recreation_facilities=src/data_sourcing/data/Recreation Facilities_20260328.zip'
```

Run those serially.

## Testing / Verification

Added tests in:

- `tests/test_testingstage_services.py`

Verified with:

```bash
python3 -m unittest tests.test_testingstage_services
```

## Known Gaps

- No usable crime dataset or crime ingest pipeline currently exists in the repo DB.
- Crime page/API returns a clear unavailable/TODO response instead of fabricating data.
- Bed/bath neighbourhood metrics were removed because the data is not available yet.
- Business census ingest is large and may take noticeable time on the main DB.

## User Preferences / Decisions Captured

- Keep OSRM limited strictly to routing-related functionality.
- Do not use OSRM as a reverse geocoder or property lookup engine.
- Continue using lot size for the neighbourhood “average house size” metric.
- On the neighbourhood page:
  - preserve a high-level summary mode
  - add a detailed mode with road distance by road type below the summary
- On the OSRM page:
  - present blocks vertically, one after another
- On Crime and Top X pages:
  - neighbourhood input should be a dropdown
  - Top X should also include a no-filter option
