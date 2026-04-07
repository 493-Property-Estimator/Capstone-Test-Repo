# Group 14 Capstone Repo

For AI-agent onboarding, read `AGENTS.md` first.

## Current Status

This repository currently contains:

- the full user-story and per-feature spec structure under `specs/`
- a shared frontend/backend API contract in `frontend_api_contract.md`
- a MapLibre-based modular frontend in `src/frontend/`
- a FastAPI backend in `src/backend/`
- a local SQLite feature store in `src/data_sourcing/open_data.db`

## Frontend Status

The frontend currently implements the main user-facing application for the frontend-owned stories:

- address search, resolution, and ambiguous-candidate handling
- map click selection with drag guards
- MapLibre + OpenStreetMap rendering for the Edmonton area
- DB-backed assessment property clustering and individual property rendering
- simplified property hover card and right-side detail panel
- open-data layer toggles and viewport refresh handling
- estimate request form with minimal and standard property details
- estimate criteria controls for factor inclusion, response detail options, and weighting sliders
- estimate rendering, confidence display, top-factor rendering, and warning UI
- client-side validation and invalid-input messaging

The current frontend is organized as:

- `src/frontend/index.html`
- `src/frontend/styles/app.css`
- `src/frontend/src/app.js`
- `src/frontend/app.env`
- feature modules under `src/frontend/src/features/`
- map integration under `src/frontend/src/map/`
- backend integration client under `src/frontend/src/services/api/apiClient.js`
- frontend tests under `src/frontend/tests/`

## Frontend Runtime Behavior

The frontend is environment-driven through `src/frontend/app.env` and `src/frontend/src/config.js`.

Important runtime behavior:

- the frontend targets `http://localhost:8000/api/v1` by default
- live API mode is preferred unless overridden by env settings
- assessment properties are requested from the backend `/api/v1/properties` endpoint, not from a CSV file
- property clustering is handled by the backend response mode and rendered by MapLibre in the browser
- the main map UI uses a collapsible map-side layer panel rather than a left-column layer list
- selecting a property by map click or search can open the right-side property detail panel
- the estimate request includes optional factor criteria and output-detail options when enabled in the UI

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
python3 -m uvicorn src.backend.src.app:app --reload --port 8000
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
2. `python3 -m uvicorn src.backend.src.app:app --reload --port 8000`
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

The root property assessment CSV, when present, is treated as an ingestion/bootstrap source only. The running app does not read that CSV directly. In live mode, the frontend requests property and layer data from the backend, and the backend serves those responses from the SQLite feature store.

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
- That value is configured through `src/frontend/app.env` and `src/frontend/src/config.js`.
- The backend defaults to `src/data_sourcing/open_data.db` unless `DATA_DB_PATH` is set.
- In live mode, assessment properties are served from the SQLite database through backend endpoints such as `/api/v1/properties`; the frontend does not read the root assessment CSV directly.
- The browser needs internet access for:
  - MapLibre/OpenStreetMap tile loading
- Map clicks send coordinate payloads to the backend through the map-click resolution endpoint.
- A guard is in place so hold-and-drag map movement does not send click payloads.
- Search behavior, property viewport cache timing, property limits, and layer refresh debounce values are configurable from frontend env settings.
- The estimate endpoint expects a valid API token when backend auth is enabled; the frontend token must match the backend token.

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

Run all Python tests in the repository (existing + new, including `tests/` and `src/backend/tests/`):

```bash
npm run test:python:all
```

Run frontend tests:

```bash
npm run test:frontend
```

Run frontend coverage:

```bash
npm run test:frontend:coverage
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

Latest verified frontend automated result:

- tests: `19/19` passing
- line coverage: `100.00%`
- branch coverage: `100.00%`
- function coverage: `99.53%`

## Next Integration Steps

- continue aligning backend response payloads with `frontend_api_contract.md`
- verify all enabled layers against the latest database contents and backend query support
- extend frontend acceptance-flow evidence as new UI features are added
