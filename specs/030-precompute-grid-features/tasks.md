# Tasks: Precompute Grid-Level Features

**Input**: Design documents from `/specs/030-precompute-grid-features/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend feature skeleton for `backend/src/api/precompute_grid_features.py`, `backend/src/models/precompute_grid_features.py`, `backend/src/services/precompute_grid_features.py`, and backend test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add shared backend assertion helpers in `backend/tests/support.py` (depends on T001)
- [ ] T004 [P] [Setup] Create shared constants/config helpers in `backend/src/services/precompute_grid_features.py` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define aggregate-record, source-snapshot, and job-report models in `backend/src/models/precompute_grid_features.py` (depends on T001)
- [ ] T006 [P] [Foundation] Implement shared job orchestration and source-loading helpers in `backend/src/jobs/precompute_grid_features.py` and `backend/src/services/precompute_grid_features.py` (depends on T001, informed by T005)
- [ ] T007 [P] [Foundation] Add reusable sanity-check and rollback fixtures in `backend/tests/conftest.py` and `backend/tests/support.py` (depends on T002, T003)
- [ ] T008 [Foundation] Create shared persistence and reporting helpers in `backend/src/services/precompute_grid_features.py` (depends on T005, T006)
- [ ] T009 [P] [Foundation] Document shared job entrypoints and execution flags in `specs/030-precompute-grid-features/quickstart.md` (depends on T006)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - Run and Complete Precomputation Job (Priority: P1)

**Goal**: Run and Complete Precomputation Job

**Independent Test**: Can be fully tested by triggering the precompute job, waiting for completion, and verifying success reporting, persisted grid aggregates, and freshness metadata in the feature store.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T010 [P] [US1] Add backend contract-or-shape regression coverage for run and complete precomputation job in `backend/tests/unit/test_precompute_grid_features_us1_contract_shape.py` (depends on T005)
- [ ] T011 [P] [US1] Add backend integration coverage for run and complete precomputation job in `backend/tests/integration/test_precompute_grid_features_us1.py` (depends on T009)
- [ ] T012 [P] [US1] Add backend unit coverage for shared logic used by run and complete precomputation job in `backend/tests/unit/test_precompute_grid_features_us1.py` (depends on T006)

### Implementation for User Story 1

- [ ] T013 [US1] Implement aggregate/job record behavior for run and complete precomputation job in `backend/src/models/precompute_grid_features.py` (depends on T005, T010)
- [ ] T014 [P] [US1] Implement job orchestration and dataset loading for run and complete precomputation job in `backend/src/jobs/precompute_grid_features.py` (depends on T006, T011)
- [ ] T015 [P] [US1] Implement aggregate validation, outlier handling, or rollback behavior for run and complete precomputation job in `backend/src/services/precompute_grid_features.py` (depends on T008, T012)
- [ ] T016 [US1] Wire job success, warning, and failure reporting for run and complete precomputation job in `backend/src/jobs/precompute_grid_features.py` and `specs/030-precompute-grid-features/quickstart.md` (depends on T014, T015)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Aggregate and Validate Grid-Level Features (Priority: P2)

**Goal**: Aggregate and Validate Grid-Level Features

**Independent Test**: Can be fully tested by inspecting representative grid cells after a successful run and confirming the required aggregate fields are populated with plausible values and abnormal values are flagged or handled.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T017 [P] [US2] Add backend contract-or-shape regression coverage for aggregate and validate grid-level features in `backend/tests/unit/test_precompute_grid_features_us2_contract_shape.py` (depends on T005; user-story dependency: extends US1)
- [ ] T018 [P] [US2] Add backend integration coverage for aggregate and validate grid-level features in `backend/tests/integration/test_precompute_grid_features_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T019 [P] [US2] Add backend unit coverage for shared logic used by aggregate and validate grid-level features in `backend/tests/unit/test_precompute_grid_features_us2.py` (depends on T006; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T020 [US2] Implement aggregate/job record behavior for aggregate and validate grid-level features in `backend/src/models/precompute_grid_features.py` (depends on T005, T017)
- [ ] T021 [P] [US2] Implement job orchestration and dataset loading for aggregate and validate grid-level features in `backend/src/jobs/precompute_grid_features.py` (depends on T006, T018)
- [ ] T022 [P] [US2] Implement aggregate validation, outlier handling, or rollback behavior for aggregate and validate grid-level features in `backend/src/services/precompute_grid_features.py` (depends on T008, T019)
- [ ] T023 [US2] Wire job success, warning, and failure reporting for aggregate and validate grid-level features in `backend/src/jobs/precompute_grid_features.py` and `specs/030-precompute-grid-features/quickstart.md` (depends on T021, T022)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Fail Safely on Source or Write Problems (Priority: P3)

**Goal**: Fail Safely on Source or Write Problems

**Independent Test**: Can be fully tested by disabling a source dataset and by simulating a database write failure, then verifying warnings, fallback or skip behavior, retries, rollback, and final job outcome.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T024 [P] [US3] Add backend contract-or-shape regression coverage for fail safely on source or write problems in `backend/tests/unit/test_precompute_grid_features_us3_contract_shape.py` (depends on T005; user-story dependency: extends US2)
- [ ] T025 [P] [US3] Add backend integration coverage for fail safely on source or write problems in `backend/tests/integration/test_precompute_grid_features_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T026 [P] [US3] Add backend unit coverage for shared logic used by fail safely on source or write problems in `backend/tests/unit/test_precompute_grid_features_us3.py` (depends on T006; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T027 [US3] Implement aggregate/job record behavior for fail safely on source or write problems in `backend/src/models/precompute_grid_features.py` (depends on T005, T024)
- [ ] T028 [P] [US3] Implement job orchestration and dataset loading for fail safely on source or write problems in `backend/src/jobs/precompute_grid_features.py` (depends on T006, T025)
- [ ] T029 [P] [US3] Implement aggregate validation, outlier handling, or rollback behavior for fail safely on source or write problems in `backend/src/services/precompute_grid_features.py` (depends on T008, T026)
- [ ] T030 [US3] Wire job success, warning, and failure reporting for fail safely on source or write problems in `backend/src/jobs/precompute_grid_features.py` and `specs/030-precompute-grid-features/quickstart.md` (depends on T028, T029)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T031 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/030-precompute-grid-features/tasks.md` (depends on T016, T023, T030)
- [ ] T032 [P] [Polish] Apply final observability, logging, and deterministic-output refinements in `backend/src/services/precompute_grid_features.py` and `backend/src/api/precompute_grid_features.py` when applicable (depends on T031)
- [ ] T033 [Polish] Verify quickstart steps and update feature execution notes in `specs/030-precompute-grid-features/quickstart.md` (depends on T032)
- [ ] T034 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/030-precompute-grid-features/tasks.md` (depends on T033)

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup can start immediately
- Foundational work depends on Setup and blocks all user-story implementation
- User stories depend on the Foundational phase and then proceed in priority order unless multiple developers are available
- Polish depends on the user stories selected for delivery being complete

### User Story Dependencies

- **US1** can start as soon as Foundation is complete and establishes the core feature workflow
- **US2** depends on the shared contracts and state transitions established by **US1**, while remaining independently testable once implemented
- **US3** depends on the shared contracts and state transitions established by **US2**, while remaining independently testable once implemented

### Cross-Feature Dependencies

- `specs/030-precompute-grid-features/` depends on `specs/017-geospatial-ingest/` when integrating the shared platform because Grid aggregation depends on ingested geospatial source layers.
- `specs/030-precompute-grid-features/` depends on `specs/018-census-ingest/` when integrating the shared platform because Grid aggregation may incorporate published census indicators.
- `specs/030-precompute-grid-features/` depends on `specs/019-ingest-tax-assessments/` when integrating the shared platform because Grid aggregation uses assessment-derived comparable value inputs.
- `specs/030-precompute-grid-features/` depends on `specs/020-standardize-poi-categories/` when integrating the shared platform because Grid aggregation should consume standardized POI/store categories.
- `specs/030-precompute-grid-features/` depends on `specs/021-deduplicate-open-data/` when integrating the shared platform because Grid aggregation should consume deduplicated source records before writing aggregates.

### Within Each User Story

- Write the story tests first and confirm they fail before implementation work begins
- Complete model or contract updates before service orchestration
- Finish the story and run its scoped tests before moving to the next priority

### Parallel Opportunities

- Tasks marked `[P]` in Setup and Foundation can be split across backend, frontend, or data-pipeline owners
- Contract, integration, and unit tests for the same story can usually be authored in parallel once the shared fixtures exist
- Once Foundation is complete, separate developers can take different stories in parallel if they respect the explicit dependency notes on each task

---

## Implementation Strategy

### MVP First

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 - Run and Complete Precomputation Job
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
