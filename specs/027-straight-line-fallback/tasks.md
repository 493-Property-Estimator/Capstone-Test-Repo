# Tasks: Fall Back to Straight-Line Distance When Routing Fails

**Input**: Design documents from `/specs/027-straight-line-fallback/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend feature skeleton for `backend/src/api/straight_line_fallback.py`, `backend/src/models/straight_line_fallback.py`, `backend/src/services/straight_line_fallback.py`, and backend test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add shared backend assertion helpers in `backend/tests/support.py` (depends on T001)
- [ ] T004 [P] [Setup] Create shared constants/config helpers in `backend/src/services/straight_line_fallback.py` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define shared feature models and result envelopes in `backend/src/models/straight_line_fallback.py` (depends on T001)
- [ ] T006 [P] [Foundation] Implement shared computation and fallback interfaces in `backend/src/services/straight_line_fallback.py` and `backend/src/services/straight_line_fallback_support.py` (depends on T001, informed by T005)
- [ ] T007 [P] [Foundation] Create orchestration helpers or entrypoints in `backend/src/api/straight_line_fallback.py` when applicable and shared test fixtures in `backend/tests/conftest.py` (depends on T005, T006)
- [ ] T008 [P] [Foundation] Add deterministic formatting, weighting, or reporting helpers in `backend/src/services/straight_line_fallback_reporting.py` (depends on T001)
- [ ] T009 [Foundation] Add reusable success, fallback, and failure fixtures for backend tests in `backend/tests/conftest.py` and `backend/tests/support.py` (depends on T002, T003)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - Continue estimates during routing outages (Priority: P1)

**Goal**: Continue estimates during routing outages

**Independent Test**: Can be fully tested by simulating healthy routing and routing timeouts, then verifying road distance is preferred when available and straight-line fallback is used with a warning when routing fails.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T010 [P] [US1] Add backend contract-or-shape regression coverage for continue estimates during routing outages in `backend/tests/unit/test_straight_line_fallback_us1_contract_shape.py` (depends on T005)
- [ ] T011 [P] [US1] Add backend integration coverage for continue estimates during routing outages in `backend/tests/integration/test_straight_line_fallback_us1.py` (depends on T009)
- [ ] T012 [P] [US1] Add backend unit coverage for shared logic used by continue estimates during routing outages in `backend/tests/unit/test_straight_line_fallback_us1.py` (depends on T006)

### Implementation for User Story 1

- [ ] T013 [US1] Extend feature models or result envelopes for continue estimates during routing outages in `backend/src/models/straight_line_fallback.py` (depends on T005, T010)
- [ ] T014 [P] [US1] Implement primary computation behavior for continue estimates during routing outages in `backend/src/services/straight_line_fallback.py` and `backend/src/services/straight_line_fallback_support.py` (depends on T006, T011)
- [ ] T015 [P] [US1] Implement fallback, weighting, formatting, or deterministic-output behavior for continue estimates during routing outages in `backend/src/services/straight_line_fallback_reporting.py` (depends on T008, T012)
- [ ] T016 [US1] Wire orchestration or estimate-pipeline integration for continue estimates during routing outages in `backend/src/api/straight_line_fallback.py` when applicable, otherwise in `backend/src/services/straight_line_fallback.py` (depends on T014, T015)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Handle partial routing failures without stopping the estimate (Priority: P2)

**Goal**: Handle partial routing failures without stopping the estimate

**Independent Test**: Can be tested by requesting estimates with multiple targets, forcing partial routing failures, and verifying road distances are kept where available while straight-line fallback is used for failed targets.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T017 [P] [US2] Add backend contract-or-shape regression coverage for handle partial routing failures without stopping the estimate in `backend/tests/unit/test_straight_line_fallback_us2_contract_shape.py` (depends on T005; user-story dependency: extends US1)
- [ ] T018 [P] [US2] Add backend integration coverage for handle partial routing failures without stopping the estimate in `backend/tests/integration/test_straight_line_fallback_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T019 [P] [US2] Add backend unit coverage for shared logic used by handle partial routing failures without stopping the estimate in `backend/tests/unit/test_straight_line_fallback_us2.py` (depends on T006; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T020 [US2] Extend feature models or result envelopes for handle partial routing failures without stopping the estimate in `backend/src/models/straight_line_fallback.py` (depends on T005, T017)
- [ ] T021 [P] [US2] Implement primary computation behavior for handle partial routing failures without stopping the estimate in `backend/src/services/straight_line_fallback.py` and `backend/src/services/straight_line_fallback_support.py` (depends on T006, T018)
- [ ] T022 [P] [US2] Implement fallback, weighting, formatting, or deterministic-output behavior for handle partial routing failures without stopping the estimate in `backend/src/services/straight_line_fallback_reporting.py` (depends on T008, T019)
- [ ] T023 [US2] Wire orchestration or estimate-pipeline integration for handle partial routing failures without stopping the estimate in `backend/src/api/straight_line_fallback.py` when applicable, otherwise in `backend/src/services/straight_line_fallback.py` (depends on T021, T022)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Return controlled errors when fallback cannot be used (Priority: P3)

**Goal**: Return controlled errors when fallback cannot be used

**Independent Test**: Can be tested by disabling fallback or sending invalid coordinates during routing failure and verifying controlled error responses, no computed distances, and traceable request identifiers when applicable.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T024 [P] [US3] Add backend contract-or-shape regression coverage for return controlled errors when fallback cannot be used in `backend/tests/unit/test_straight_line_fallback_us3_contract_shape.py` (depends on T005; user-story dependency: extends US2)
- [ ] T025 [P] [US3] Add backend integration coverage for return controlled errors when fallback cannot be used in `backend/tests/integration/test_straight_line_fallback_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T026 [P] [US3] Add backend unit coverage for shared logic used by return controlled errors when fallback cannot be used in `backend/tests/unit/test_straight_line_fallback_us3.py` (depends on T006; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T027 [US3] Extend feature models or result envelopes for return controlled errors when fallback cannot be used in `backend/src/models/straight_line_fallback.py` (depends on T005, T024)
- [ ] T028 [P] [US3] Implement primary computation behavior for return controlled errors when fallback cannot be used in `backend/src/services/straight_line_fallback.py` and `backend/src/services/straight_line_fallback_support.py` (depends on T006, T025)
- [ ] T029 [P] [US3] Implement fallback, weighting, formatting, or deterministic-output behavior for return controlled errors when fallback cannot be used in `backend/src/services/straight_line_fallback_reporting.py` (depends on T008, T026)
- [ ] T030 [US3] Wire orchestration or estimate-pipeline integration for return controlled errors when fallback cannot be used in `backend/src/api/straight_line_fallback.py` when applicable, otherwise in `backend/src/services/straight_line_fallback.py` (depends on T028, T029)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T031 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/027-straight-line-fallback/tasks.md` (depends on T016, T023, T030)
- [ ] T032 [P] [Polish] Apply final observability, logging, and deterministic-output refinements in `backend/src/services/straight_line_fallback.py` and `backend/src/api/straight_line_fallback.py` when applicable (depends on T031)
- [ ] T033 [Polish] Verify quickstart steps and update feature execution notes in `specs/027-straight-line-fallback/quickstart.md` (depends on T032)
- [ ] T034 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/027-straight-line-fallback/tasks.md` (depends on T033)

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

- `specs/027-straight-line-fallback/` depends on `specs/008-travel-accessibility/` when integrating the shared platform because Straight-line fallback extends travel-distance computations when routing fails.
- `specs/027-straight-line-fallback/` depends on `specs/011-commute-accessibility/` when integrating the shared platform because Straight-line fallback also applies to commute-distance calculations.
- `specs/027-straight-line-fallback/` depends on `specs/023-property-estimate-api/` when integrating the shared platform because Fallback warnings and observability fields must integrate with the estimate API response.

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
3. Complete Phase 3: US1 - Continue estimates during routing outages
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
