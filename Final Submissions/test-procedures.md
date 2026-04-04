# Frontend Test Procedures

## Objective

Validate the frontend implementation through automated testing and documented acceptance-flow analysis, with the required submission targets:
- unit + integration tests must pass,
- frontend branch coverage must reach `100%`,
- acceptance tests must cover all documented frontend user-story flows in scope.

## Environment Used

- OS/runtime: Linux environment in Codex shell
- Node.js: `v24.11.1`
- Coverage tool: Node built-in coverage via `--experimental-test-coverage`
- Test runner: Node built-in `node --test`
- Frontend source under test: `src/frontend/src`

## Procedure Followed

1. Run the frontend automated test gate:
   - `npm run test:frontend`
2. Run the frontend coverage gate:
   - `npm run test:frontend:coverage`
3. If any test fails or branch coverage drops below `100%`:
   - inspect uncovered files/lines from the coverage report,
   - add or fix frontend unit/integration tests,
   - harden affected UI/controller paths,
   - rerun the coverage command.
4. Repeat until:
   - all frontend tests pass,
   - branch coverage is `100%`.
5. Perform manual acceptance-flow traceability analysis against the frontend-owned acceptance test markdown files and record the mapping in the submission report.

## Commands Executed

```bash
npm run test:frontend
npm run test:frontend:coverage
```

## Codex Prompt/Execution Context

Test and coverage runs were executed from Codex shell using direct commands, including:
- "Run `npm run test:frontend` and report pass/fail."
- "Run `npm run test:frontend:coverage` and provide the coverage summary."
- "After merge changes, rerun coverage until branch coverage reaches 100% again."

## Elevated Permission Note

- No elevated permission was required for the frontend test and coverage commands themselves.
- Git sync/push steps were handled separately and are not required to reproduce the test results.
- Equivalent alternative: run the same commands locally outside Codex and capture the outputs directly.

## Completion Criteria

Submission-ready when all are true:
- `npm run test:frontend` returns exit code `0`.
- `npm run test:frontend:coverage` returns exit code `0`.
- Coverage output shows `100%` global branch coverage for the included frontend files.
- Documented frontend acceptance flows are all covered in the submission traceability report.

## Coverage Claim Clarification

- This submission claims `100% branch coverage` for the included frontend source under the provided coverage command.
- It also claims `100% acceptance-flow coverage` for the documented frontend user stories in scope.
- It does not claim exhaustive real-world flow coverage across all future backend responses, browser engines, or external dependency behavior.

## Additional Verification Applied In Final Run

- Revalidated the full frontend suite after merging the newest `origin/master` changes into `merge-harrison`.
- Re-hardened the env-driven API fallback logic in `src/frontend/src/services/api/apiClient.js` so the final measured branch coverage returned to `100%`.
- Verified the final report numbers against the latest successful run, not an earlier pre-merge draft.
