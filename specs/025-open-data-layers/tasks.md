# Tasks: Toggle Open-Data Layers in the Map UI

**Input**: Design documents from `/specs/025-open-data-layers/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend/frontend feature skeletons for `backend/src/api/open_data_layers.py`, `frontend/src/components/layer-panel.js`, `frontend/src/pages/map-layers.html`, and test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add frontend test bootstrap and DOM helpers in `frontend/tests/test-setup.js` (depends on T001)
- [ ] T004 [P] [Setup] Create shared page shell and base styles in `frontend/src/pages/map-layers.html` and `frontend/src/styles/base.css` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define shared client-side state, API payload adapters, and UI state models in `frontend/src/services/layer-api.js` and `frontend/src/components/layer-panel.js` (depends on T001)
- [ ] T006 [P] [Foundation] Implement backend proxy/service contract in `backend/src/services/layer_data.py` (depends on T001, informed by T005)
- [ ] T007 [P] [Foundation] Build shared page shell, loading regions, and warning regions in `frontend/src/pages/map-layers.html` and `frontend/src/styles/base.css` (depends on T001)
- [ ] T008 [Foundation] Add reusable frontend fixtures for success, warning, and failure states in `frontend/tests/test-setup.js` plus backend forwarding fixtures in `backend/tests/conftest.py` (depends on T002, T003)
- [ ] T009 [P] [Foundation] Create backend normalization or forwarding helpers in `backend/src/services/layer_data.py` (depends on T001)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - Turn map layers on and off (Priority: P1)

**Goal**: Turn map layers on and off

**Independent Test**: Can be fully tested by opening the layer panel, enabling one or more layers, verifying the overlays and legend appear, then disabling a layer and confirming it is fully removed.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T010 [P] [US1] Add backend contract-or-shape regression coverage for turn map layers on and off in `backend/tests/unit/test_open_data_layers_us1_contract_shape.py` (depends on T005)
- [ ] T011 [P] [US1] Add backend integration coverage for turn map layers on and off in `backend/tests/integration/test_open_data_layers_us1.py` (depends on T009)
- [ ] T012 [P] [US1] Add backend unit coverage for shared logic used by turn map layers on and off in `backend/tests/unit/test_open_data_layers_us1.py` (depends on T006)
- [ ] T013 [P] [US1] Add frontend integration coverage for turn map layers on and off in `frontend/tests/integration/test_open_data_layers_us1.js` (depends on T003)
- [ ] T014 [P] [US1] Add frontend unit coverage for UI logic used by turn map layers on and off in `frontend/tests/unit/test_open_data_layers_us1.js` (depends on T003)

### Implementation for User Story 1

- [ ] T015 [US1] Implement client-side state and request handling for turn map layers on and off in `frontend/src/services/layer-api.js` (depends on T005, T013)
- [ ] T016 [P] [US1] Implement primary UI components for turn map layers on and off in `frontend/src/components/layer-panel.js` and `frontend/src/components/layer-legend.js` (depends on T007, T013)
- [ ] T017 [P] [US1] Implement backend proxy or forwarding behavior for turn map layers on and off in `backend/src/services/layer_data.py` (depends on T006, T011)
- [ ] T018 [US1] Wire page-level interactions, retry states, and selection handling for turn map layers on and off in `frontend/src/pages/map-layers.html` (depends on T015, T016, T017)
- [ ] T019 [US1] Align copy, warnings, and accessible styles for turn map layers on and off in `frontend/src/styles/base.css` (depends on T018)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Keep layers in sync with map movement and heavy data (Priority: P1)

**Goal**: Keep layers in sync with map movement and heavy data

**Independent Test**: Can be fully tested by enabling a layer, panning or zooming the map, rapidly toggling layers, and enabling a heavy layer while confirming the UI stays responsive and reflects the final requested state.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T020 [P] [US2] Add backend contract-or-shape regression coverage for keep layers in sync with map movement and heavy data in `backend/tests/unit/test_open_data_layers_us2_contract_shape.py` (depends on T005; user-story dependency: extends US1)
- [ ] T021 [P] [US2] Add backend integration coverage for keep layers in sync with map movement and heavy data in `backend/tests/integration/test_open_data_layers_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T022 [P] [US2] Add backend unit coverage for shared logic used by keep layers in sync with map movement and heavy data in `backend/tests/unit/test_open_data_layers_us2.py` (depends on T006; user-story dependency: extends US1)
- [ ] T023 [P] [US2] Add frontend integration coverage for keep layers in sync with map movement and heavy data in `frontend/tests/integration/test_open_data_layers_us2.js` (depends on T003; user-story dependency: extends US1)
- [ ] T024 [P] [US2] Add frontend unit coverage for UI logic used by keep layers in sync with map movement and heavy data in `frontend/tests/unit/test_open_data_layers_us2.js` (depends on T003; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T025 [US2] Implement client-side state and request handling for keep layers in sync with map movement and heavy data in `frontend/src/services/layer-api.js` (depends on T005, T023)
- [ ] T026 [P] [US2] Implement primary UI components for keep layers in sync with map movement and heavy data in `frontend/src/components/layer-panel.js` and `frontend/src/components/layer-legend.js` (depends on T007, T023)
- [ ] T027 [P] [US2] Implement backend proxy or forwarding behavior for keep layers in sync with map movement and heavy data in `backend/src/services/layer_data.py` (depends on T006, T021)
- [ ] T028 [US2] Wire page-level interactions, retry states, and selection handling for keep layers in sync with map movement and heavy data in `frontend/src/pages/map-layers.html` (depends on T025, T026, T027)
- [ ] T029 [US2] Align copy, warnings, and accessible styles for keep layers in sync with map movement and heavy data in `frontend/src/styles/base.css` (depends on T028)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Handle missing or partial layer data gracefully (Priority: P2)

**Goal**: Handle missing or partial layer data gracefully

**Independent Test**: Can be fully tested by simulating a layer API outage and by enabling a layer in a region with incomplete coverage, then verifying the user sees the correct warning and map behavior.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T030 [P] [US3] Add backend contract-or-shape regression coverage for handle missing or partial layer data gracefully in `backend/tests/unit/test_open_data_layers_us3_contract_shape.py` (depends on T005; user-story dependency: extends US2)
- [ ] T031 [P] [US3] Add backend integration coverage for handle missing or partial layer data gracefully in `backend/tests/integration/test_open_data_layers_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T032 [P] [US3] Add backend unit coverage for shared logic used by handle missing or partial layer data gracefully in `backend/tests/unit/test_open_data_layers_us3.py` (depends on T006; user-story dependency: extends US2)
- [ ] T033 [P] [US3] Add frontend integration coverage for handle missing or partial layer data gracefully in `frontend/tests/integration/test_open_data_layers_us3.js` (depends on T003; user-story dependency: extends US2)
- [ ] T034 [P] [US3] Add frontend unit coverage for UI logic used by handle missing or partial layer data gracefully in `frontend/tests/unit/test_open_data_layers_us3.js` (depends on T003; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T035 [US3] Implement client-side state and request handling for handle missing or partial layer data gracefully in `frontend/src/services/layer-api.js` (depends on T005, T033)
- [ ] T036 [P] [US3] Implement primary UI components for handle missing or partial layer data gracefully in `frontend/src/components/layer-panel.js` and `frontend/src/components/layer-legend.js` (depends on T007, T033)
- [ ] T037 [P] [US3] Implement backend proxy or forwarding behavior for handle missing or partial layer data gracefully in `backend/src/services/layer_data.py` (depends on T006, T031)
- [ ] T038 [US3] Wire page-level interactions, retry states, and selection handling for handle missing or partial layer data gracefully in `frontend/src/pages/map-layers.html` (depends on T035, T036, T037)
- [ ] T039 [US3] Align copy, warnings, and accessible styles for handle missing or partial layer data gracefully in `frontend/src/styles/base.css` (depends on T038)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T040 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/025-open-data-layers/tasks.md` (depends on T019, T029, T039)
- [ ] T041 [P] [Polish] Apply final accessibility, copy, and warning-state refinements in `frontend/src/styles/base.css`, `frontend/src/components/layer-panel.js`, and `frontend/src/pages/map-layers.html` (depends on T040)
- [ ] T042 [Polish] Verify quickstart steps and update feature execution notes in `specs/025-open-data-layers/quickstart.md` (depends on T041)
- [ ] T043 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/025-open-data-layers/tasks.md` (depends on T042)

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

- `specs/025-open-data-layers/` depends on `specs/003-user-map/` when integrating the shared platform because Open-data overlays depend on the shared map UI and viewport state.
- `specs/025-open-data-layers/` depends on `specs/017-geospatial-ingest/` when integrating the shared platform because Layer rendering depends on ingested geospatial layer data being available.
- `specs/025-open-data-layers/` depends on `specs/020-standardize-poi-categories/` when integrating the shared platform because POI overlays should use standardized category outputs when those layers are exposed.
- `specs/025-open-data-layers/` depends on `specs/021-deduplicate-open-data/` when integrating the shared platform because Overlay rendering should use deduplicated source records to avoid duplicate map features.

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
3. Complete Phase 3: US1 - Turn map layers on and off
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
