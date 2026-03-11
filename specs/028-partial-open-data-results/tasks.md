# Tasks: Provide Partial Results When Some Open Data is Unavailable

**Input**: Design documents from `/specs/028-partial-open-data-results/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend/frontend feature skeletons for `backend/src/api/partial_open_data_results.py`, `frontend/src/components/partial_open_data_results.js`, `frontend/src/pages/partial-open-data-results.html`, and test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add frontend test bootstrap and DOM helpers in `frontend/tests/test-setup.js` (depends on T001)
- [ ] T004 [P] [Setup] Create shared page shell and base styles in `frontend/src/pages/partial-open-data-results.html` and `frontend/src/styles/base.css` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define shared backend request/response models in `backend/src/models/partial_open_data_results.py` and `backend/src/models/partial_open_data_results.py` (depends on T001)
- [ ] T006 [P] [Foundation] Implement shared backend service interfaces in `backend/src/services/partial_open_data_results.py` and `backend/src/services/partial_open_data_results_support.py` (depends on T001, informed by T005)
- [ ] T007 [Foundation] Create API request parsing and common response serialization in `backend/src/api/partial_open_data_results.py` (depends on T005, T006)
- [ ] T008 [P] [Foundation] Add reusable frontend API-client scaffolding in `frontend/src/services/partial_open_data_results.js` (depends on T001, informed by T007)
- [ ] T009 [P] [Foundation] Build shared page-shell, render regions, and styles in `frontend/src/pages/partial-open-data-results.html` and `frontend/src/styles/base.css` (depends on T001)
- [ ] T010 [Foundation] Add reusable backend/frontend mock responses for success, validation, degraded, and failure states in `backend/tests/conftest.py` and `frontend/tests/test-setup.js` (depends on T002, T003)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - Get a usable estimate with partial open-data coverage (Priority: P1)

**Goal**: Get a usable estimate with partial open-data coverage

**Independent Test**: Can be fully tested by requesting estimates with one optional dataset unavailable and verifying that the API returns a successful partial result with estimate values, confidence, completeness, missing-factor details, warnings, and factor breakdown.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T011 [P] [US1] Add contract test coverage for get a usable estimate with partial open-data coverage in `backend/tests/contract/test_partial_open_data_results_us1_contract.py` (depends on T008)
- [ ] T012 [P] [US1] Add backend integration coverage for get a usable estimate with partial open-data coverage in `backend/tests/integration/test_partial_open_data_results_us1.py` (depends on T009)
- [ ] T013 [P] [US1] Add backend unit coverage for shared logic used by get a usable estimate with partial open-data coverage in `backend/tests/unit/test_partial_open_data_results_us1.py` (depends on T006)
- [ ] T014 [P] [US1] Add frontend integration coverage for get a usable estimate with partial open-data coverage in `frontend/tests/integration/test_partial_open_data_results_us1.js` (depends on T003)
- [ ] T015 [P] [US1] Add frontend unit coverage for UI logic used by get a usable estimate with partial open-data coverage in `frontend/tests/unit/test_partial_open_data_results_us1.js` (depends on T003)

### Implementation for User Story 1

- [ ] T016 [US1] Extend backend request/response models for get a usable estimate with partial open-data coverage in `backend/src/models/partial_open_data_results.py` and `backend/src/models/partial_open_data_results.py` (depends on T005, T011)
- [ ] T017 [P] [US1] Implement backend service logic for get a usable estimate with partial open-data coverage in `backend/src/services/partial_open_data_results.py` and `backend/src/services/partial_open_data_results_support.py` (depends on T006, T012)
- [ ] T018 [US1] Wire API orchestration and response handling for get a usable estimate with partial open-data coverage in `backend/src/api/partial_open_data_results.py` (depends on T016, T017)
- [ ] T019 [P] [US1] Implement or extend frontend component behavior for get a usable estimate with partial open-data coverage in `frontend/src/components/partial_open_data_results.js` and `frontend/src/components/partial_open_data_results_panel.js` (depends on T009, T014)
- [ ] T020 [P] [US1] Update frontend service mappings for get a usable estimate with partial open-data coverage in `frontend/src/services/partial_open_data_results.js` (depends on T018)
- [ ] T021 [US1] Wire page-level rendering, recovery, and state transitions for get a usable estimate with partial open-data coverage in `frontend/src/pages/partial-open-data-results.html` (depends on T019, T020)
- [ ] T022 [US1] Align shared styling, labels, and warning states for get a usable estimate with partial open-data coverage in `frontend/src/styles/base.css` (depends on T021)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Continue with reduced reliability when key supporting datasets are missing (Priority: P2)

**Goal**: Continue with reduced reliability when key supporting datasets are missing

**Independent Test**: Can be tested by disabling comparables or multiple datasets and by simulating timeouts, then verifying low-confidence or low-reliability responses, omission of unavailable factors, timeout handling, and completed requests.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T023 [P] [US2] Add contract test coverage for continue with reduced reliability when key supporting datasets are missing in `backend/tests/contract/test_partial_open_data_results_us2_contract.py` (depends on T008; user-story dependency: extends US1)
- [ ] T024 [P] [US2] Add backend integration coverage for continue with reduced reliability when key supporting datasets are missing in `backend/tests/integration/test_partial_open_data_results_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T025 [P] [US2] Add backend unit coverage for shared logic used by continue with reduced reliability when key supporting datasets are missing in `backend/tests/unit/test_partial_open_data_results_us2.py` (depends on T006; user-story dependency: extends US1)
- [ ] T026 [P] [US2] Add frontend integration coverage for continue with reduced reliability when key supporting datasets are missing in `frontend/tests/integration/test_partial_open_data_results_us2.js` (depends on T003; user-story dependency: extends US1)
- [ ] T027 [P] [US2] Add frontend unit coverage for UI logic used by continue with reduced reliability when key supporting datasets are missing in `frontend/tests/unit/test_partial_open_data_results_us2.js` (depends on T003; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T028 [US2] Extend backend request/response models for continue with reduced reliability when key supporting datasets are missing in `backend/src/models/partial_open_data_results.py` and `backend/src/models/partial_open_data_results.py` (depends on T005, T023)
- [ ] T029 [P] [US2] Implement backend service logic for continue with reduced reliability when key supporting datasets are missing in `backend/src/services/partial_open_data_results.py` and `backend/src/services/partial_open_data_results_support.py` (depends on T006, T024)
- [ ] T030 [US2] Wire API orchestration and response handling for continue with reduced reliability when key supporting datasets are missing in `backend/src/api/partial_open_data_results.py` (depends on T028, T029)
- [ ] T031 [P] [US2] Implement or extend frontend component behavior for continue with reduced reliability when key supporting datasets are missing in `frontend/src/components/partial_open_data_results.js` and `frontend/src/components/partial_open_data_results_panel.js` (depends on T009, T026)
- [ ] T032 [P] [US2] Update frontend service mappings for continue with reduced reliability when key supporting datasets are missing in `frontend/src/services/partial_open_data_results.js` (depends on T030)
- [ ] T033 [US2] Wire page-level rendering, recovery, and state transitions for continue with reduced reliability when key supporting datasets are missing in `frontend/src/pages/partial-open-data-results.html` (depends on T031, T032)
- [ ] T034 [US2] Align shared styling, labels, and warning states for continue with reduced reliability when key supporting datasets are missing in `frontend/src/styles/base.css` (depends on T033)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Fail explicitly when a required condition prevents a partial estimate (Priority: P3)

**Goal**: Fail explicitly when a required condition prevents a partial estimate

**Independent Test**: Can be tested by removing the baseline or requesting strict mode with a required missing factor, then verifying an error response that identifies the blocking condition.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T035 [P] [US3] Add contract test coverage for fail explicitly when a required condition prevents a partial estimate in `backend/tests/contract/test_partial_open_data_results_us3_contract.py` (depends on T008; user-story dependency: extends US2)
- [ ] T036 [P] [US3] Add backend integration coverage for fail explicitly when a required condition prevents a partial estimate in `backend/tests/integration/test_partial_open_data_results_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T037 [P] [US3] Add backend unit coverage for shared logic used by fail explicitly when a required condition prevents a partial estimate in `backend/tests/unit/test_partial_open_data_results_us3.py` (depends on T006; user-story dependency: extends US2)
- [ ] T038 [P] [US3] Add frontend integration coverage for fail explicitly when a required condition prevents a partial estimate in `frontend/tests/integration/test_partial_open_data_results_us3.js` (depends on T003; user-story dependency: extends US2)
- [ ] T039 [P] [US3] Add frontend unit coverage for UI logic used by fail explicitly when a required condition prevents a partial estimate in `frontend/tests/unit/test_partial_open_data_results_us3.js` (depends on T003; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T040 [US3] Extend backend request/response models for fail explicitly when a required condition prevents a partial estimate in `backend/src/models/partial_open_data_results.py` and `backend/src/models/partial_open_data_results.py` (depends on T005, T035)
- [ ] T041 [P] [US3] Implement backend service logic for fail explicitly when a required condition prevents a partial estimate in `backend/src/services/partial_open_data_results.py` and `backend/src/services/partial_open_data_results_support.py` (depends on T006, T036)
- [ ] T042 [US3] Wire API orchestration and response handling for fail explicitly when a required condition prevents a partial estimate in `backend/src/api/partial_open_data_results.py` (depends on T040, T041)
- [ ] T043 [P] [US3] Implement or extend frontend component behavior for fail explicitly when a required condition prevents a partial estimate in `frontend/src/components/partial_open_data_results.js` and `frontend/src/components/partial_open_data_results_panel.js` (depends on T009, T038)
- [ ] T044 [P] [US3] Update frontend service mappings for fail explicitly when a required condition prevents a partial estimate in `frontend/src/services/partial_open_data_results.js` (depends on T042)
- [ ] T045 [US3] Wire page-level rendering, recovery, and state transitions for fail explicitly when a required condition prevents a partial estimate in `frontend/src/pages/partial-open-data-results.html` (depends on T043, T044)
- [ ] T046 [US3] Align shared styling, labels, and warning states for fail explicitly when a required condition prevents a partial estimate in `frontend/src/styles/base.css` (depends on T045)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T047 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/028-partial-open-data-results/tasks.md` (depends on T022, T034, T046)
- [ ] T048 [P] [Polish] Apply final accessibility, copy, and warning-state refinements in `frontend/src/styles/base.css`, `frontend/src/components/partial_open_data_results.js`, and `frontend/src/pages/partial-open-data-results.html` (depends on T047)
- [ ] T049 [Polish] Verify quickstart steps and update feature execution notes in `specs/028-partial-open-data-results/quickstart.md` (depends on T048)
- [ ] T050 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/028-partial-open-data-results/tasks.md` (depends on T049)

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

- `specs/028-partial-open-data-results/` depends on `specs/023-property-estimate-api/` when integrating the shared platform because Partial-result behavior is exposed through the estimate API success and error contracts.
- `specs/028-partial-open-data-results/` depends on `specs/017-geospatial-ingest/` when integrating the shared platform because Open-data availability for spatial factors depends on geospatial ingest outputs.
- `specs/028-partial-open-data-results/` depends on `specs/018-census-ingest/` when integrating the shared platform because Neighbourhood or census indicators can participate in partial-data estimation.
- `specs/028-partial-open-data-results/` depends on `specs/020-standardize-poi-categories/` when integrating the shared platform because POI-derived factors may be omitted with warnings when standardized POI data is unavailable.

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
3. Complete Phase 3: US1 - Get a usable estimate with partial open-data coverage
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
