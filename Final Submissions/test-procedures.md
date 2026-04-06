# Frontend Test Procedures

## Objective

Reproduce the current frontend automated test and coverage results for the MapLibre-based Edmonton property explorer frontend.

The frontend test deliverable is evaluated using:
- `npm run test:frontend`
- `npm run test:frontend:coverage`

## Environment

- OS/runtime: Linux shell environment
- Node.js: `v24.11.1`
- Test runner: built-in `node --test`
- Coverage tool: built-in Node coverage via `--experimental-test-coverage`
- Frontend source under test: `src/frontend/src`

## Setup

From the repository root:

```bash
cd /root/Speckit-Constitution-To-Tasks
npm install
```

## Commands

Run the frontend automated suite:

```bash
npm run test:frontend
```

Run the frontend coverage suite:

```bash
npm run test:frontend:coverage
```

## Expected Current Outcome

Latest verified results at the time this document was updated:

- `npm run test:frontend`: passes
- `npm run test:frontend:coverage`: passes
- automated suite count: `15/15` passing
- measured global coverage:
  - lines: `100.00%`
  - branches: `100.00%`
  - functions: `97.97%`

## Reproduction Notes

- Run both commands from the repository root.
- The coverage command excludes `src/frontend/src/services/api/mockData.js`.
- The frontend tests use the repo’s local fake DOM and fake MapLibre helpers, so no browser or live backend process is required to reproduce the automated suite.

## Acceptance-Flow Verification

Acceptance-flow coverage for the frontend-owned scope should be checked against:

- [`Final Submissions/frontend-test-report.md`](/root/Speckit-Constitution-To-Tasks/Final%20Submissions/frontend-test-report.md)

That report maps the submitted automated tests to the frontend user-story flows in scope.

## Important Status Clarification

The current automated suite is green, and the included frontend source set reaches both `100.00%` line coverage and `100.00%` branch coverage in the latest verified run.
