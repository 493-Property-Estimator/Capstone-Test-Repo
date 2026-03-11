# Implementation Plan: Ingest municipal census datasets

**Branch**: `018-census-ingest` | **Date**: 2026-03-11 | **Spec**: `specs/018-census-ingest/spec.md`
**Input**: Feature specification from `/specs/018-census-ingest/spec.md`

**Note**: This plan is generated via the `/prompts:speckit.plan` workflow.

## Summary

Ingest municipal census datasets, normalize and link to internal area keys, compute neighbourhood indicators, and publish them safely with QA gating, coverage thresholds, and auditable run metadata while preserving the last known-good production indicators on failures.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only)  
**Storage**: Database/feature store with raw staging and indicator tables  
**Testing**: pytest for Python; frontend testing harness per feature (must meet constitution gates)  
**Target Platform**: Web application (operator UI) + batch ingestion runner  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: Ingestion completes within operational window; UI updates < 100 ms  
**Constraints**: Vanilla stack only; performance budgets enforced; acceptance tests required  
**Scale/Scope**: City-scale census datasets and neighbourhood indicators

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Code quality: lint/format clean, modular structure, no unjustified complexity
- [ ] Testing: acceptance tests mapped to `Acceptance Tests/UC-18-AT.md` plus unit/integration
- [ ] UX consistency: shared styles/components used, labels/validation consistent
- [ ] Performance: budgets met or explicit waiver documented
- [ ] Traceability: all work mapped to UC-18 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/018-census-ingest/
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
│   │   └── census_ingest.py
│   ├── models/
│   │   └── census_ingest.py
│   ├── services/
│   │   ├── census_ingest.py
│   │   └── census_ingest_support.py
│   ├── ingestion/
│   │   ├── census_ingest_pipeline.py
│   │   └── census_ingest_qa.py
│   └── lib/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   │   └── census_ingest.js
│   ├── pages/
│   │   └── census-ingest.html
│   ├── services/
│   │   └── census_ingest.js
│   └── styles/
│       └── base.css
└── tests/
```

**Structure Decision**: Web app with backend ingestion services and operator UI; indicator computation and QA run server-side.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
