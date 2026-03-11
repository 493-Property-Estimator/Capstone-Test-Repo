# Implementation Plan: Ingest open geospatial datasets

**Branch**: `017-geospatial-ingest` | **Date**: 2026-03-11 | **Spec**: `specs/017-geospatial-ingest/spec.md`
**Input**: Feature specification from `/specs/017-geospatial-ingest/spec.md`

**Note**: This plan is generated via the `/prompts:speckit.plan` workflow.

## Summary

Ingest open geospatial datasets for roads, boundaries, and POIs with validation, canonical transformations, QA gates, atomic promotion, and auditable run metadata while preserving last known-good production data on failures.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only)  
**Storage**: Spatial database/feature store with staging and production tables  
**Testing**: pytest for Python; frontend testing harness per feature (must meet constitution gates)  
**Target Platform**: Web application (operator UI) + batch ingestion runner  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: Ingestion completes within operational window; UI updates < 100 ms  
**Constraints**: Vanilla stack only; performance budgets enforced; acceptance tests required  
**Scale/Scope**: City-scale geospatial datasets (roads, boundaries, POIs)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Code quality: lint/format clean, modular structure, no unjustified complexity
- [ ] Testing: acceptance tests mapped to `Acceptance Tests/UC-17-AT.md` plus unit/integration
- [ ] UX consistency: shared styles/components used, labels/validation consistent
- [ ] Performance: budgets met or explicit waiver documented
- [ ] Traceability: all work mapped to UC-17 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/017-geospatial-ingest/
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
│   │   └── geospatial_ingest.py
│   ├── models/
│   │   └── geospatial_ingest.py
│   ├── services/
│   │   ├── geospatial_ingest.py
│   │   └── geospatial_ingest_support.py
│   ├── ingestion/
│   │   ├── geospatial_ingest_pipeline.py
│   │   └── geospatial_ingest_qa.py
│   └── lib/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   │   └── geospatial_ingest.js
│   ├── pages/
│   │   └── geospatial-ingest.html
│   ├── services/
│   │   └── geospatial_ingest.js
│   └── styles/
│       └── base.css
└── tests/
```

**Structure Decision**: Web app with a backend ingestion pipeline and operator UI; ingestion services handle download/validate/transform/QA/promote.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
