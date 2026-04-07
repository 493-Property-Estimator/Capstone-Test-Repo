# Group 14 Capstone Repo

For AI-agent onboarding, read `AGENTS.md` first.

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

If you want the live database-backed app running locally, initialize the SQLite database first:

```bash
./ingest init-db
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

Recommended startup flow from the repo root:

1. `./ingest init-db`
2. `python3 -m uvicorn backend.src.app:app --reload --port 8000`
3. `python3 -m http.server 8080 --directory src/frontend`
4. Open `http://localhost:8080`

### Database

Initialize the SQLite database schema:

```bash
./ingest init-db
```

List configured ingestion sources:

```bash
./ingest list-sources
```

Run a refresh ingestion workflow:

```bash
./ingest run-refresh --trigger on_demand
```

Show the database file currently in use:

```bash
./ingest db-path
```

Show a readable database summary with schema and row counts:

```bash
./ingest db-summary
```

If you want to ingest recognized local files from `src/data_sourcing/data`, use:

```bash
python3 scripts/init_and_ingest_open_data.py
```

The root property assessment CSV is treated as an ingestion/bootstrap source when needed. The running app does not read that CSV directly. In live mode, the frontend requests property and layer data from the backend, and the backend serves those responses from the SQLite feature store.

### TestingStage Test Page

This repo also includes a simple combined frontend/backend playground that serves a test page against the sample SQLite database.

Run from the repo root:

```bash
python3 TestingStage/backend/server.py
```

Open:

```text
http://127.0.0.1:8010
```

## Runtime Notes

- The frontend expects the backend API at `http://localhost:8000/api/v1`.
- That value is configured in `src/frontend/src/config.js`.
- The backend defaults to `src/data_sourcing/open_data.db` unless `DATA_DB_PATH` is set.
- In live mode, assessment properties are served from the SQLite database through backend endpoints such as `/api/v1/properties`; the frontend does not read the root assessment CSV directly.
- The browser needs internet access for:
  - MapLibre/OpenStreetMap tile loading
- Map clicks send coordinate payloads to the backend through the map-click resolution endpoint.
- A guard is in place so hold-and-drag map movement does not send click payloads.

## Test Commands

Run the folder-specific Python suites:

```bash
npm run test:python:scripts
npm run test:python:estimator
npm run test:python:data-sourcing
```

Run all new Python suites together (`scripts/Tests`, `src/estimator/Tests`, `src/data_sourcing/Tests`):

```bash
npm run test:python:new
```

Run all Python tests in the repository (existing + new, including `tests/` and `backend/tests/`):

```bash
npm run test:python:all
```

Run frontend tests:

```bash
npm run test:frontend
```

Run full test sweep (Python + frontend):

```bash
npm run test:python:all
npm run test:frontend
```

Generate coverage reports for each new suite:

```bash
npm run test:python:coverage:scripts
npm run test:python:coverage:estimator
npm run test:python:coverage:data-sourcing
```

Coverage report output directories:

- `coverage/html/scripts`
- `coverage/html/estimator`
- `coverage/html/data-sourcing`

Generate full Python coverage across all Python tests:

```bash
npm run test:python:coverage:all
```

Full Python coverage output:

- HTML report: `coverage/html/all/index.html`
- XML report: `coverage/coverage.xml`

Generate frontend coverage:

```bash
npm run test:frontend:coverage
```

## Next Integration Steps

- connect the Python backend to the contract in `frontend_api_contract.md`
- test the frontend against live backend responses for search, estimate, and layer data
