# Frontend Test Suite

This suite covers the frontend-owned user stories implemented in `src/frontend/src`.

## Acceptance Traceability

- `UC-01` Estimate by address
  - `controllers.test.js`
  - `map-app.test.js`
- `UC-02` Estimate by latitude/longitude
  - `controllers.test.js`
- `UC-03` Estimate by map click
  - `controllers.test.js`
  - `map-app.test.js`
- `UC-24` Address search in the map UI
  - `controllers.test.js`
  - `map-app.test.js`
- `UC-25` Toggle open-data layers
  - `layers-api.test.js`
  - `map-app.test.js`
- `UC-26` Missing-data warnings and confidence UI
  - `controllers.test.js`
- `UC-32` Clear invalid-input handling in the frontend/API client path
  - `controllers.test.js`
  - `layers-api.test.js`

## Test Types

- Unit coverage:
  - `config-live.test.js`
  - `config-fallback.test.js`
  - `config-store-utils.test.js`
  - `controllers.test.js`
  - `layers-api.test.js`
- Integration coverage:
  - `map-app.test.js`

## Commands

```bash
npm run test:frontend
npm run test:frontend:coverage
```
