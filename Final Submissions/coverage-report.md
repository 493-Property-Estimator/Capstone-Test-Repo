# Frontend Coverage Report

- Date: 2026-04-06 America/Edmonton
- Command: `npm run test:frontend:coverage`
- Coverage tool: Node built-in coverage via `--experimental-test-coverage`
- Frontend source under test: `src/frontend/src`
- Exit code: `0`

## Current Result

The latest verified frontend coverage run passes and meets the `100%` line-coverage and `100%` branch-coverage target for the included frontend source files.

| Scope | Lines | Branches | Functions |
|---|---:|---:|---:|
| All included frontend files | 100.00% | 100.00% | 99.50% |

## File-Level Summary

| File | Lines | Branches | Functions |
|---|---:|---:|---:|
| `src/frontend/src/app.js` | 100.00% | 100.00% | 88.89% |
| `src/frontend/src/config.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/features/estimate/estimateController.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/features/layers/layerController.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/features/mapSelection/mapSelectionController.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/features/propertyDetails/propertyDetailController.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/features/search/searchController.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/features/warnings/warningController.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/map/mapAdapter.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/services/api/apiClient.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/state/store.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/utils/debounce.js` | 100.00% | 100.00% | 100.00% |
| `src/frontend/src/utils/dom.js` | 100.00% | 100.00% | 100.00% |

## Test Count From Same Run

- Frontend automated suite: `19/19` passed
- Failed: `0`
- Skipped: `0`
- Cancelled: `0`

## Evidence Snippet

```text
file                             | line % | branch % | funcs %
--------------------------------------------------------------
app.js                           | 100.00 |   100.00 |   88.89
config.js                        | 100.00 |   100.00 |  100.00
estimateController.js            | 100.00 |   100.00 |  100.00
layerController.js               | 100.00 |   100.00 |  100.00
mapSelectionController.js        | 100.00 |   100.00 |  100.00
propertyDetailController.js      | 100.00 |   100.00 |  100.00
searchController.js              | 100.00 |   100.00 |  100.00
warningController.js             | 100.00 |   100.00 |  100.00
mapAdapter.js                    | 100.00 |   100.00 |  100.00
apiClient.js                     | 100.00 |   100.00 |  100.00
store.js                         | 100.00 |   100.00 |  100.00
debounce.js                      | 100.00 |   100.00 |  100.00
dom.js                           | 100.00 |   100.00 |  100.00
--------------------------------------------------------------
all files                        | 100.00 |   100.00 |   99.50
```

## Notes

- The `100%` line and branch result was verified with the current `19/19` passing frontend automated suite.
- `src/frontend/src/services/api/mockData.js` is excluded from the coverage command on purpose; it is fixture-heavy mock support, not the maintained application logic.
- Acceptance-flow traceability for the frontend-owned scope is documented separately in [`Final Submissions/frontend-test-report.md`](/root/Speckit-Constitution-To-Tasks/Final%20Submissions/frontend-test-report.md).
