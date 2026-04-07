# AGENTS: Comprehensive Project Guide

This file is for future AI agents and human maintainers. It is intentionally explicit and complete.

## 1) Project identity

This repository implements an Edmonton-focused property intelligence application:

- Input modes: address search, map click, or coordinates.
- Outputs: estimate value + range + confidence + factor breakdown + warnings.
- Map overlays: open-data layers (schools, parks, playgrounds, police stations, transit, assessment properties).
- Data foundation: local SQLite feature store populated by ingestion pipelines from open datasets.

Primary runtime is local-first (backend + frontend + SQLite).

## 2) Canonical source of truth

There are duplicate backend trees:

- `backend/`
- `src/backend/`

The active runtime path is `backend.src...` (for example `backend.src.app:app`).
Treat `backend/` as canonical unless a task explicitly says otherwise.

## 3) High-level architecture

### 3.1 Frontend (`src/frontend/`)

- `src/frontend/index.html`: root UI shell.
- `src/frontend/src/app.js`: app composition root, controller wiring, store setup.
- `src/frontend/src/config.js`: runtime config defaults + optional `/app.env` overrides.
- `src/frontend/src/services/api/apiClient.js`: HTTP calls to backend with optional mock fallback logic.
- `src/frontend/src/features/*`: functional modules:
  - `search/`
  - `mapSelection/`
  - `layers/`
  - `estimate/`
  - `warnings/`
  - `propertyDetails/`
- `src/frontend/src/map/mapAdapter.js`: map abstraction and map event integration.
- `src/frontend/src/state/store.js`: app state store.

### 3.2 Backend (`backend/src/`)

- `backend/src/app.py`: FastAPI app bootstrap, middleware, router mounting, startup/shutdown hooks.
- `backend/src/config.py`: environment-driven settings and defaults.
- `backend/src/api/*`: HTTP endpoints.
- `backend/src/services/*`: auth, validation, cache, routing, metrics, feature helpers.
- `backend/src/db/queries.py`: SQL query layer over SQLite.
- `backend/src/jobs/precompute_grid.py`: compute grid-level aggregate features.

### 3.3 Data sourcing (`src/data_sourcing/`)

- `src/data_sourcing/cli.py`: canonical ingestion CLI definitions.
- `src/data_sourcing/service.py`: orchestration layer used by CLI/server workflows.
- `src/data_sourcing/pipelines.py`: ingest/transform/promote pipeline implementations.
- `src/data_sourcing/database.py`: DB schema/init + utility persistence helpers.
- `src/data_sourcing/sources/source_registry.json`: source registry.
- `src/data_sourcing/open_data.db`: default SQLite store consumed by backend.

### 3.4 Estimator (`src/estimator/`)

- `src/estimator/property_estimator.py`: primary valuation engine.
- `src/estimator/proximity.py`: nearest-property and proximity helper logic.
- `src/estimator/__init__.py`: exports estimator entrypoints used by backend.

## 4) Runtime boot sequence

When backend starts (`backend/src/app.py`):

1. Loads settings from environment + `.env`.
2. Connects to SQLite (`data_db_path`) and ensures schema exists.
3. Warms heavy estimator dependencies once at startup (`warm_estimator`).
4. Initializes app state (`settings`, `metrics`, `cache`).
5. Optionally starts refresh scheduler loop if enabled.

Request middleware adds:

- `X-Request-Id` propagation/generation.
- Request metrics and error tracking.

## 5) API surface (current endpoints)

All routes are mounted under `/api/v1` except health routes.

### 5.1 Search

- `GET /api/v1/search/suggestions`
  - Query params: `q`, optional `limit`, optional `provider`.
  - Validates minimum query length.
  - `provider=osrm` currently falls back to DB path.
- `GET /api/v1/search/resolve`
  - Query params: `q`, optional `provider`.
  - Returns `resolved`, `ambiguous`, `not_found`, or `unsupported_region`.

### 5.2 Location resolution

- `POST /api/v1/locations/resolve-click`
  - Payload includes `coordinates`.
  - Rejects out-of-bounds clicks.
  - Resolves nearest known property for canonical context.

### 5.3 Estimates

- `POST /api/v1/estimates`
  - Auth protected by default (`Authorization: Bearer <token>` or `X-API-Key`).
  - Validates location and property detail inputs.
  - Resolves location via canonical id, address, coordinates, or polygon centroid.
  - Enforces Edmonton bounds.
  - Uses estimator with timeout budget.
  - Caches responses by normalized request + dataset version.
  - Returns estimate payload with range, factors, confidence, warnings, and cache status.

### 5.4 Layer data

- `GET /api/v1/layers/{layer_id}`
  - Query params: `west,south,east,north,zoom`.
  - Layer must be enabled in settings.
  - Returns GeoJSON-like features + legend.

### 5.5 Assessment property layer

- `GET /api/v1/properties`
  - Query params: `west,south,east,north,zoom`, optional `limit`, optional `cursor`.
  - Supports pagination cursor (`offset:N`).
  - Returns either clusters or explicit property markers based on zoom threshold.

### 5.6 Jobs and health

- `GET /api/v1/jobs/refresh-status`
- `POST /api/v1/jobs/precompute-grid`
- `GET /health`
- `GET /metrics`

## 6) Core config and environment variables

Primary settings live in `backend/src/config.py`. Most important:

- `DATA_DB_PATH` (default `src/data_sourcing/open_data.db`)
- `CACHE_TTL_SECONDS`
- `SEARCH_PROVIDER` (`db` or `osrm`; osrm currently fallback path in search routes)
- `ENABLED_LAYERS`
- `ESTIMATE_AUTH_REQUIRED` (default on)
- `ESTIMATE_API_TOKEN` (default `dev-local-token`)
- `ESTIMATE_TIME_BUDGET_SECONDS`
- `ENABLE_ROUTING`, `ROUTING_PROVIDER`
- `REFRESH_SCHEDULER_ENABLED`, `REFRESH_SCHEDULE_SECONDS`
- search/property limits (`SEARCH_*`, `PROPERTIES_*`)

Frontend runtime defaults live in `src/frontend/src/config.js` and can be overridden via `/app.env`.
Important frontend defaults:

- `API_BASE_URL=http://localhost:8000/api/v1`
- `PREFER_LIVE_API=1`
- `ALLOW_MOCK_FALLBACK=1`
- `ESTIMATE_API_TOKEN=dev-local-token`
- `ENABLED_LAYERS=schools,parks,playgrounds,police_stations,transit_stops,assessment_properties`

## 7) Canonical commands

Run from repo root unless specified.

### 7.1 Setup and run

```bash
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
./ingest init-db
python3 -m uvicorn backend.src.app:app --reload --port 8000
python3 -m http.server 8080 --directory src/frontend
```

Alternative scripts from `package.json`:

```bash
npm run backend
npm run frontend
```

### 7.2 Tests

```bash
# Python tests (repo-wide)
python3 -m pytest

# Frontend tests
npm run test:frontend
npm run test:frontend:coverage
```

### 7.3 Ingestion CLI (`./ingest`)

Supported commands:

- `init-db`
- `ingest`
- `run-refresh`
- `list-sources`
- `show-source`
- `db-summary`
- `db-path`
- `ingest-bedbath`

Examples:

```bash
./ingest list-sources
./ingest ingest
./ingest run-refresh --trigger on_demand
./ingest db-summary
```

## 8) Data flow summary

1. Source registry defines datasets and pipeline mappings.
2. Ingestion service validates source accessibility and runs pipeline plan with dependencies.
3. Pipelines load/normalize data into staging + promote to production tables.
4. Backend reads production tables via SQL query layer.
5. Frontend calls backend endpoints and renders map/estimate state.

Estimator flow:

1. Endpoint validates payload.
2. Resolves location.
3. Computes estimate via `estimate_property_value`.
4. Adapts estimator output to API schema.
5. Caches result keyed by location + attributes + dataset version.

## 9) Important behavior and constraints

- Edmonton bounds are enforced in multiple paths (search resolve status, click resolve, estimate validation).
- Estimate endpoint returns validation and business errors with structured error payloads.
- Search `provider=osrm` is accepted but currently resolved via DB fallback path in backend.
- Layer/property endpoints enforce `ENABLED_LAYERS` settings.
- Properties endpoint uses clustering below configured zoom threshold.
- Health endpoint is rate limited.

## 10) Testing and quality map

Primary test locations:

- Backend acceptance/integration/contract/support:
  - `backend/tests/acceptance/`
  - `backend/tests/integration/`
  - `backend/tests/contract/`
  - `backend/tests/support/`
- Frontend tests:
  - `src/frontend/tests/`
  - traceability notes in `src/frontend/tests/README.md`
- Additional root tests:
  - `tests/`

When changing API payloads:

- Update backend endpoint tests.
- Update frontend API client and controller tests.
- Check `frontend_api_contract.md` for contract consistency.

## 11) Repo navigation rules for agents

### 11.1 Where to focus first

- `backend/`
- `src/frontend/`
- `src/data_sourcing/`
- `src/estimator/`
- `README.md`
- `frontend_api_contract.md`

### 11.2 Large or legacy areas to avoid unless task-specific

- `TestingStage/osrm-backend/third_party/` (very large vendored tree)
- `TestingStage/` prototypes
- Historical process docs:
  - `Acceptance Tests/`
  - `Use Cases/`
  - `Scenarios/`
  - most of `Report/`

### 11.3 Token/time-efficient discovery pattern

1. Start with `AGENTS.md`, `README.md`, target module `app.py/config.py`.
2. Use `rg -n` for endpoint/function names.
3. Read only directly relevant files.
4. Avoid full-repo scans once target module is identified.

## 12) Common change playbooks

### 12.1 Add/modify endpoint

1. Update `backend/src/api/<module>.py`.
2. Add/update DB query helpers in `backend/src/db/queries.py` if needed.
3. Add validation/auth changes in `backend/src/services/`.
4. Add/update backend tests.
5. Update frontend API client + feature controller + frontend tests.

### 12.2 Add/modify ingestion source

1. Update `src/data_sourcing/sources/source_registry.json`.
2. Add/adjust pipeline handling in `src/data_sourcing/pipelines.py` and/or `service.py`.
3. Validate with `./ingest list-sources`, `./ingest ingest --source-key ...`.
4. Verify DB state with `./ingest db-summary`.

### 12.3 Estimation logic changes

1. Update `src/estimator/property_estimator.py` (and helpers).
2. Preserve response adapter expectations in `backend/src/api/estimates.py`.
3. Run backend tests targeting estimate-related coverage.

## 13) Operational notes

- Root `.env` is used by backend settings loader unless `SHARED_ENV_FILE` overrides it.
- Frontend auth token must match backend `ESTIMATE_API_TOKEN` when auth is enabled.
- Default DB file can be large; avoid unnecessary duplication in workflows.
- Some untracked/generated dataset artifacts may exist locally; do not assume they should be committed.

## 14) Quick orientation checklist for a new agent

1. Confirm task scope touches frontend, backend, ingestion, or estimator.
2. Confirm canonical backend tree (`backend/`).
3. Inspect relevant config defaults before code changes.
4. Implement minimal targeted change in correct module.
5. Run nearest tests.
6. Update docs/contracts if interface behavior changed.
