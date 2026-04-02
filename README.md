# Group 14 Capstone Repo

## Current Status

This repository currently contains:

- the full user-story and per-feature spec structure under `specs/`
- a shared frontend/backend API contract in `frontend_api_contract.md`
- a modular frontend scaffold in `src/frontend/`
- a FastAPI backend scaffold in `src/backend/`

## Frontend Status

The frontend currently implements the UI-side skeleton for the stories that fall within frontend scope:

- address search and suggestion handling
- map click selection
- OpenStreetMap rendering for the Edmonton area
- open-data layer toggles and viewport refresh handling
- estimate request form with minimal and standard property details
- estimate rendering, confidence display, and warning UI
- client-side validation and invalid-input messaging

The current frontend is organized as:

- `src/frontend/index.html`
- `src/frontend/styles/app.css`
- `src/frontend/src/app.js`
- feature modules under `src/frontend/src/features/`
- backend integration client under `src/frontend/src/services/api/apiClient.js`

## How To Run

Install backend dependencies from repo root:

```bash
pip install -r src/backend/requirements.txt
pip install -r src/backend/requirements-dev.txt
```

### Frontend

Run directly from repo root:

```bash
python3 -m http.server 8080 --directory src/frontend
```

Or use the package script:

```bash
npm run frontend
```

Open:

```text
http://localhost:8080
```

### Backend

The backend reads the SQLite database from `src/data_sourcing/open_data.db` by default. If needed, set it explicitly:

```bash
export DATA_DB_PATH=src/data_sourcing/open_data.db
```

Run directly from repo root:

```bash
python3 -m uvicorn backend.src.app:app --reload --port 8000
```

Or use the package script:

```bash
npm run backend
```

The API will be available at:

```text
http://localhost:8000/api/v1
```

### Database

Initialize the SQLite database schema:

```bash
python3 -m src.data_sourcing.cli init-db --db src/data_sourcing/open_data.db
```

List configured ingestion sources:

```bash
python3 -m src.data_sourcing.cli list-sources --db src/data_sourcing/open_data.db
```

Run a refresh ingestion workflow:

```bash
python3 -m src.data_sourcing.cli run-refresh --db src/data_sourcing/open_data.db --trigger on_demand
```

If you want to ingest recognized local files from `src/data_sourcing/data`, use:

```bash
python3 scripts/init_and_ingest_open_data.py
```

## Runtime Notes

- The frontend expects the backend API at `http://localhost:8000/api/v1`.
- That value is configured in `src/frontend/src/config.js`.
- The backend defaults to `src/data_sourcing/open_data.db` unless `DATA_DB_PATH` is set.
- The browser needs internet access for:
  - Leaflet CDN assets
  - OpenStreetMap tile loading
- Map clicks send coordinate payloads to the backend through the map-click resolution endpoint.
- A guard is in place so hold-and-drag map movement does not send click payloads.

## Next Integration Steps

- connect the Python backend to the contract in `frontend_api_contract.md`
- test the frontend against live backend responses for search, estimate, and layer data
