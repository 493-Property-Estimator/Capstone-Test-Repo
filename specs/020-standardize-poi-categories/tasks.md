# Tasks: Standardize POI categories across sources

**Input**: Design documents from `/specs/020-standardize-poi-categories/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend/frontend feature skeletons for `backend/src/api/standardize_poi_categories.py`, `frontend/src/components/standardize_poi_categories.js`, `frontend/src/pages/standardize-poi-categories.html`, and test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add frontend test bootstrap and DOM helpers in `frontend/tests/test-setup.js` (depends on T001)
- [ ] T004 [P] [Setup] Create shared page shell and base styles in `frontend/src/pages/standardize-poi-categories.html` and `frontend/src/styles/base.css` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define run-report, source-config, staging, and promotion models in `backend/src/models/standardize_poi_categories.py` (depends on T001)
- [ ] T006 [P] [Foundation] Implement shared download/load orchestration boundaries in `backend/src/ingestion/standardize_poi_categories_pipeline.py` and `backend/src/ingestion/standardize_poi_categories_qa.py` (depends on T001, informed by T005)
- [ ] T007 [P] [Foundation] Implement common validation, QA, and failure-report helpers in `backend/src/services/standardize_poi_categories.py` and `backend/src/services/standardize_poi_categories_support.py` (depends on T001, informed by T005)
- [ ] T008 [Foundation] Create run-status API or operator-report serialization in `backend/src/api/standardize_poi_categories.py` (depends on T005, T006, T007)
- [ ] T009 [P] [Foundation] Build operator UI shell or status view in `frontend/src/pages/standardize-poi-categories.html` and `frontend/src/components/standardize_poi_categories.js` (depends on T001, informed by T008)
- [ ] T010 [Foundation] Add reusable ingestion success/failure fixtures for backend and frontend tests in `backend/tests/conftest.py` and `frontend/tests/test-setup.js` (depends on T002, T003)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - Publish standardized categories (Priority: P1)

**Goal**: Publish standardized categories

**Independent Test**: Can be fully tested by running standardization on multi-source POIs with complete mappings and confirming canonical categories, provenance, and version metadata are published successfully.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T011 [P] [US1] Add contract test coverage for publish standardized categories in `backend/tests/contract/test_standardize_poi_categories_us1_contract.py` (depends on T008)
- [ ] T012 [P] [US1] Add backend integration coverage for publish standardized categories in `backend/tests/integration/test_standardize_poi_categories_us1.py` (depends on T009)
- [ ] T013 [P] [US1] Add backend unit coverage for shared logic used by publish standardized categories in `backend/tests/unit/test_standardize_poi_categories_us1.py` (depends on T006)
- [ ] T014 [P] [US1] Add frontend integration coverage for publish standardized categories in `frontend/tests/integration/test_standardize_poi_categories_us1.js` (depends on T003)
- [ ] T015 [P] [US1] Add frontend unit coverage for UI logic used by publish standardized categories in `frontend/tests/unit/test_standardize_poi_categories_us1.js` (depends on T003)

### Implementation for User Story 1

- [ ] T016 [US1] Implement run-model and report-field behavior for publish standardized categories in `backend/src/models/standardize_poi_categories.py` (depends on T005, T011)
- [ ] T017 [P] [US1] Implement ingestion/download/load orchestration for publish standardized categories in `backend/src/ingestion/standardize_poi_categories_pipeline.py` and `backend/src/ingestion/standardize_poi_categories_qa.py` (depends on T006, T012)
- [ ] T018 [P] [US1] Implement validation, QA, or promotion behavior for publish standardized categories in `backend/src/services/standardize_poi_categories.py` and `backend/src/services/standardize_poi_categories_support.py` (depends on T007, T013)
- [ ] T019 [US1] Expose run status, operator report, or re-run controls for publish standardized categories in `backend/src/api/standardize_poi_categories.py` (depends on T017, T018)
- [ ] T020 [P] [US1] Implement operator UI states for publish standardized categories in `frontend/src/components/standardize_poi_categories.js` and `frontend/src/pages/standardize-poi-categories.html` (depends on T009, T014)
- [ ] T021 [US1] Align operator-side copy, alerts, and workflow status rendering for publish standardized categories in `frontend/src/styles/base.css` and `frontend/src/services/standardize_poi_categories.js` (depends on T019, T020)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Enforce mapping governance (Priority: P1)

**Goal**: Enforce mapping governance

**Independent Test**: Can be fully tested by running standardization with new labels, conflicting mappings, threshold breaches, and forced promotion failures, then verifying the system either blocks or warns according to governance policy.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T022 [P] [US2] Add contract test coverage for enforce mapping governance in `backend/tests/contract/test_standardize_poi_categories_us2_contract.py` (depends on T008; user-story dependency: extends US1)
- [ ] T023 [P] [US2] Add backend integration coverage for enforce mapping governance in `backend/tests/integration/test_standardize_poi_categories_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T024 [P] [US2] Add backend unit coverage for shared logic used by enforce mapping governance in `backend/tests/unit/test_standardize_poi_categories_us2.py` (depends on T006; user-story dependency: extends US1)
- [ ] T025 [P] [US2] Add frontend integration coverage for enforce mapping governance in `frontend/tests/integration/test_standardize_poi_categories_us2.js` (depends on T003; user-story dependency: extends US1)
- [ ] T026 [P] [US2] Add frontend unit coverage for UI logic used by enforce mapping governance in `frontend/tests/unit/test_standardize_poi_categories_us2.js` (depends on T003; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T027 [US2] Implement run-model and report-field behavior for enforce mapping governance in `backend/src/models/standardize_poi_categories.py` (depends on T005, T022)
- [ ] T028 [P] [US2] Implement ingestion/download/load orchestration for enforce mapping governance in `backend/src/ingestion/standardize_poi_categories_pipeline.py` and `backend/src/ingestion/standardize_poi_categories_qa.py` (depends on T006, T023)
- [ ] T029 [P] [US2] Implement validation, QA, or promotion behavior for enforce mapping governance in `backend/src/services/standardize_poi_categories.py` and `backend/src/services/standardize_poi_categories_support.py` (depends on T007, T024)
- [ ] T030 [US2] Expose run status, operator report, or re-run controls for enforce mapping governance in `backend/src/api/standardize_poi_categories.py` (depends on T028, T029)
- [ ] T031 [P] [US2] Implement operator UI states for enforce mapping governance in `frontend/src/components/standardize_poi_categories.js` and `frontend/src/pages/standardize-poi-categories.html` (depends on T009, T025)
- [ ] T032 [US2] Align operator-side copy, alerts, and workflow status rendering for enforce mapping governance in `frontend/src/styles/base.css` and `frontend/src/services/standardize_poi_categories.js` (depends on T030, T031)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Support deterministic and repeatable reclassification (Priority: P2)

**Goal**: Support deterministic and repeatable reclassification

**Independent Test**: Can be fully tested by re-running the same inputs with fixed taxonomy and mapping versions, then re-running after a taxonomy change and comparing assignments and metadata.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T033 [P] [US3] Add contract test coverage for support deterministic and repeatable reclassification in `backend/tests/contract/test_standardize_poi_categories_us3_contract.py` (depends on T008; user-story dependency: extends US2)
- [ ] T034 [P] [US3] Add backend integration coverage for support deterministic and repeatable reclassification in `backend/tests/integration/test_standardize_poi_categories_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T035 [P] [US3] Add backend unit coverage for shared logic used by support deterministic and repeatable reclassification in `backend/tests/unit/test_standardize_poi_categories_us3.py` (depends on T006; user-story dependency: extends US2)
- [ ] T036 [P] [US3] Add frontend integration coverage for support deterministic and repeatable reclassification in `frontend/tests/integration/test_standardize_poi_categories_us3.js` (depends on T003; user-story dependency: extends US2)
- [ ] T037 [P] [US3] Add frontend unit coverage for UI logic used by support deterministic and repeatable reclassification in `frontend/tests/unit/test_standardize_poi_categories_us3.js` (depends on T003; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T038 [US3] Implement run-model and report-field behavior for support deterministic and repeatable reclassification in `backend/src/models/standardize_poi_categories.py` (depends on T005, T033)
- [ ] T039 [P] [US3] Implement ingestion/download/load orchestration for support deterministic and repeatable reclassification in `backend/src/ingestion/standardize_poi_categories_pipeline.py` and `backend/src/ingestion/standardize_poi_categories_qa.py` (depends on T006, T034)
- [ ] T040 [P] [US3] Implement validation, QA, or promotion behavior for support deterministic and repeatable reclassification in `backend/src/services/standardize_poi_categories.py` and `backend/src/services/standardize_poi_categories_support.py` (depends on T007, T035)
- [ ] T041 [US3] Expose run status, operator report, or re-run controls for support deterministic and repeatable reclassification in `backend/src/api/standardize_poi_categories.py` (depends on T039, T040)
- [ ] T042 [P] [US3] Implement operator UI states for support deterministic and repeatable reclassification in `frontend/src/components/standardize_poi_categories.js` and `frontend/src/pages/standardize-poi-categories.html` (depends on T009, T036)
- [ ] T043 [US3] Align operator-side copy, alerts, and workflow status rendering for support deterministic and repeatable reclassification in `frontend/src/styles/base.css` and `frontend/src/services/standardize_poi_categories.js` (depends on T041, T042)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T044 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/020-standardize-poi-categories/tasks.md` (depends on T021, T032, T043)
- [ ] T045 [P] [Polish] Apply final accessibility, copy, and warning-state refinements in `frontend/src/styles/base.css`, `frontend/src/components/standardize_poi_categories.js`, and `frontend/src/pages/standardize-poi-categories.html` (depends on T044)
- [ ] T046 [Polish] Verify quickstart steps and update feature execution notes in `specs/020-standardize-poi-categories/quickstart.md` (depends on T045)
- [ ] T047 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/020-standardize-poi-categories/tasks.md` (depends on T046)

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

- `specs/020-standardize-poi-categories/` depends on `specs/017-geospatial-ingest/` when integrating the shared platform because The spec explicitly standardizes POIs after geospatial ingestion stores raw POI records.

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
3. Complete Phase 3: US1 - Publish standardized categories
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
