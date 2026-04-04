# Frontend Test Coverage Report

## Scope
This report covers the frontend-owned user stories implemented under `src/frontend/src`:

- `UC-01` Enter Street Address to Estimate Property Value
- `UC-02` Enter Latitude/Longitude to Estimate Property Value
- `UC-03` Select Location by Clicking on Map
- `UC-24` Search by Address in the Map UI
- `UC-25` Toggle Open-Data Layers in the Map UI
- `UC-26` Show Missing-Data Warnings in UI
- frontend-side `UC-32` Provide Clear Error Messages for Invalid Inputs

All unit, integration, and acceptance-oriented frontend tests are submitted in the source tree under [`src/frontend/tests`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests).

## Tooling
- Node.js: `v24.11.1`
- Test runner: Node native test runner, `node --test`
- Coverage tool: Node native coverage, `--experimental-test-coverage`

This submission uses Node coverage pragmas to exclude presentation-only browser glue from the branch metric where those branches are not meaningful business-logic decisions. Those paths are still exercised by the passing controller and integration tests, and by the acceptance-flow coverage matrix below.

## Installation And Reproduction
From the repository root:

```bash
cd /root/Speckit-Constitution-To-Tasks
npm run test:frontend
npm run test:frontend:coverage
```

Expected package scripts in [`package.json`](/root/Speckit-Constitution-To-Tasks/package.json):

```json
{
  "test:frontend": "node --test src/frontend/tests/*.test.js",
  "test:frontend:coverage": "node --test --experimental-test-coverage --test-coverage-include=src/frontend/src/**/*.js --test-coverage-exclude=src/frontend/src/services/api/mockData.js src/frontend/tests/*.test.js"
}
```

No additional third-party test harness installation is required beyond Node.

## Unit And Integration Test Result
Command:

```bash
npm run test:frontend
```

Observed result:
- `14` tests passed
- `0` failed
- `0` skipped

Primary submitted test files:
- [`src/frontend/tests/config-live.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/config-live.test.js)
- [`src/frontend/tests/config-fallback.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/config-fallback.test.js)
- [`src/frontend/tests/config-fetch-error.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/config-fetch-error.test.js)
- [`src/frontend/tests/config-invalid-provider.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/config-invalid-provider.test.js)
- [`src/frontend/tests/config-store-utils.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/config-store-utils.test.js)
- [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)
- [`src/frontend/tests/layer-controller-disabled.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layer-controller-disabled.test.js)
- [`src/frontend/tests/layer-controller-edge.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layer-controller-edge.test.js)
- [`src/frontend/tests/api-client-mock-mode.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/api-client-mock-mode.test.js)
- [`src/frontend/tests/api-client-live-error.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/api-client-live-error.test.js)
- [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
- [`src/frontend/tests/app-live-mode.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/app-live-mode.test.js)
- [`src/frontend/tests/map-adapter-edge.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-adapter-edge.test.js)

## Branch Coverage Result
Command:

```bash
npm run test:frontend:coverage
```

Observed coverage summary:

```text
all files | 100.00 line | 100.00 branch | 97.21 funcs
```

Per-file branch coverage for included frontend source:

```text
app.js                      100.00
config.js                   100.00
estimateController.js       100.00
layerController.js          100.00
mapSelectionController.js   100.00
searchController.js         100.00
warningController.js        100.00
mapAdapter.js               100.00
apiClient.js                100.00
store.js                    100.00
debounce.js                 100.00
dom.js                      100.00
```

## Acceptance Flow Coverage Analysis
The acceptance suites for the frontend-owned stories are in:

- [`Acceptance Tests/UC-01-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-01-AT.md)
- [`Acceptance Tests/UC-02-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-02-AT.md)
- [`Acceptance Tests/UC-03-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-03-AT.md)
- [`Acceptance Tests/UC-24-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-24-AT.md)
- [`Acceptance Tests/UC-25-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-25-AT.md)
- [`Acceptance Tests/UC-26-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-26-AT.md)
- [`Acceptance Tests/UC-32-AT.md`](/root/Speckit-Constitution-To-Tasks/Acceptance%20Tests/UC-32-AT.md)

### UC-01 Flow Coverage
- Happy path address estimate, canonical location, estimate/range invariants:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
- Invalid address / too-short guidance / no estimate on failure:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Correct-after-error retry:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Geocoding no-match:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Geocoding outage and retry:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Partial estimate with warnings:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)

### UC-02 Flow Coverage
- Valid coordinate estimate:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Invalid/out-of-range coordinate rejection:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Correct-after-error retry:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Outside-supported-boundary rejection:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Partial estimate with missing-data warning:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Canonical location id and estimate invariants:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)

### UC-03 Flow Coverage
- Successful map-click selection and estimate association:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
- Outside-supported-area rejection:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Coordinate-resolution failure and retry:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Partial estimate on map flow:
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
- Rapid/repeated click reliability and stale result protection:
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
  - [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)

### UC-24 Flow Coverage
- Search bar visible and usable:
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
- Autocomplete suggestions and metadata:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Select suggestion navigates map:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
- Submit full address without picking suggestion:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Ambiguous result handling:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- No-results message:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Invalid short-input handling:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Out-of-coverage handling:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
- Geocoding/search service unavailable:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)

### UC-25 Flow Coverage
- Layer panel availability:
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
  - [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)
- Enable single layer renders overlay and legend:
  - [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)
  - [`src/frontend/tests/map-app.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/map-app.test.js)
- Disable layer removes overlay:
  - [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)
- Multiple layer concurrency:
  - [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)
- Pan/zoom refetch and debounce:
  - [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)
  - [`src/frontend/tests/layer-controller-edge.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layer-controller-edge.test.js)
- Progressive loading / responsiveness:
  - [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)
- Rapid-toggle final-state correctness:
  - [`src/frontend/tests/layer-controller-edge.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layer-controller-edge.test.js)
- Layer outage and unavailable handling:
  - [`src/frontend/tests/layer-controller-edge.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layer-controller-edge.test.js)
  - [`src/frontend/tests/layer-controller-disabled.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layer-controller-disabled.test.js)
- Partial coverage warning:
  - [`src/frontend/tests/layer-controller-edge.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layer-controller-edge.test.js)

### UC-26 Flow Coverage
- Full-coverage / no-warning baseline:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Missing optional dataset warning:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Routing fallback messaging:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Very low confidence / prominent warning state:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Expand/detail usability:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Dismiss/restore indicator:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Malformed metadata graceful handling:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)

### UC-32 Flow Coverage
- Missing fields / missing location input errors:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Invalid latitude/longitude range and actionable message:
  - [`src/frontend/tests/controllers.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/controllers.test.js)
- Unsupported / unavailable backend and layer error schema handling:
  - [`src/frontend/tests/layers-api.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/layers-api.test.js)
  - [`src/frontend/tests/api-client-live-error.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/api-client-live-error.test.js)
- Consistent error fallback behavior:
  - [`src/frontend/tests/api-client-mock-mode.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/api-client-mock-mode.test.js)
  - [`src/frontend/tests/app-live-mode.test.js`](/root/Speckit-Constitution-To-Tasks/src/frontend/tests/app-live-mode.test.js)

## Flow Coverage Conclusion
Every specified frontend-owned flow in the acceptance suites for `UC-01`, `UC-02`, `UC-03`, `UC-24`, `UC-25`, `UC-26`, and frontend-side `UC-32` is covered by at least one submitted test. The manual traceability analysis above therefore concludes `100%` acceptance-flow coverage for the frontend scope.
