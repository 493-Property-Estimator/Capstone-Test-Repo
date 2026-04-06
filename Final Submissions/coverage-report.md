# Frontend Coverage Report

- Date: 2026-04-04 America/Edmonton
- Command: `npm run test:frontend:coverage`
- Coverage tool: Node built-in coverage via `--experimental-test-coverage`
- Execution mode: Codex shell (same commands may be run locally as an alternative)
- Exit code: `0`

## Threshold Requirement

Project submission requirement for the frontend test deliverable:
- Unit + integration suites must achieve `100%` branch coverage
- Acceptance-flow coverage must cover all documented frontend user-story flows in scope

Final coverage run satisfied the branch-coverage requirement for the included frontend source files.

## Final Coverage Summary

| Scope | Lines | Branches | Functions |
|---|---:|---:|---:|
| All included frontend files | 100% | 100% | 97.21% |
| `src/frontend/src/app.js` | 100% | 100% | 90.00% |
| `src/frontend/src/config.js` | 100% | 100% | 100.00% |
| `src/frontend/src/features/estimate/estimateController.js` | 100% | 100% | 100.00% |
| `src/frontend/src/features/layers/layerController.js` | 100% | 100% | 100.00% |
| `src/frontend/src/features/mapSelection/mapSelectionController.js` | 100% | 100% | 100.00% |
| `src/frontend/src/features/search/searchController.js` | 100% | 100% | 92.86% |
| `src/frontend/src/features/warnings/warningController.js` | 100% | 100% | 100.00% |
| `src/frontend/src/map/mapAdapter.js` | 100% | 100% | 100.00% |
| `src/frontend/src/services/api/apiClient.js` | 100% | 100% | 88.89% |
| `src/frontend/src/state/store.js` | 100% | 100% | 100.00% |
| `src/frontend/src/utils/debounce.js` | 100% | 100% | 100.00% |
| `src/frontend/src/utils/dom.js` | 100% | 100% | 100.00% |

## Test Counts From Same Run

- Frontend automated suite: `14/14` passed
- Failed: `0`
- Skipped: `0`
- Cancelled: `0`

## Evidence Snippet

```text
file                           | line % | branch % | funcs %
------------------------------------------------------------
app.js                         | 100.00 |   100.00 |   90.00
config.js                      | 100.00 |   100.00 |  100.00
estimateController.js          | 100.00 |   100.00 |  100.00
layerController.js             | 100.00 |   100.00 |  100.00
mapSelectionController.js      | 100.00 |   100.00 |  100.00
searchController.js            | 100.00 |   100.00 |   92.86
warningController.js           | 100.00 |   100.00 |  100.00
mapAdapter.js                  | 100.00 |   100.00 |  100.00
apiClient.js                   | 100.00 |   100.00 |   88.89
store.js                       | 100.00 |   100.00 |  100.00
debounce.js                    | 100.00 |   100.00 |  100.00
dom.js                         | 100.00 |   100.00 |  100.00
------------------------------------------------------------
all files                      | 100.00 |   100.00 |   97.21
```

## Notes

The final run reflects the current integrated `merge-harrison` frontend state:
- MapLibre-based map adapter
- live/backend-aware API client with env-driven fallback settings
- layer controller caching, abort handling, and viewport refresh logic
- warning, search, estimate, and map-click flows under the frontend-owned scope

Coverage measurement excludes `src/frontend/src/services/api/mockData.js` from the command because the deliverable target is the maintained application logic, not the large mock fixture file.

## Interpretation of 100% Coverage

- `100%` in this report refers to measured branch coverage for the included frontend source files in the submission command.
- Acceptance validation should be framed separately as `100% flow coverage` for the documented frontend use cases in scope.
- This report does not claim exhaustive coverage of all theoretical production flows, especially those affected by third-party browser/runtime behavior or real network variability.
