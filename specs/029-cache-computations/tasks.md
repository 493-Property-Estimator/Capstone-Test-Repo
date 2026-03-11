# Tasks: Cache Frequently Requested Computations

**Input**: Design documents from `/specs/029-cache-computations/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `contracts/ui.md`
**Tests**: Include the tests needed to keep this feature acceptance-test traceable and independently verifiable.
**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and reviewed independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks that touch different files and have no unmet dependencies
- **[Story]**: Shared setup/foundation or the owning user story (`US1`, `US2`, `US3`)
- Every task includes an exact target path and explicit prerequisite task IDs

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline structure, fixtures, and shared helpers required before story work starts

- [ ] T001 [Setup] Create backend feature skeleton for `backend/src/api/cache_computations.py`, `backend/src/models/cache_computations.py`, `backend/src/services/cache_computations.py`, and backend test directories (no dependencies)
- [ ] T002 [P] [Setup] Add backend test bootstrap and reusable fixtures in `backend/tests/conftest.py` (depends on T001)
- [ ] T003 [P] [Setup] Add shared backend assertion helpers in `backend/tests/support.py` (depends on T001)
- [ ] T004 [P] [Setup] Create shared constants/config helpers in `backend/src/services/cache_computations.py` (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts, base models, and orchestration boundaries required by all user stories

**⚠️ CRITICAL**: No story implementation should start until this phase is complete

- [ ] T005 [Foundation] Define shared feature models and result envelopes in `backend/src/models/cache_computations.py` (depends on T001)
- [ ] T006 [P] [Foundation] Implement shared computation and fallback interfaces in `backend/src/services/cache_computations.py` and `backend/src/services/cache_computations_support.py` (depends on T001, informed by T005)
- [ ] T007 [P] [Foundation] Create orchestration helpers or entrypoints in `backend/src/api/cache_computations.py` when applicable and shared test fixtures in `backend/tests/conftest.py` (depends on T005, T006)
- [ ] T008 [P] [Foundation] Add deterministic formatting, weighting, or reporting helpers in `backend/src/services/cache_computations_reporting.py` (depends on T001)
- [ ] T009 [Foundation] Add reusable success, fallback, and failure fixtures for backend tests in `backend/tests/conftest.py` and `backend/tests/support.py` (depends on T002, T003)

**Checkpoint**: Foundational contracts and shared helpers are ready for story implementation

---

## Phase 3: User Story 1 - Reuse Valid Cached Estimate (Priority: P1)

**Goal**: Reuse Valid Cached Estimate

**Independent Test**: Can be fully tested by sending the same estimate request twice within the validity window and confirming the second response is served from cache with the same result.

### Tests for User Story 1

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T010 [P] [US1] Add backend contract-or-shape regression coverage for reuse valid cached estimate in `backend/tests/unit/test_cache_computations_us1_contract_shape.py` (depends on T005)
- [ ] T011 [P] [US1] Add backend integration coverage for reuse valid cached estimate in `backend/tests/integration/test_cache_computations_us1.py` (depends on T009)
- [ ] T012 [P] [US1] Add backend unit coverage for shared logic used by reuse valid cached estimate in `backend/tests/unit/test_cache_computations_us1.py` (depends on T006)

### Implementation for User Story 1

- [ ] T013 [US1] Extend feature models or result envelopes for reuse valid cached estimate in `backend/src/models/cache_computations.py` (depends on T005, T010)
- [ ] T014 [P] [US1] Implement primary computation behavior for reuse valid cached estimate in `backend/src/services/cache_computations.py` and `backend/src/services/cache_computations_support.py` (depends on T006, T011)
- [ ] T015 [P] [US1] Implement fallback, weighting, formatting, or deterministic-output behavior for reuse valid cached estimate in `backend/src/services/cache_computations_reporting.py` (depends on T008, T012)
- [ ] T016 [US1] Wire orchestration or estimate-pipeline integration for reuse valid cached estimate in `backend/src/api/cache_computations.py` when applicable, otherwise in `backend/src/services/cache_computations.py` (depends on T014, T015)

**Checkpoint**: User Story 1 should now be independently functional and reviewable

---

## Phase 4: User Story 2 - Populate Cache on Miss or Stale Result (Priority: P2)

**Goal**: Populate Cache on Miss or Stale Result

**Independent Test**: Can be fully tested by requesting an uncached estimate, confirming a miss and cache population, then expiring or invalidating the entry and confirming recomputation refreshes the cache.

### Tests for User Story 2

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T017 [P] [US2] Add backend contract-or-shape regression coverage for populate cache on miss or stale result in `backend/tests/unit/test_cache_computations_us2_contract_shape.py` (depends on T005; user-story dependency: extends US1)
- [ ] T018 [P] [US2] Add backend integration coverage for populate cache on miss or stale result in `backend/tests/integration/test_cache_computations_us2.py` (depends on T009; user-story dependency: extends US1)
- [ ] T019 [P] [US2] Add backend unit coverage for shared logic used by populate cache on miss or stale result in `backend/tests/unit/test_cache_computations_us2.py` (depends on T006; user-story dependency: extends US1)

### Implementation for User Story 2

- [ ] T020 [US2] Extend feature models or result envelopes for populate cache on miss or stale result in `backend/src/models/cache_computations.py` (depends on T005, T017)
- [ ] T021 [P] [US2] Implement primary computation behavior for populate cache on miss or stale result in `backend/src/services/cache_computations.py` and `backend/src/services/cache_computations_support.py` (depends on T006, T018)
- [ ] T022 [P] [US2] Implement fallback, weighting, formatting, or deterministic-output behavior for populate cache on miss or stale result in `backend/src/services/cache_computations_reporting.py` (depends on T008, T019)
- [ ] T023 [US2] Wire orchestration or estimate-pipeline integration for populate cache on miss or stale result in `backend/src/api/cache_computations.py` when applicable, otherwise in `backend/src/services/cache_computations.py` (depends on T021, T022)

**Checkpoint**: User Story 2 should now be independently functional and reviewable

---

## Phase 5: User Story 3 - Fail Safely When Cache Cannot Be Trusted (Priority: P3)

**Goal**: Fail Safely When Cache Cannot Be Trusted

**Independent Test**: Can be fully tested by simulating cache outage and corrupted cache entries and verifying the system recomputes estimates without crashing or hard-failing the request.

### Tests for User Story 3

> **NOTE: Write these tests first, ensure they fail before implementation**

- [ ] T024 [P] [US3] Add backend contract-or-shape regression coverage for fail safely when cache cannot be trusted in `backend/tests/unit/test_cache_computations_us3_contract_shape.py` (depends on T005; user-story dependency: extends US2)
- [ ] T025 [P] [US3] Add backend integration coverage for fail safely when cache cannot be trusted in `backend/tests/integration/test_cache_computations_us3.py` (depends on T009; user-story dependency: extends US2)
- [ ] T026 [P] [US3] Add backend unit coverage for shared logic used by fail safely when cache cannot be trusted in `backend/tests/unit/test_cache_computations_us3.py` (depends on T006; user-story dependency: extends US2)

### Implementation for User Story 3

- [ ] T027 [US3] Extend feature models or result envelopes for fail safely when cache cannot be trusted in `backend/src/models/cache_computations.py` (depends on T005, T024)
- [ ] T028 [P] [US3] Implement primary computation behavior for fail safely when cache cannot be trusted in `backend/src/services/cache_computations.py` and `backend/src/services/cache_computations_support.py` (depends on T006, T025)
- [ ] T029 [P] [US3] Implement fallback, weighting, formatting, or deterministic-output behavior for fail safely when cache cannot be trusted in `backend/src/services/cache_computations_reporting.py` (depends on T008, T026)
- [ ] T030 [US3] Wire orchestration or estimate-pipeline integration for fail safely when cache cannot be trusted in `backend/src/api/cache_computations.py` when applicable, otherwise in `backend/src/services/cache_computations.py` (depends on T028, T029)

**Checkpoint**: User Story 3 should now be independently functional and reviewable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish traceability, accessibility, observability, and execution validation that spans multiple stories

- [ ] T031 [P] [Polish] Add acceptance-traceability notes linking tests to the relevant acceptance scenarios in `backend/tests/`, `frontend/tests/`, and `specs/029-cache-computations/tasks.md` (depends on T016, T023, T030)
- [ ] T032 [P] [Polish] Apply final observability, logging, and deterministic-output refinements in `backend/src/services/cache_computations.py` and `backend/src/api/cache_computations.py` when applicable (depends on T031)
- [ ] T033 [Polish] Verify quickstart steps and update feature execution notes in `specs/029-cache-computations/quickstart.md` (depends on T032)
- [ ] T034 [Polish] Run the full test scope for this feature and record any remaining gaps in `specs/029-cache-computations/tasks.md` (depends on T033)

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

- `specs/029-cache-computations/` depends on `specs/023-property-estimate-api/` when integrating the shared platform because Caching wraps the estimate API request normalization, response storage, and replay path.

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
3. Complete Phase 3: US1 - Reuse Valid Cached Estimate
4. Validate US1 independently before expanding to later priorities
5. Continue story-by-story, preserving explicit task and cross-feature dependencies
