# Tasks: Ingest open geospatial datasets

**Input**: Design documents from `/specs/017-geospatial-ingest/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend/frontend feature skeletons for `backend/src/api/geospatial_ingest.py`, `frontend/src/components/geospatial_ingest.js`, `frontend/src/pages/geospatial-ingest.html`, and test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add frontend test bootstrap and DOM helpers in `frontend/tests/test-setup.js` (depends on T001)
- [ ] T004 [P] [Setup] Create shared page shell and base styles in `frontend/src/pages/geospatial-ingest.html` and `frontend/src/styles/base.css` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define run-report, source-config, staging, and promotion models in `backend/src/models/geospatial_ingest.py` (depends on T001)
- [ ] T006 [P] [Foundation] Implement shared download/load orchestration boundaries in `backend/src/ingestion/geospatial_ingest_pipeline.py` and `backend/src/ingestion/geospatial_ingest_qa.py` (depends on T001, informed by T005)
- [ ] T007 [P] [Foundation] Implement common validation, QA, and failure-report helpers in `backend/src/services/geospatial_ingest.py` and `backend/src/services/geospatial_ingest_support.py` (depends on T001, informed by T005)
- [ ] T008 [Foundation] Create run-status API or operator-report serialization in `backend/src/api/geospatial_ingest.py` (depends on T005, T006, T007)
- [ ] T009 [P] [Foundation] Build operator UI shell or status view in `frontend/src/pages/geospatial-ingest.html` and `frontend/src/components/geospatial_ingest.js` (depends on T001, informed by T008)
- [ ] T010 [Foundation] Add reusable ingestion success/failure fixtures for backend and frontend tests in `backend/tests/conftest.py` and `frontend/tests/test-setup.js` (depends on T002, T003)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - Ingest validated geospatial data (Priority: P1)

**Goal**: Ingest validated geospatial data

**Independent Test**: Run ingestion against valid source artifacts and verify that production tables contain transformed datasets and that ingestion metadata is recorded.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T011 [P] [US1] Add contract test coverage for ingest validated geospatial data in `backend/tests/contract/test_geospatial_ingest_us1_contract.py` (depends on T008)
- [ ] T012 [P] [US1] Add backend integration coverage for ingest validated geospatial data in `backend/tests/integration/test_geospatial_ingest_us1.py` (depends on T009)
- [ ] T013 [P] [US1] Add backend unit coverage for shared logic used by ingest validated geospatial data in `backend/tests/unit/test_geospatial_ingest_us1.py` (depends on T006)
- [ ] T014 [P] [US1] Add frontend integration coverage for ingest validated geospatial data in `frontend/tests/integration/test_geospatial_ingest_us1.js` (depends on T003)
- [ ] T015 [P] [US1] Add frontend unit coverage for UI logic used by ingest validated geospatial data in `frontend/tests/unit/test_geospatial_ingest_us1.js` (depends on T003)

### Implementation for User Story 1

- [ ] T016 [US1] Implement run-model and report-field behavior for ingest validated geospatial data in `backend/src/models/geospatial_ingest.py` (depends on T005, T011)
- [ ] T017 [P] [US1] Implement ingestion/download/load orchestration for ingest validated geospatial data in `backend/src/ingestion/geospatial_ingest_pipeline.py` and `backend/src/ingestion/geospatial_ingest_qa.py` (depends on T006, T012)
- [ ] T018 [P] [US1] Implement validation, QA, or promotion behavior for ingest validated geospatial data in `backend/src/services/geospatial_ingest.py` and `backend/src/services/geospatial_ingest_support.py` (depends on T007, T013)
- [ ] T019 [US1] Expose run status, operator report, or re-run controls for ingest validated geospatial data in `backend/src/api/geospatial_ingest.py` (depends on T017, T018)
- [ ] T020 [P] [US1] Implement operator UI states for ingest validated geospatial data in `frontend/src/components/geospatial_ingest.js` and `frontend/src/pages/geospatial-ingest.html` (depends on T009, T014)
- [ ] T021 [US1] Align operator-side copy, alerts, and workflow status rendering for ingest validated geospatial data in `frontend/src/styles/base.css` and `frontend/src/services/geospatial_ingest.js` (depends on T019, T020)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Prevent bad data from replacing production (Priority: P2)

**Goal**: Prevent bad data from replacing production

**Independent Test**: Run ingestion against negative fixtures for download failure, schema change, invalid geometry, CRS mismatch, QA failure, and promotion failure, then verify that promotion is blocked and production remains unchanged.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T022 [P] [US2] Add contract test coverage for prevent bad data from replacing production in `backend/tests/contract/test_geospatial_ingest_us2_contract.py` (depends on T008; user-story dependency: extends US1)
- [ ] T023 [P] [US2] Add backend integration coverage for prevent bad data from replacing production in `backend/tests/integration/test_geospatial_ingest_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T024 [P] [US2] Add backend unit coverage for shared logic used by prevent bad data from replacing production in `backend/tests/unit/test_geospatial_ingest_us2.py` (depends on T006; user-story dependency: extends US1)
- [ ] T025 [P] [US2] Add frontend integration coverage for prevent bad data from replacing production in `frontend/tests/integration/test_geospatial_ingest_us2.js` (depends on T003; user-story dependency: extends US1)
- [ ] T026 [P] [US2] Add frontend unit coverage for UI logic used by prevent bad data from replacing production in `frontend/tests/unit/test_geospatial_ingest_us2.js` (depends on T003; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T027 [US2] Implement run-model and report-field behavior for prevent bad data from replacing production in `backend/src/models/geospatial_ingest.py` (depends on T005, T022)
- [ ] T028 [P] [US2] Implement ingestion/download/load orchestration for prevent bad data from replacing production in `backend/src/ingestion/geospatial_ingest_pipeline.py` and `backend/src/ingestion/geospatial_ingest_qa.py` (depends on T006, T023)
- [ ] T029 [P] [US2] Implement validation, QA, or promotion behavior for prevent bad data from replacing production in `backend/src/services/geospatial_ingest.py` and `backend/src/services/geospatial_ingest_support.py` (depends on T007, T024)
- [ ] T030 [US2] Expose run status, operator report, or re-run controls for prevent bad data from replacing production in `backend/src/api/geospatial_ingest.py` (depends on T028, T029)
- [ ] T031 [P] [US2] Implement operator UI states for prevent bad data from replacing production in `frontend/src/components/geospatial_ingest.js` and `frontend/src/pages/geospatial-ingest.html` (depends on T009, T025)
- [ ] T032 [US2] Align operator-side copy, alerts, and workflow status rendering for prevent bad data from replacing production in `frontend/src/styles/base.css` and `frontend/src/services/geospatial_ingest.js` (depends on T030, T031)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Trace and repeat ingestion runs (Priority: P3)

**Goal**: Trace and repeat ingestion runs

**Independent Test**: Execute repeated runs with unchanged inputs and verify distinct run IDs, stable dataset version metadata, and consistent counts within expected tolerances.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T033 [P] [US3] Add contract test coverage for trace and repeat ingestion runs in `backend/tests/contract/test_geospatial_ingest_us3_contract.py` (depends on T008; user-story dependency: extends US2)
- [ ] T034 [P] [US3] Add backend integration coverage for trace and repeat ingestion runs in `backend/tests/integration/test_geospatial_ingest_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T035 [P] [US3] Add backend unit coverage for shared logic used by trace and repeat ingestion runs in `backend/tests/unit/test_geospatial_ingest_us3.py` (depends on T006; user-story dependency: extends US2)
- [ ] T036 [P] [US3] Add frontend integration coverage for trace and repeat ingestion runs in `frontend/tests/integration/test_geospatial_ingest_us3.js` (depends on T003; user-story dependency: extends US2)
- [ ] T037 [P] [US3] Add frontend unit coverage for UI logic used by trace and repeat ingestion runs in `frontend/tests/unit/test_geospatial_ingest_us3.js` (depends on T003; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T038 [US3] Implement run-model and report-field behavior for trace and repeat ingestion runs in `backend/src/models/geospatial_ingest.py` (depends on T005, T033)
- [ ] T039 [P] [US3] Implement ingestion/download/load orchestration for trace and repeat ingestion runs in `backend/src/ingestion/geospatial_ingest_pipeline.py` and `backend/src/ingestion/geospatial_ingest_qa.py` (depends on T006, T034)
- [ ] T040 [P] [US3] Implement validation, QA, or promotion behavior for trace and repeat ingestion runs in `backend/src/services/geospatial_ingest.py` and `backend/src/services/geospatial_ingest_support.py` (depends on T007, T035)
- [ ] T041 [US3] Expose run status, operator report, or re-run controls for trace and repeat ingestion runs in `backend/src/api/geospatial_ingest.py` (depends on T039, T040)
- [ ] T042 [P] [US3] Implement operator UI states for trace and repeat ingestion runs in `frontend/src/components/geospatial_ingest.js` and `frontend/src/pages/geospatial-ingest.html` (depends on T009, T036)
- [ ] T043 [US3] Align operator-side copy, alerts, and workflow status rendering for trace and repeat ingestion runs in `frontend/src/styles/base.css` and `frontend/src/services/geospatial_ingest.js` (depends on T041, T042)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T044 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/017-geospatial-ingest/tasks.md` (depends on T021, T032, T043)
- [ ] T045 [P] [Polish] Apply final accessibility, copy, and warning-state refinements in `frontend/src/styles/base.css`, `frontend/src/components/geospatial_ingest.js`, and `frontend/src/pages/geospatial-ingest.html` (depends on T044)
- [ ] T046 [Polish] Verify quickstart steps and update feature execution notes in `specs/017-geospatial-ingest/quickstart.md` (depends on T045)
- [ ] T047 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/017-geospatial-ingest/tasks.md` (depends on T046)

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

- No explicit cross-feature implementation prerequisite is stated in the feature docs; keep this feature internally complete and integrate shared platform dependencies only when they are introduced elsewhere.

### Within Each User Story

- Write the story tests first and confirm they fail before implementation work begins
- Complete model or contract updates before service orchestration
- Complete backend or client contract work before wiring page-level UI behavior
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
3. Complete Phase 3: US1 - Ingest validated geospatial data
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
