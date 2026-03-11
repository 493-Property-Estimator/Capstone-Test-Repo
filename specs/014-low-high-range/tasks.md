# Tasks: Return a Low/High Range

**Input**: Design documents from `/specs/014-low-high-range/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend/frontend feature skeletons for `backend/src/api/low_high_range.py`, `backend/src/models/estimate.py`, `frontend/src/components/estimate-result.js`, `frontend/src/pages/estimate.html`, and test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add frontend test bootstrap and DOM helpers in `frontend/tests/test-setup.js` (depends on T001)
- [ ] T004 [P] [Setup] Create shared page shell and base styles in `frontend/src/pages/estimate.html` and `frontend/src/styles/base.css` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define shared client-side state, API payload adapters, and UI state models in `frontend/src/services/estimate-api.js` and `frontend/src/components/estimate-result.js` (depends on T001)
- [ ] T006 [P] [Foundation] Implement backend proxy/service contract in `backend/src/services/valuation.py`, `backend/src/services/uncertainty.py`, and `backend/src/services/formatting.py` (depends on T001, informed by T005)
- [ ] T007 [P] [Foundation] Build shared page shell, loading regions, and warning regions in `frontend/src/pages/estimate.html` and `frontend/src/styles/base.css` (depends on T001)
- [ ] T008 [Foundation] Add reusable frontend fixtures for success, warning, and failure states in `frontend/tests/test-setup.js` plus backend forwarding fixtures in `backend/tests/conftest.py` (depends on T002, T003)
- [ ] T009 [P] [Foundation] Create backend normalization or forwarding helpers in `backend/src/services/valuation.py` (depends on T001)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - View Estimate With Uncertainty Range (Priority: P1)

**Goal**: View Estimate With Uncertainty Range

**Independent Test**: Can be fully tested by requesting an estimate for a location where both point estimate and range are available and verifying the response fields, labels, metadata, and formatting.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T010 [P] [US1] Add backend contract-or-shape regression coverage for view estimate with uncertainty range in `backend/tests/unit/test_low_high_range_us1_contract_shape.py` (depends on T005)
- [ ] T011 [P] [US1] Add backend integration coverage for view estimate with uncertainty range in `backend/tests/integration/test_low_high_range_us1.py` (depends on T009)
- [ ] T012 [P] [US1] Add backend unit coverage for shared logic used by view estimate with uncertainty range in `backend/tests/unit/test_low_high_range_us1.py` (depends on T006)
- [ ] T013 [P] [US1] Add frontend integration coverage for view estimate with uncertainty range in `frontend/tests/integration/test_low_high_range_us1.js` (depends on T003)
- [ ] T014 [P] [US1] Add frontend unit coverage for UI logic used by view estimate with uncertainty range in `frontend/tests/unit/test_low_high_range_us1.js` (depends on T003)

### Implementation for User Story 1

- [ ] T015 [US1] Implement client-side state and request handling for view estimate with uncertainty range in `frontend/src/services/estimate-api.js` (depends on T005, T013)
- [ ] T016 [P] [US1] Implement primary UI components for view estimate with uncertainty range in `frontend/src/components/estimate-result.js` and `frontend/src/components/range-display.js` (depends on T007, T013)
- [ ] T017 [P] [US1] Implement backend proxy or forwarding behavior for view estimate with uncertainty range in `backend/src/services/valuation.py` (depends on T006, T011)
- [ ] T018 [US1] Wire page-level interactions, retry states, and selection handling for view estimate with uncertainty range in `frontend/src/pages/estimate.html` (depends on T015, T016, T017)
- [ ] T019 [US1] Align copy, warnings, and accessible styles for view estimate with uncertainty range in `frontend/src/styles/base.css` (depends on T018)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Keep the Point Estimate When Range Is Unavailable (Priority: P2)

**Goal**: Keep the Point Estimate When Range Is Unavailable

**Independent Test**: Can be tested by forcing insufficient-data and internal-error conditions during range computation and verifying that the point estimate remains available with appropriate warnings when configured.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T020 [P] [US2] Add backend contract-or-shape regression coverage for keep the point estimate when range is unavailable in `backend/tests/unit/test_low_high_range_us2_contract_shape.py` (depends on T005; user-story dependency: extends US1)
- [ ] T021 [P] [US2] Add backend integration coverage for keep the point estimate when range is unavailable in `backend/tests/integration/test_low_high_range_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T022 [P] [US2] Add backend unit coverage for shared logic used by keep the point estimate when range is unavailable in `backend/tests/unit/test_low_high_range_us2.py` (depends on T006; user-story dependency: extends US1)
- [ ] T023 [P] [US2] Add frontend integration coverage for keep the point estimate when range is unavailable in `frontend/tests/integration/test_low_high_range_us2.js` (depends on T003; user-story dependency: extends US1)
- [ ] T024 [P] [US2] Add frontend unit coverage for UI logic used by keep the point estimate when range is unavailable in `frontend/tests/unit/test_low_high_range_us2.js` (depends on T003; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T025 [US2] Implement client-side state and request handling for keep the point estimate when range is unavailable in `frontend/src/services/estimate-api.js` (depends on T005, T023)
- [ ] T026 [P] [US2] Implement primary UI components for keep the point estimate when range is unavailable in `frontend/src/components/estimate-result.js` and `frontend/src/components/range-display.js` (depends on T007, T023)
- [ ] T027 [P] [US2] Implement backend proxy or forwarding behavior for keep the point estimate when range is unavailable in `backend/src/services/valuation.py` (depends on T006, T021)
- [ ] T028 [US2] Wire page-level interactions, retry states, and selection handling for keep the point estimate when range is unavailable in `frontend/src/pages/estimate.html` (depends on T025, T026, T027)
- [ ] T029 [US2] Align copy, warnings, and accessible styles for keep the point estimate when range is unavailable in `frontend/src/styles/base.css` (depends on T028)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Keep Range Output Valid and Transparent (Priority: P3)

**Goal**: Keep Range Output Valid and Transparent

**Independent Test**: Can be tested by forcing invalid-range and partial-feature conditions, then repeating the same input under fixed versions to verify warnings, guardrails, and consistent outputs.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T030 [P] [US3] Add backend contract-or-shape regression coverage for keep range output valid and transparent in `backend/tests/unit/test_low_high_range_us3_contract_shape.py` (depends on T005; user-story dependency: extends US2)
- [ ] T031 [P] [US3] Add backend integration coverage for keep range output valid and transparent in `backend/tests/integration/test_low_high_range_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T032 [P] [US3] Add backend unit coverage for shared logic used by keep range output valid and transparent in `backend/tests/unit/test_low_high_range_us3.py` (depends on T006; user-story dependency: extends US2)
- [ ] T033 [P] [US3] Add frontend integration coverage for keep range output valid and transparent in `frontend/tests/integration/test_low_high_range_us3.js` (depends on T003; user-story dependency: extends US2)
- [ ] T034 [P] [US3] Add frontend unit coverage for UI logic used by keep range output valid and transparent in `frontend/tests/unit/test_low_high_range_us3.js` (depends on T003; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T035 [US3] Implement client-side state and request handling for keep range output valid and transparent in `frontend/src/services/estimate-api.js` (depends on T005, T033)
- [ ] T036 [P] [US3] Implement primary UI components for keep range output valid and transparent in `frontend/src/components/estimate-result.js` and `frontend/src/components/range-display.js` (depends on T007, T033)
- [ ] T037 [P] [US3] Implement backend proxy or forwarding behavior for keep range output valid and transparent in `backend/src/services/valuation.py` (depends on T006, T031)
- [ ] T038 [US3] Wire page-level interactions, retry states, and selection handling for keep range output valid and transparent in `frontend/src/pages/estimate.html` (depends on T035, T036, T037)
- [ ] T039 [US3] Align copy, warnings, and accessible styles for keep range output valid and transparent in `frontend/src/styles/base.css` (depends on T038)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T040 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/014-low-high-range/tasks.md` (depends on T019, T029, T039)
- [ ] T041 [P] [Polish] Apply final accessibility, copy, and warning-state refinements in `frontend/src/styles/base.css`, `frontend/src/components/estimate-result.js`, and `frontend/src/pages/estimate.html` (depends on T040)
- [ ] T042 [Polish] Verify quickstart steps and update feature execution notes in `specs/014-low-high-range/quickstart.md` (depends on T041)
- [ ] T043 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/014-low-high-range/tasks.md` (depends on T042)

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

- `specs/014-low-high-range/` depends on `specs/013-single-value-estimate/` when integrating the shared platform because The spec explicitly computes the uncertainty range only after the point estimate from UC-13 exists.

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
3. Complete Phase 3: US1 - View Estimate With Uncertainty Range
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
