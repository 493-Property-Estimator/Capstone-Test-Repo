# Backend Implementation Plan (Aligned with frontend_api_contract.md and current codebase)

## 1. Backend Package + Entry
1. Create `backend/` with Python app entry (e.g., `backend/src/app.py`) and configuration (`backend/src/config.py`).
2. Wire router under `/api/v1` to match `frontend/src/services/api/apiClient.js`.
3. Ensure standard response shape with `request_id` and consistent error envelope.

## 2. Data Layer Integration (Existing Feature Store)
1. Use `src/data_sourcing/database.py` and `src/data_sourcing/config.py` for SQLite connections.
2. Add `backend/src/db/queries.py` with read helpers for:
   - `property_locations_prod`
   - `assessments_prod`
   - `geospatial_prod`
   - `poi_*`
   - `roads_*` and `road_segments_*`
   - `dataset_versions` and `run_logs` (freshness checks)

## 3. Core API Endpoints (Contract-First)
1. `GET /api/v1/search/suggestions` → `backend/src/api/search.py`
   - Uses `src/data_sourcing` data and `specs/shared-data-fetching.md` rules.
2. `GET /api/v1/search/resolve` → `backend/src/api/search.py`
   - Resolves address to canonical location and coverage status.
3. `POST /api/v1/locations/resolve-click` → `backend/src/api/locations.py`
   - Boundary check and canonical location lookup.
4. `POST /api/v1/estimates` → `backend/src/api/estimates.py`
   - Orchestrates feature retrieval + estimator signals.
   - Returns factor breakdown, confidence, warnings, missing factors.
5. `GET /api/v1/layers/{layer_id}` → `backend/src/api/layers.py`
   - Returns normalized GeoJSON with `source_meta`.
6. `GET /health`, `GET /metrics` → `backend/src/api/health.py`
   - Dependency checks and aggregated metrics.
7. `POST /api/v1/jobs/precompute-grid` → `backend/src/jobs/precompute_grid.py`
   - Triggers grid precompute workflow.

## 4. Validation + Error Formatting (UC-32)
1. Create `backend/src/services/validation.py`.
2. Enforce 400 vs 422 rules and structured error schema.
3. Align with `frontend_api_contract.md` standard error response.

## 5. Estimator Integration (No Final Valuation in Backend)
1. Build `backend/src/services/features.py` to call `src/estimator/proximity.py`.
2. Use estimator outputs to populate `factor_breakdown`.
3. Defer final price calculation if required; return factor inputs and metadata in contract shape.

## 6. Fallbacks, Partial Results, Caching
1. Add `backend/src/services/routing.py` with straight-line fallback logic.
2. Add `backend/src/services/warnings.py` to build warnings, missing_factors, and approximations.
3. Ensure partial responses return 200 with `status: "partial"`.
4. Add `backend/src/services/cache.py` and include cache metadata in responses.

## 7. Tests (Black-Box HTTP)
1. Acceptance tests for backend-covered UCs as HTTP tests:
   - UC-01, UC-02, UC-03, UC-04, UC-05
   - UC-23, UC-24, UC-25, UC-26, UC-27, UC-28, UC-29, UC-30, UC-31, UC-32
2. Contract tests for `frontend_api_contract.md` and spec `contracts/api.md`.
3. Integration tests that hit endpoints using a sample DB from `scripts/create_db_sample.py`.
4. Test runner uses `BASE_URL` (default `http://localhost:8000`) and runs against a live backend.

## How This Interacts With Existing Code
- Uses existing data store and ingestion:
  - `src/data_sourcing/` remains the source of truth for open-data ingestion and SQLite schema.
  - Backend reads from this DB and can trigger ingestion/precompute jobs.
- Uses existing estimator:
  - `src/estimator/proximity.py` is called by backend services to compute proximity features and distances.
- Serves the existing frontend:
  - Backend implements exactly what `frontend/src/services/api/apiClient.js` calls.

## Proposed File Structure (New)
backend/
  src/
    app.py
    config.py
    api/
      search.py
      locations.py
      estimates.py
      layers.py
      health.py
    services/
      validation.py
      features.py
      routing.py
      warnings.py
      cache.py
    db/
      connection.py
      queries.py
    jobs/
      precompute_grid.py
  tests/
    acceptance/
    contract/
    integration/
    support/
