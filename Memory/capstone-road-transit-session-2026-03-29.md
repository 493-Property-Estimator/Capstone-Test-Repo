# Capstone Road and Transit Session Summary

Date: 2026-03-29

## Road dataset work

- Reviewed the existing SQLite schema, ingest pipeline, source registry, and live `open_data.db`.
- Confirmed the production road network already came from `geospatial.osm_alberta` with 115,283 rows in both `roads_prod` and `road_segments_prod`.
- Found the Edmonton road dataset locally at `src/data_sourcing/data/Road Network_20260328.zip`.
- Changed the Edmonton road source to act as an enrichment source instead of inserting new road rows.
- Added new road fields to the schema:
  - `roads_*`: `official_road_name`, `jurisdiction`, `functional_class`, `quadrant`
  - `road_segments_*`: `municipal_segment_id`, `official_road_name`, `roadway_category`, `surface_type`, `jurisdiction`, `functional_class`, `travel_direction`, `quadrant`, `from_intersection_id`, `to_intersection_id`, `metadata_json`
- Added schema migration support for existing DB files.
- Implemented matching logic that maps Edmonton road centerlines onto existing road segments using normalized road name plus centroid proximity.
- Updated source discovery so the Edmonton road network zip is preferred when present.
- Ran the live enrichment against `src/data_sourcing/open_data.db`.
- Result:
  - road row count unchanged: 115,283
  - segment row count unchanged: 115,283
  - 12,714 existing road/segment rows enriched

## Transit work

- Reviewed the existing transit pipeline and found the repo already had `transit.ets_stops` and `transit.ets_trips` ingest support.
- Confirmed `transit_prod` existed but was empty in the current repository DB.
- Added backend transit query and planning support in `TestingStage/backend/services.py`:
  - list routes
  - list stops, optionally filtered by route
  - return route details and route geometry
  - plan a walking + transit journey using stop points and trip geometries
- The journey planner accepts either:
  - coordinates
  - address/property text resolved through the local property database
- The planner prefers fewer transfers first, then shorter total travel distance.
- Added new API endpoints in `TestingStage/backend/server.py`:
  - `GET /api/transit/routes`
  - `GET /api/transit/stops`
  - `GET /api/transit/route`
  - `POST /api/transit/journey`
- Added a new frontend TestingStage page:
  - `TestingStage/frontend/transit.html`
  - `TestingStage/frontend/transit-page.js`
- Added transit navigation links across the existing TestingStage pages.
- Transit ingestion was not run on live data in this workspace because the ETS zip files were not present under `src/data_sourcing/data` at the time of verification.

## Testing and verification

- Added regression test for Edmonton road enrichment.
- Added transit service tests covering:
  - route listing
  - route details
  - journey planning with address and coordinate input
- Ran and passed:
  - `python3 -m unittest tests.test_transit_services tests.test_testingstage_services tests.test_road_enrichment`
- Also passed:
  - Python syntax checks
  - `node --check TestingStage/frontend/transit-page.js`

## Ingest commands provided

The following `./ingest` commands were provided for the user:

```bash
./ingest init-db
./ingest ingest --source-key geospatial.roads --source "geospatial.roads=src/data_sourcing/data/Road Network_20260328.zip"
./ingest ingest --source-key transit.ets_stops --source "transit.ets_stops=src/data_sourcing/data/ETS Bus Schedule GTFS Data Feed - Stops_20260320.zip"
./ingest ingest --source-key transit.ets_trips --source "transit.ets_trips=src/data_sourcing/data/ETS Bus Schedule GTFS Data Feed - Trips_20260320.zip"
```

## Git cleanup guidance

- The user hit a GitHub push rejection because large cached shapefile artifacts had been committed.
- Guidance given:
  - if only in latest commit:
    - `git rm -r --cached src/data_sourcing/sources/cache`
    - `git commit --amend --no-edit`
  - if spread across multiple local commits:
    - `git filter-repo --path src/data_sourcing/sources/cache --invert-paths`
    - `git push --force-with-lease origin EstimatorTest`

