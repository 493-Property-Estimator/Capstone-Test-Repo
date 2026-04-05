# Harrison Frontend Session Status

codex resume 019cfd2c-7d81-7372-b0b3-ed24c4329b3c

## Branch State

- Current branch: `backend`
- Latest pushed commit: `5c5c86a`
- Main integration commit previously pushed to `master`: `2f3e746`

## Scope Implemented

Frontend implementation was treated as:

- Epic 1 frontend responsibilities
- Epic 3 frontend responsibilities
- Epic 5 frontend responsibilities
- Epic 6 frontend responsibilities
- `US-32` invalid-input/error UI
- UI/display portions of Epic 2

## Current Architecture

- Frontend is vanilla HTML/CSS/JavaScript under [`src/frontend/`](/root/Speckit-Constitution-To-Tasks/src/frontend)
- Map stack is now MapLibre with an OpenStreetMap raster basemap
- Frontend is configured to use the live backend API, not mock mode
- Assessment properties are loaded through a dedicated backend viewport endpoint:
  - `GET /api/v1/properties`
- Generic map overlays still use:
  - `GET /api/v1/layers/{layer_id}`

## Completed Work

- Built a modular frontend scaffold under [`src/frontend/`](/root/Speckit-Constitution-To-Tasks/src/frontend)
- Added address search UI and resolution flow
- Added map click selection flow with click-vs-drag guard
- Added estimate form, estimate panel, warnings, and confidence UI
- Added a shared API contract in [`frontend_api_contract.md`](/root/Speckit-Constitution-To-Tasks/frontend_api_contract.md)
- Added shared City of Edmonton data-fetching rules in [`specs/shared-data-fetching.md`](/root/Speckit-Constitution-To-Tasks/specs/shared-data-fetching.md)
- Migrated the map from Leaflet to MapLibre
- Exported the root assessment CSV into frontend property GeoJSON tiles for mock/testing
- Added a dedicated frontend property viewport path with:
  - abortable requests
  - stale-response protection
  - viewport caching
  - adjacent-viewport prefetch
- Added backend-side property viewport support in:
  - [`backend/src/api/properties.py`](/root/Speckit-Constitution-To-Tasks/backend/src/api/properties.py)
  - [`backend/src/services/property_viewport.py`](/root/Speckit-Constitution-To-Tasks/backend/src/services/property_viewport.py)
- Wired the live backend properties route into:
  - [`backend/src/app.py`](/root/Speckit-Constitution-To-Tasks/backend/src/app.py)
- Optimized backend property loading with:
  - SQL-level clustering for low zoom
  - SQL pagination for high zoom
  - in-memory viewport response caching
  - SQLite index creation for property viewport queries

## Important Files

- [`src/frontend/index.html`](/root/Speckit-Constitution-To-Tasks/src/frontend/index.html)
- [`src/frontend/styles/app.css`](/root/Speckit-Constitution-To-Tasks/src/frontend/styles/app.css)
- [`src/frontend/src/app.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/app.js)
- [`src/frontend/src/config.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/config.js)
- [`src/frontend/src/map/mapAdapter.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/map/mapAdapter.js)
- [`src/frontend/src/features/search/searchController.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/features/search/searchController.js)
- [`src/frontend/src/features/layers/layerController.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/features/layers/layerController.js)
- [`src/frontend/src/features/estimate/estimateController.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/features/estimate/estimateController.js)
- [`src/frontend/src/services/api/apiClient.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/services/api/apiClient.js)
- [`src/frontend/src/services/api/mockData.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/services/api/mockData.js)
- [`src/frontend/src/state/store.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/src/state/store.js)
- [`backend/src/app.py`](/root/Speckit-Constitution-To-Tasks/backend/src/app.py)
- [`backend/src/api/properties.py`](/root/Speckit-Constitution-To-Tasks/backend/src/api/properties.py)
- [`backend/src/services/property_viewport.py`](/root/Speckit-Constitution-To-Tasks/backend/src/services/property_viewport.py)
- [`frontend_api_contract.md`](/root/Speckit-Constitution-To-Tasks/frontend_api_contract.md)

## Local Environment

- Backend dependencies are installed in [`.venv`](/root/Speckit-Constitution-To-Tasks/.venv)
- `.venv/` is ignored in git and should remain local-only

## How To Run

1. Start the backend from repo root:

```bash
cd /root/Speckit-Constitution-To-Tasks
.venv/bin/uvicorn backend.src.app:app --reload --host 0.0.0.0 --port 8000
```

2. Start the frontend in another terminal:

```bash
cd /root/Speckit-Constitution-To-Tasks
python3 -m http.server 8080 --directory src/frontend
```

3. Open:

```text
http://localhost:8080
```

## Current Known Direction

- Fastest panning/property loading path is now backend-owned viewport clustering plus frontend viewport caching
- Long-term best scale path would still be backend-served vector/property tiles if the citywide dataset grows further

## Immediate Next Steps

- verify the live `/api/v1/properties` endpoint behavior in the browser
- test rapid pan/zoom across the city and watch for stale render or flicker issues
- verify cluster counts render correctly across zoom levels
- verify individual property rendering at high zoom in live mode
- if needed, move from viewport JSON responses to tile-style backend responses later
