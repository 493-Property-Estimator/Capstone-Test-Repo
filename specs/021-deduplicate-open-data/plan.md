# Implementation Plan: Deduplicate open-data entities

**Branch**: `021-deduplicate-open-data` | **Date**: 2026-03-11 | **Spec**: `specs/021-deduplicate-open-data/spec.md`
**Input**: Feature specification from `/specs/021-deduplicate-open-data/spec.md`

**Note**: This plan is generated via the `/prompts:speckit.plan` workflow.

## Summary

Deduplicate multi-source open-data entities into canonical entities using deterministic matching rules, confidence thresholds, QA safeguards, and atomic publication while preserving last known-good canonical data on failures.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only)  
**Storage**: Spatial database/feature store with canonical entities and link tables  
**Testing**: pytest for Python; frontend testing harness per feature (must meet constitution gates)  
**Target Platform**: Web application (operator UI) + batch deduplication runner  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: Deduplication completes within operational window; UI updates < 100 ms  
**Constraints**: Vanilla stack only; performance budgets enforced; acceptance tests required  
**Scale/Scope**: City-scale POI inventories with overlapping sources

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Code quality: lint/format clean, modular structure, no unjustified complexity
- [ ] Testing: acceptance tests mapped to `Acceptance Tests/UC-21-AT.md` plus unit/integration
- [ ] UX consistency: shared styles/components used, labels/validation consistent
- [ ] Performance: budgets met or explicit waiver documented
- [ ] Traceability: all work mapped to UC-21 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/021-deduplicate-open-data/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── deduplicate_open_data.py
│   ├── models/
│   │   └── deduplicate_open_data.py
│   ├── services/
│   │   ├── deduplicate_open_data.py
│   │   └── deduplicate_open_data_support.py
│   └── lib/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   │   ├── deduplicate_open_data.js
│   │   └── deduplicate_open_data_panel.js
│   ├── pages/
│   │   └── deduplicate-open-data.html
│   ├── services/
│   │   └── deduplicate_open_data.js
│   └── styles/
│       └── base.css
└── tests/
```

**Structure Decision**: Web app with backend deduplication services and operator UI; matching/QA/publication handled server-side.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
