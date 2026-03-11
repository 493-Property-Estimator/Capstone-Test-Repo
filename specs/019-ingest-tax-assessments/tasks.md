# Tasks: Ingest property tax assessment data

**Input**: Design documents from `/specs/019-ingest-tax-assessments/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend/frontend feature skeletons for `backend/src/api/ingest_tax_assessments.py`, `frontend/src/components/ingest_tax_assessments.js`, `frontend/src/pages/ingest-tax-assessments.html`, and test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add frontend test bootstrap and DOM helpers in `frontend/tests/test-setup.js` (depends on T001)
- [ ] T004 [P] [Setup] Create shared page shell and base styles in `frontend/src/pages/ingest-tax-assessments.html` and `frontend/src/styles/base.css` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define run-report, source-config, staging, and promotion models in `backend/src/models/ingest_tax_assessments.py` (depends on T001)
- [ ] T006 [P] [Foundation] Implement shared download/load orchestration boundaries in `backend/src/ingestion/ingest_tax_assessments_pipeline.py` and `backend/src/ingestion/ingest_tax_assessments_qa.py` (depends on T001, informed by T005)
- [ ] T007 [P] [Foundation] Implement common validation, QA, and failure-report helpers in `backend/src/services/ingest_tax_assessments.py` and `backend/src/services/ingest_tax_assessments_support.py` (depends on T001, informed by T005)
- [ ] T008 [Foundation] Create run-status API or operator-report serialization in `backend/src/api/ingest_tax_assessments.py` (depends on T005, T006, T007)
- [ ] T009 [P] [Foundation] Build operator UI shell or status view in `frontend/src/pages/ingest-tax-assessments.html` and `frontend/src/components/ingest_tax_assessments.js` (depends on T001, informed by T008)
- [ ] T010 [Foundation] Add reusable ingestion success/failure fixtures for backend and frontend tests in `backend/tests/conftest.py` and `frontend/tests/test-setup.js` (depends on T002, T003)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - Publish assessment baseline (Priority: P1)

**Goal**: Publish assessment baseline

**Independent Test**: Can be fully tested by running ingestion on a valid dataset and confirming the new baseline is queryable by canonical location ID with recorded run metadata.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T011 [P] [US1] Add contract test coverage for publish assessment baseline in `backend/tests/contract/test_ingest_tax_assessments_us1_contract.py` (depends on T008)
- [ ] T012 [P] [US1] Add backend integration coverage for publish assessment baseline in `backend/tests/integration/test_ingest_tax_assessments_us1.py` (depends on T009)
- [ ] T013 [P] [US1] Add backend unit coverage for shared logic used by publish assessment baseline in `backend/tests/unit/test_ingest_tax_assessments_us1.py` (depends on T006)
- [ ] T014 [P] [US1] Add frontend integration coverage for publish assessment baseline in `frontend/tests/integration/test_ingest_tax_assessments_us1.js` (depends on T003)
- [ ] T015 [P] [US1] Add frontend unit coverage for UI logic used by publish assessment baseline in `frontend/tests/unit/test_ingest_tax_assessments_us1.js` (depends on T003)

### Implementation for User Story 1

- [ ] T016 [US1] Implement run-model and report-field behavior for publish assessment baseline in `backend/src/models/ingest_tax_assessments.py` (depends on T005, T011)
- [ ] T017 [P] [US1] Implement ingestion/download/load orchestration for publish assessment baseline in `backend/src/ingestion/ingest_tax_assessments_pipeline.py` and `backend/src/ingestion/ingest_tax_assessments_qa.py` (depends on T006, T012)
- [ ] T018 [P] [US1] Implement validation, QA, or promotion behavior for publish assessment baseline in `backend/src/services/ingest_tax_assessments.py` and `backend/src/services/ingest_tax_assessments_support.py` (depends on T007, T013)
- [ ] T019 [US1] Expose run status, operator report, or re-run controls for publish assessment baseline in `backend/src/api/ingest_tax_assessments.py` (depends on T017, T018)
- [ ] T020 [P] [US1] Implement operator UI states for publish assessment baseline in `frontend/src/components/ingest_tax_assessments.js` and `frontend/src/pages/ingest-tax-assessments.html` (depends on T009, T014)
- [ ] T021 [US1] Align operator-side copy, alerts, and workflow status rendering for publish assessment baseline in `frontend/src/styles/base.css` and `frontend/src/services/ingest_tax_assessments.js` (depends on T019, T020)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Prevent unsafe publication (Priority: P1)

**Goal**: Prevent unsafe publication

**Independent Test**: Can be fully tested by running ingestion against invalid schema, invalid values, low-coverage data, extreme outliers, and forced promotion failures, then confirming production remains unchanged.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T022 [P] [US2] Add contract test coverage for prevent unsafe publication in `backend/tests/contract/test_ingest_tax_assessments_us2_contract.py` (depends on T008; user-story dependency: extends US1)
- [ ] T023 [P] [US2] Add backend integration coverage for prevent unsafe publication in `backend/tests/integration/test_ingest_tax_assessments_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T024 [P] [US2] Add backend unit coverage for shared logic used by prevent unsafe publication in `backend/tests/unit/test_ingest_tax_assessments_us2.py` (depends on T006; user-story dependency: extends US1)
- [ ] T025 [P] [US2] Add frontend integration coverage for prevent unsafe publication in `frontend/tests/integration/test_ingest_tax_assessments_us2.js` (depends on T003; user-story dependency: extends US1)
- [ ] T026 [P] [US2] Add frontend unit coverage for UI logic used by prevent unsafe publication in `frontend/tests/unit/test_ingest_tax_assessments_us2.js` (depends on T003; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T027 [US2] Implement run-model and report-field behavior for prevent unsafe publication in `backend/src/models/ingest_tax_assessments.py` (depends on T005, T022)
- [ ] T028 [P] [US2] Implement ingestion/download/load orchestration for prevent unsafe publication in `backend/src/ingestion/ingest_tax_assessments_pipeline.py` and `backend/src/ingestion/ingest_tax_assessments_qa.py` (depends on T006, T023)
- [ ] T029 [P] [US2] Implement validation, QA, or promotion behavior for prevent unsafe publication in `backend/src/services/ingest_tax_assessments.py` and `backend/src/services/ingest_tax_assessments_support.py` (depends on T007, T024)
- [ ] T030 [US2] Expose run status, operator report, or re-run controls for prevent unsafe publication in `backend/src/api/ingest_tax_assessments.py` (depends on T028, T029)
- [ ] T031 [P] [US2] Implement operator UI states for prevent unsafe publication in `frontend/src/components/ingest_tax_assessments.js` and `frontend/src/pages/ingest-tax-assessments.html` (depends on T009, T025)
- [ ] T032 [US2] Align operator-side copy, alerts, and workflow status rendering for prevent unsafe publication in `frontend/src/styles/base.css` and `frontend/src/services/ingest_tax_assessments.js` (depends on T030, T031)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Produce auditable, repeatable linking outcomes (Priority: P2)

**Goal**: Produce auditable, repeatable linking outcomes

**Independent Test**: Can be fully tested by running datasets with ambiguous links, duplicate mappings, scheduled execution, and repeated fixed-input runs, then comparing the resulting metrics and linked outputs.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T033 [P] [US3] Add contract test coverage for produce auditable, repeatable linking outcomes in `backend/tests/contract/test_ingest_tax_assessments_us3_contract.py` (depends on T008; user-story dependency: extends US2)
- [ ] T034 [P] [US3] Add backend integration coverage for produce auditable, repeatable linking outcomes in `backend/tests/integration/test_ingest_tax_assessments_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T035 [P] [US3] Add backend unit coverage for shared logic used by produce auditable, repeatable linking outcomes in `backend/tests/unit/test_ingest_tax_assessments_us3.py` (depends on T006; user-story dependency: extends US2)
- [ ] T036 [P] [US3] Add frontend integration coverage for produce auditable, repeatable linking outcomes in `frontend/tests/integration/test_ingest_tax_assessments_us3.js` (depends on T003; user-story dependency: extends US2)
- [ ] T037 [P] [US3] Add frontend unit coverage for UI logic used by produce auditable, repeatable linking outcomes in `frontend/tests/unit/test_ingest_tax_assessments_us3.js` (depends on T003; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T038 [US3] Implement run-model and report-field behavior for produce auditable, repeatable linking outcomes in `backend/src/models/ingest_tax_assessments.py` (depends on T005, T033)
- [ ] T039 [P] [US3] Implement ingestion/download/load orchestration for produce auditable, repeatable linking outcomes in `backend/src/ingestion/ingest_tax_assessments_pipeline.py` and `backend/src/ingestion/ingest_tax_assessments_qa.py` (depends on T006, T034)
- [ ] T040 [P] [US3] Implement validation, QA, or promotion behavior for produce auditable, repeatable linking outcomes in `backend/src/services/ingest_tax_assessments.py` and `backend/src/services/ingest_tax_assessments_support.py` (depends on T007, T035)
- [ ] T041 [US3] Expose run status, operator report, or re-run controls for produce auditable, repeatable linking outcomes in `backend/src/api/ingest_tax_assessments.py` (depends on T039, T040)
- [ ] T042 [P] [US3] Implement operator UI states for produce auditable, repeatable linking outcomes in `frontend/src/components/ingest_tax_assessments.js` and `frontend/src/pages/ingest-tax-assessments.html` (depends on T009, T036)
- [ ] T043 [US3] Align operator-side copy, alerts, and workflow status rendering for produce auditable, repeatable linking outcomes in `frontend/src/styles/base.css` and `frontend/src/services/ingest_tax_assessments.js` (depends on T041, T042)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T044 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/019-ingest-tax-assessments/tasks.md` (depends on T021, T032, T043)
- [ ] T045 [P] [Polish] Apply final accessibility, copy, and warning-state refinements in `frontend/src/styles/base.css`, `frontend/src/components/ingest_tax_assessments.js`, and `frontend/src/pages/ingest-tax-assessments.html` (depends on T044)
- [ ] T046 [Polish] Verify quickstart steps and update feature execution notes in `specs/019-ingest-tax-assessments/quickstart.md` (depends on T045)
- [ ] T047 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/019-ingest-tax-assessments/tasks.md` (depends on T046)

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
3. Complete Phase 3: US1 - Publish assessment baseline
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
