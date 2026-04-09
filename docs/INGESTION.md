# Ingestion Guide (CLI + Frontend)

This project is **local-first**: ingestion pipelines populate a local SQLite database, the backend serves data from that database, and the frontend consumes backend endpoints.

## Where data lives

- Default SQLite feature store: `src/data_sourcing/open_data.db`
- CLI commands accept `--db` to point at a specific database file.
- The backend reads `DATA_DB_PATH` (defaults to `src/data_sourcing/open_data.db`).

If you ingest into one DB file but the backend is pointed at a different DB file, the UI will look “empty” even though ingestion succeeded.

## CLI ingestion (`./ingest`)

The repo provides a stable ingestion launcher:

```bash
./ingest --help
```

Common workflows:

```bash
# 1) Initialize schema (creates tables if missing).
./ingest init-db

# 2) Inspect configured sources.
./ingest list-sources
./ingest show-source --key geospatial.parks

# 3) Ingest everything enabled in the registry.
./ingest ingest

# 4) Ingest a single source, overriding where the data file comes from.
./ingest ingest --source-key geospatial.parks --source 'geospatial.parks=src/data_sourcing/data/Parks_20260320.zip'

# 5) Run the refresh wrapper (on-demand or scheduled-style run).
./ingest run-refresh --trigger on_demand

# 6) Quick DB introspection.
./ingest db-path
./ingest db-summary
```

Source registry:

- `src/data_sourcing/sources/source_registry.json`

### Auto-discover + ingest downloaded files

If you have a folder of downloaded datasets under `src/data_sourcing/data/`, you can use:

```bash
python3 scripts/ingest_data_folder.py --dry-run
python3 scripts/init_and_ingest_open_data.py --db src/data_sourcing/open_data.db
```

These scripts match files by stable name fragments and choose the most recently modified match.

## Frontend ingestion (Upload page)

The frontend includes an **Ingestion** page (sidebar → “Data Ingestion”) that uploads a file to the backend and triggers an ingestion run.

### Requirements

- Backend must be running (default API base URL is `http://localhost:8000/api/v1`).
- Frontend must be configured to use the live API:
  - `src/frontend/app.env`:
    - `PREFER_LIVE_API=1`
    - `ALLOW_MOCK_FALLBACK=0` (recommended for ingestion)

### What the UI calls

- `POST /api/v1/jobs/ingest` (multipart form-data)
- Implemented in `src/backend/src/api/ingestion_jobs.py`

Form fields:

- `source_name`: a human label for the run (e.g. `parks_2026_q2`)
- `dataset_type`: one of the supported types below
- `trigger`: `on_demand` | `scheduled` | `manual_review` (recorded in run metadata)
- `validate_only`: when true, validates the uploaded file but does not ingest/promote
- `overwrite`: forwarded by the UI; behavior depends on the ingestion pipeline
- `file`: the dataset file you selected

Uploaded files are written to a temporary file during ingestion and deleted afterwards.

### Supported dataset types

The upload endpoint supports a small set of “UI-friendly” dataset types that map onto canonical ingestion source keys:

| UI `dataset_type` | Ingestion `source_key` |
|---|---|
| `assessment_properties` | `assessments.property_tax_csv` |
| `schools` | `geospatial.school_locations` |
| `parks` | `geospatial.parks` |
| `playgrounds` | `geospatial.playgrounds` |
| `transit_stops` | `transit.ets_stops` |

Allowed file extensions are currently: `csv`, `json`, `geojson`, `zip`.

### Schema validation (what “file kind cannot be ingested” means)

Before ingestion starts, the backend reads the uploaded file and checks that it contains required fields for the selected dataset type.

- Field matching is **normalized** (case-insensitive, non-alphanumeric characters removed).
- GeoJSON is accepted if the backend can detect `lat/lon` from a point geometry, or from properties.

Required fields (aliases shown as `/` groups):

- `assessment_properties`: `assessmentvalue/assessedvalue`, plus `lat/latitude`, plus `lon/lng/longitude`
- `schools`: `name/schoolname`, plus `lat/latitude`, plus `lon/lng/longitude`
- `parks`: `name/officialname`, plus `lat/latitude`, plus `lon/lng/longitude`
- `playgrounds`: `name`, plus `lat/latitude`, plus `lon/lng/longitude`
- `transit_stops`: `stopid/entityid`, plus `name/stopname`, plus `lat/latitude/stoplat`, plus `lon/lng/longitude/stoplon`

### What to expect after a successful ingestion

- The backend DB is updated (staging tables then promoted tables, depending on the pipeline).
- Refresh the map view; the affected layer/properties should reflect the new data as you pan/zoom.
- If nothing changes:
  - Confirm `DATA_DB_PATH` (backend) matches the `--db` you used on CLI or the DB the backend was pointed at while ingesting via the UI.
  - Confirm the layer is enabled (`ENABLED_LAYERS` in `src/frontend/app.env` and backend settings).

