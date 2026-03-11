# Quickstart: UC-03 Map-Click Estimate

This plan defines the UI/API contract and data model for the map-click estimate flow. Implementation is not yet present in the repository.

## Expected Runtime Shape
- **Frontend**: static HTML/CSS/JS served from `frontend/`
- **Backend**: Python HTTP service in `backend/` exposing the estimate API

## When Implementation Exists
- Start backend service (Python 3.x) from `backend/`
- Serve frontend files from `frontend/` (static server)
- Open the map page and click a location to request an estimate

## Tests
- Acceptance tests: `Acceptance Tests/UC-03-AT.md`
- Unit/integration tests to be added per constitution gates
