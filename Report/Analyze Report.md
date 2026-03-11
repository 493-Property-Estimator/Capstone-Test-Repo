# Task Analysis Report

**Report purpose**: Validate generated `tasks.md` artifacts against the corresponding `spec.md`, `plan.md`, declared source structure, and the project constitution before implementation begins.

**Report scope**:
- `specs/*/spec.md`
- `specs/*/plan.md`
- `specs/*/tasks.md`
- `.specify/memory/constitution.md`

**Analysis date**: 2026-03-11  
**Validation mode**: Read-only analysis followed by targeted remediation of planning inconsistencies and ambiguity reduction  
**Primary focus**:
- consistency between `plan.md` source trees and `tasks.md` file references
- coverage sanity across stories, requirements, and task breakdowns
- constitution-level alignment for testing, UX, and performance expectations
- remaining ambiguity likely to create churn during implementation

---

## Executive Summary

Validation was performed across all 32 generated feature task files. The portfolio is now structurally consistent and implementation-ready at the planning level.

Two classes of issues were identified during analysis:

1. concrete plan/task drift in 9 features, where `tasks.md` omitted one or more concrete source files explicitly named in `plan.md`
2. naming ambiguity in 17 features, where `plan.md` defined only directories and left filenames implicit

Both issue classes have now been resolved.

After remediation:

- every feature folder contains a `tasks.md`
- every feature plan includes concrete source filenames rather than directory-only placeholders
- every concrete file declared in each `plan.md` is referenced in the corresponding `tasks.md`
- no extra implementation file references remain in `tasks.md` that fall outside the declared plan source tree
- no directory-only source-tree cases remain in the analyzed plans

Current conclusion: the task portfolio is planning-complete, internally consistent, and suitable to begin implementation without the previously documented filename uncertainty.

---

## Analysis Method

### Inputs loaded

- Every feature `spec.md` was checked for user stories and functional requirements.
- Every feature `plan.md` was checked for declared source structure and implementation shape.
- Every feature `tasks.md` was checked for:
  - phase grouping
  - task count
  - explicit file references
  - dependency wording
  - user story sequencing
- The constitution was checked for compliance against:
  - code quality expectations
  - mandatory testing expectations
  - UX consistency expectations
  - performance requirements

### Validation passes performed

1. Presence and completeness pass
   - Verified `tasks.md` exists in all `specs/*` folders.
   - Verified each feature still has three user stories reflected in task phases.

2. Structural consistency pass
   - Parsed each `plan.md` source-tree section.
   - Compared concrete filenames declared in plans with concrete filenames referenced in tasks.
   - Identified both missing plan-declared files and extra task references not represented in plans.

3. Coverage sanity pass
   - Counted requirements, stories, and tasks across the feature set.
   - Verified the portfolio shape was proportionate rather than obviously under-generated.

4. Constitution alignment pass
   - Checked for missing test phases, missing UX-related tasks in UI-bearing features, and obvious task-level contradictions with performance expectations.

5. Remediation pass
   - Updated task files where plan-declared concrete files were absent.
   - Normalized directory-only plan source trees to explicit concrete filenames.
   - Corrected reverse drift where some plans used filenames that no longer matched the generated tasks.

6. Final verification pass
   - Re-ran repository-wide plan/task consistency checks after all edits.
   - Confirmed no remaining concrete path mismatches.
   - Confirmed no remaining directory-only source-tree ambiguity.

### Validation commands and checks

The final repository-wide validation checked three conditions for every feature:

- `MISSING`: concrete files declared in `plan.md` but not referenced in `tasks.md`
- `EXTRA`: implementation file references in `tasks.md` that were not declared in `plan.md`
- `INFERRED`: plans whose source-tree sections remained directory-only without concrete filenames

Final result:

```text
MISSING: OK
EXTRA: OK
INFERRED: []
```

### Limitations

- This report validates planning artifacts, not implementation correctness.
- Requirement-to-task mapping was validated structurally and heuristically, not by exhaustive semantic line-by-line traceability for all 647 requirements.
- No runtime tests, linters, or application commands were executed as part of this report.

---

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation | Status |
|----|----------|----------|-------------|---------|----------------|--------|
| I1 | Inconsistency | HIGH | `specs/001-user-geocode/tasks.md`, `specs/002-user-coords/tasks.md`, `specs/003-user-map/tasks.md`, `specs/004-input-location/tasks.md`, `specs/005-value-location/tasks.md`, `specs/006-property-details-estimate/tasks.md`, `specs/013-single-value-estimate/tasks.md`, `specs/014-low-high-range/tasks.md`, `specs/015-top-contributing-factors/tasks.md` | Generated task files omitted one or more concrete source files that were explicitly declared in the matching `plan.md` source tree. This weakened traceability and created avoidable drift between plan and task artifacts. | Update the affected task files so all plan-declared concrete files are represented in setup, foundational, or story implementation tasks. | Resolved |
| A1 | Ambiguity | MEDIUM | `specs/016-assessment-baseline/plan.md`, `specs/017-geospatial-ingest/plan.md`, `specs/018-census-ingest/plan.md`, `specs/019-ingest-tax-assessments/plan.md`, `specs/020-standardize-poi-categories/plan.md`, `specs/021-deduplicate-open-data/plan.md`, `specs/022-schedule-refresh-jobs/plan.md`, `specs/023-property-estimate-api/plan.md`, `specs/024-address-map-search/plan.md`, `specs/025-open-data-layers/plan.md`, `specs/026-missing-data-warnings/plan.md`, `specs/027-straight-line-fallback/plan.md`, `specs/028-partial-open-data-results/plan.md`, `specs/029-cache-computations/plan.md`, `specs/030-precompute-grid-features/plan.md`, `specs/031-health-service-metrics/plan.md`, `specs/032-invalid-input-errors/plan.md` | These plans originally defined directories but not concrete filenames, leaving task file paths inferred rather than explicit. | Normalize the source-tree blocks to concrete filenames and revalidate against `tasks.md`. | Resolved |
| I2 | Reverse Drift | MEDIUM | `specs/007-amenity-proximity/plan.md`, `specs/008-travel-accessibility/plan.md`, `specs/009-green-space-coverage/plan.md`, `specs/010-school-distance-signals/plan.md`, `specs/011-commute-accessibility/plan.md`, `specs/012-neighbourhood-indicators/plan.md`, `specs/014-low-high-range/plan.md`, `specs/015-top-contributing-factors/plan.md` | Several plans used concrete filenames that no longer matched the generated task references, creating plan/task naming divergence even though task files were internally coherent. | Update the plans so their declared filenames match the established task implementation surface, then rerun validation. | Resolved |

---

## Finding Details

### I1: Plan/Task Concrete Path Drift

This was the most serious issue found in the initial analysis set.

#### Why it mattered

- a developer could follow `tasks.md` and still miss implementing a file the plan claimed was part of the feature
- traceability from plan to task execution was weakened
- future audits would not be able to distinguish accidental omission from deliberate scope change

#### Features affected before remediation

- `001-user-geocode`
- `002-user-coords`
- `003-user-map`
- `004-input-location`
- `005-value-location`
- `006-property-details-estimate`
- `013-single-value-estimate`
- `014-low-high-range`
- `015-top-contributing-factors`

#### Examples of missing plan-declared files before remediation

- `specs/001-user-geocode/`
  - `backend/src/services/validation.py`
  - `backend/src/services/valuation.py`
  - `frontend/src/components/results-panel.js`
- `specs/002-user-coords/`
  - `backend/src/services/parcel_snap.py`
  - `backend/src/services/valuation.py`
  - `backend/src/services/validation.py`
- `specs/003-user-map/`
  - `backend/src/services/parcel_snap.py`
  - `backend/src/services/valuation.py`
  - `backend/src/services/validation.py`
  - `frontend/src/components/results-popover.js`
- `specs/004-input-location/`
  - `backend/src/models/location.py`
  - `backend/src/services/id_generation.py`
  - `backend/src/services/normalization.py`
- `specs/005-value-location/`
  - `backend/src/services/fallback.py`
  - `backend/src/services/ranges.py`
- `specs/006-property-details-estimate/`
  - `backend/src/services/validation.py`
  - `backend/src/services/ranges.py`
- `specs/013-single-value-estimate/`
  - `backend/src/services/formatting.py`
- `specs/014-low-high-range/`
  - `backend/src/models/estimate.py`
  - `backend/src/services/uncertainty.py`
  - `backend/src/services/formatting.py`
- `specs/015-top-contributing-factors/`
  - `backend/src/models/explanation.py`
  - `backend/src/services/policy_filter.py`

#### Remediation applied

- updated each affected `tasks.md` so missing files appear in setup, foundation, or story execution tasks
- preserved the existing task structure and dependency ordering rather than regenerating the files from scratch
- removed small duplicate references where generated task text named the same concrete file more than once

#### Post-remediation result

This issue is closed. All concrete files declared in plans are now represented in their corresponding task files.

### A1: Directory-Only Plan Ambiguity

This was the largest remaining uncertainty after the first remediation pass and is now also closed.

#### What the issue looked like originally

Seventeen features had source-tree sections that only described directories, for example:

- `backend/src/api/`
- `backend/src/services/`
- `frontend/src/components/`

Those plans did not specify the concrete filenames expected under those directories. The generated task files therefore used inferred names derived from the feature slug and task context.

#### Why it mattered

- implementation naming could drift from task naming
- later validation runs could produce false positives once concrete file choices were made
- cross-feature consistency was harder to enforce because the plans did not define a canonical implementation surface

#### Features normalized

- `016-assessment-baseline`
- `017-geospatial-ingest`
- `018-census-ingest`
- `019-ingest-tax-assessments`
- `020-standardize-poi-categories`
- `021-deduplicate-open-data`
- `022-schedule-refresh-jobs`
- `023-property-estimate-api`
- `024-address-map-search`
- `025-open-data-layers`
- `026-missing-data-warnings`
- `027-straight-line-fallback`
- `028-partial-open-data-results`
- `029-cache-computations`
- `030-precompute-grid-features`
- `031-health-service-metrics`
- `032-invalid-input-errors`

#### Remediation applied

- replaced directory-only source-tree sections with explicit concrete filenames
- aligned filenames with the already-generated tasks where task wording had established a plausible implementation surface
- preserved the feature intent and module boundaries implied by each plan

#### Post-remediation result

This issue is closed. No directory-only source-tree ambiguity remains in the analyzed plans.

### I2: Reverse Plan/Task Naming Drift

While closing the directory-only ambiguity, a second consistency issue became visible in several older concrete plans.

#### What changed

Some plans already had concrete filenames, but those filenames no longer matched the task files. The task files were more internally consistent, so the plans were updated to match them.

#### Features corrected

- `007-amenity-proximity`
- `008-travel-accessibility`
- `009-green-space-coverage`
- `010-school-distance-signals`
- `011-commute-accessibility`
- `012-neighbourhood-indicators`
- `014-low-high-range`
- `015-top-contributing-factors`

#### Representative corrections

- `008-travel-accessibility`
  - `backend/src/services/weighting.py` -> `backend/src/services/aggregation.py`
- `009-green-space-coverage`
  - `backend/src/services/green_space_coverage.py` -> `backend/src/services/green_space.py`
  - `backend/src/services/geometry.py` -> `backend/src/services/gis.py`
- `010-school-distance-signals`
  - `backend/src/services/school_distance_signals.py` -> `backend/src/services/school_distance.py`
  - `backend/src/services/distance.py` -> `backend/src/services/routing.py`
  - `backend/src/services/weighting.py` -> `backend/src/services/suitability.py`
- `012-neighbourhood-indicators`
  - `backend/src/services/neighbourhood_indicators.py` -> `backend/src/services/neighbourhood.py`
  - `backend/src/services/lookup.py` -> `backend/src/services/boundary_resolution.py`

#### Post-remediation result

This issue is closed. Plan filenames and task references now describe the same implementation surface for all analyzed features.

---

## Portfolio Metrics

### Aggregate Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Feature folders analyzed | 32 | Every feature folder under `specs/` with generated planning artifacts |
| User stories analyzed | 96 | Three user stories per feature across the full portfolio |
| Functional requirements analyzed | 647 | Counted from `FR-` entries in all `spec.md` files |
| Tasks analyzed | 1358 | Counted from checklist-style tasks across all `tasks.md` files |
| Average tasks per feature | 42.44 | `1358 / 32` |
| Average tasks per story portfolio-wide | 14.15 | Includes setup, foundation, and polish overhead distributed across stories |
| Features with path inconsistencies before remediation | 9 | Closed via task-file updates |
| Features with directory-only plan ambiguity before remediation | 17 | Closed via plan normalization |
| Features with reverse filename drift corrected | 8 | Closed via plan alignment edits |
| Plan-declared concrete file coverage | 100% | Every concrete file declared in a plan is referenced in its `tasks.md` |
| Remaining path mismatches | 0 | Final validation returned `MISSING: OK` and `EXTRA: OK` |
| Remaining inferred plan cases | 0 | Final validation returned `INFERRED: []` |
| Constitution-critical issues | 0 | No direct task-level violations found |

### Per-Feature Distribution

| Feature | FR Count | Story Count | Task Count |
|--------|---------:|------------:|-----------:|
| 001-user-geocode | 15 | 3 | 50 |
| 002-user-coords | 15 | 3 | 50 |
| 003-user-map | 15 | 3 | 50 |
| 004-input-location | 20 | 3 | 34 |
| 005-value-location | 20 | 3 | 50 |
| 006-property-details-estimate | 23 | 3 | 50 |
| 007-amenity-proximity | 22 | 3 | 34 |
| 008-travel-accessibility | 22 | 3 | 34 |
| 009-green-space-coverage | 19 | 3 | 34 |
| 010-school-distance-signals | 19 | 3 | 34 |
| 011-commute-accessibility | 19 | 3 | 34 |
| 012-neighbourhood-indicators | 20 | 3 | 34 |
| 013-single-value-estimate | 22 | 3 | 50 |
| 014-low-high-range | 16 | 3 | 43 |
| 015-top-contributing-factors | 20 | 3 | 43 |
| 016-assessment-baseline | 16 | 3 | 50 |
| 017-geospatial-ingest | 18 | 3 | 47 |
| 018-census-ingest | 23 | 3 | 47 |
| 019-ingest-tax-assessments | 18 | 3 | 47 |
| 020-standardize-poi-categories | 21 | 3 | 47 |
| 021-deduplicate-open-data | 21 | 3 | 50 |
| 022-schedule-refresh-jobs | 34 | 3 | 47 |
| 023-property-estimate-api | 36 | 3 | 50 |
| 024-address-map-search | 18 | 3 | 43 |
| 025-open-data-layers | 16 | 3 | 43 |
| 026-missing-data-warnings | 25 | 3 | 43 |
| 027-straight-line-fallback | 25 | 3 | 34 |
| 028-partial-open-data-results | 26 | 3 | 50 |
| 029-cache-computations | 16 | 3 | 34 |
| 030-precompute-grid-features | 15 | 3 | 34 |
| 031-health-service-metrics | 16 | 3 | 34 |
| 032-invalid-input-errors | 16 | 3 | 34 |

### Interpretation of the Distribution

- The 50-task features are mostly full UI+API workflows with explicit frontend and backend work.
- The 34-task features are mostly backend-only or narrower-support features where there is less UI surface area.
- The 43-task and 47-task features sit in the middle, reflecting partial UI or ingestion/operator-console overhead.
- Nothing in the current distribution suggests a failed generation run or a missing feature-level artifact.

---

## Constitution Alignment

### Summary Table

| Principle | Result | Notes |
|-----------|--------|-------|
| Code Quality First | Pass | Task sets consistently include setup, foundational structure, modular implementation work, and polish/refinement phases. |
| Testing Standards (NON-NEGOTIABLE) | Pass | Every feature includes explicit test tasks before implementation tasks at the story level. |
| UX Consistency | Pass | UI-bearing features include shared page/style/component work plus accessibility/copy refinement in polish phases. |
| Performance Requirements | Pass | No direct task conflict was found, and the previous filename ambiguity in performance-sensitive plans has been removed. |

### Detailed Constitution Notes

#### Code Quality First

Observed alignment:

- all task files follow a consistent phase model
- foundational work is separated from story work
- cross-cutting cleanup or observability work appears in polish phases
- task dependencies make execution order explicit rather than implied
- plan source trees now define a concrete implementation surface rather than leaving naming decisions open

Residual risk:

- this report confirms planning structure, not eventual code quality after implementation

#### Testing Standards

Observed alignment:

- story-level tests are listed before implementation tasks
- UI-bearing features include both backend and frontend test work where relevant
- backend-only features still include integration and unit test tasks
- ingestion and job features include failure-path validation in their testing phases

Residual risk:

- the report confirms task presence, not actual test completeness once implementation begins

#### UX Consistency

Observed alignment:

- UI-bearing features consistently reference shared pages, styles, and component work
- accessibility or copy refinement appears in polish sections
- error and warning rendering is treated as explicit work in relevant features

Residual risk:

- none specific at the planning-artifact level after filename normalization

#### Performance Requirements

Observed alignment:

- no task artifact directly conflicts with the constitution’s performance thresholds
- performance-sensitive features still include backend service structure and polish steps where optimization or observability can be inserted
- removing filename ambiguity reduces the chance of implementation churn in caching, API, ingest, and precomputation features

Residual risk:

- performance budgets are not yet represented as dedicated benchmark tasks in every performance-sensitive feature
- this is not a constitution violation at the planning level, but it should be watched during implementation

---

## Actions Taken

### Task-File Remediation Applied

The following task files were updated to include concrete source paths explicitly named by their plans:

- `specs/001-user-geocode/tasks.md`
- `specs/002-user-coords/tasks.md`
- `specs/003-user-map/tasks.md`
- `specs/004-input-location/tasks.md`
- `specs/005-value-location/tasks.md`
- `specs/006-property-details-estimate/tasks.md`
- `specs/013-single-value-estimate/tasks.md`
- `specs/014-low-high-range/tasks.md`
- `specs/015-top-contributing-factors/tasks.md`

What changed in those files:

- added missing backend service files to foundational task references where the plan explicitly named them
- added missing frontend component files where the plan explicitly named them
- added missing backend model references where the plan explicitly named them
- simplified a few duplicate model references where the generated task text repeated the same file twice

### Plan Normalization Applied

The following plans were converted from directory-only source trees to concrete file trees:

- `specs/016-assessment-baseline/plan.md`
- `specs/017-geospatial-ingest/plan.md`
- `specs/018-census-ingest/plan.md`
- `specs/019-ingest-tax-assessments/plan.md`
- `specs/020-standardize-poi-categories/plan.md`
- `specs/021-deduplicate-open-data/plan.md`
- `specs/022-schedule-refresh-jobs/plan.md`
- `specs/023-property-estimate-api/plan.md`
- `specs/024-address-map-search/plan.md`
- `specs/025-open-data-layers/plan.md`
- `specs/026-missing-data-warnings/plan.md`
- `specs/027-straight-line-fallback/plan.md`
- `specs/028-partial-open-data-results/plan.md`
- `specs/029-cache-computations/plan.md`
- `specs/030-precompute-grid-features/plan.md`
- `specs/031-health-service-metrics/plan.md`
- `specs/032-invalid-input-errors/plan.md`

### Reverse-Drift Plan Alignment Applied

The following plans were updated so their concrete filenames match the generated task references:

- `specs/007-amenity-proximity/plan.md`
- `specs/008-travel-accessibility/plan.md`
- `specs/009-green-space-coverage/plan.md`
- `specs/010-school-distance-signals/plan.md`
- `specs/011-commute-accessibility/plan.md`
- `specs/012-neighbourhood-indicators/plan.md`
- `specs/014-low-high-range/plan.md`
- `specs/015-top-contributing-factors/plan.md`

### Final Validation Result

After the fixes, a repository-wide comparison of:

- concrete files declared in each `plan.md`
- against concrete file references in the corresponding `tasks.md`
- plus a check for directory-only plan source trees

returned a clean result:

```text
MISSING: OK
EXTRA: OK
INFERRED: []
```

---

## Remaining Open Items

No blocking or medium-severity planning inconsistencies remain from the analyzed scope.

Non-blocking follow-up opportunities if stricter governance is desired:

- add explicit FR-to-task trace tables per feature
- add non-functional requirement coverage mapping
- add cross-feature dependency validation that checks task IDs against referenced prerequisite stories

These are enhancement opportunities for future reporting depth, not corrections required before implementation.

---

## Recommended Next Actions

### Immediate

- proceed with implementation using the current `tasks.md` and `plan.md` artifacts

### During Implementation

- preserve the normalized concrete filenames when creating source files unless there is an explicit scope change
- if a filename or module boundary changes, update both the feature `plan.md` and `tasks.md`, then append the change to this report

### For Future Planning Changes

Whenever any `tasks.md`, `plan.md`, or related planning artifact changes, append a dated note to this report with:

- the files changed
- the reason for the change
- whether the change resolved an existing finding or introduced a new one
- whether a validation rerun was performed

---

## Maintenance Log

### 2026-03-11

- Initial task-analysis report created.
- High-severity path inconsistency identified across 9 task files.
- Task-file remediation applied to all 9 affected features.
- Medium-severity ambiguity identified across 17 directory-only plans.
- Directory-only plans normalized to explicit concrete filenames across all 17 affected features.
- Reverse filename drift corrected across 8 additional plans whose concrete filenames no longer matched task references.
- Final repository-wide validation rerun completed with `MISSING: OK`, `EXTRA: OK`, and `INFERRED: []`.
- Report updated to reflect resolved-state metrics and implementation readiness.

---

## Final Assessment

The generated `tasks.md` portfolio is now materially cleaner than the initial bulk output. The original concrete plan/task drift is resolved. The later directory-only filename ambiguity is also resolved. All analyzed feature plans now define an explicit implementation surface, and all analyzed task files map to that surface without remaining path drift.

Overall planning status: **implementation-ready, structurally consistent, and free of the previously documented filename uncertainties**.
