# Implementation Plan: Ingest property tax assessment data

**Branch**: `019-ingest-tax-assessments` | **Date**: 2026-03-11 | **Spec**: `specs/019-ingest-tax-assessments/spec.md`
**Input**: Feature specification from `/specs/019-ingest-tax-assessments/spec.md`

**Note**: This plan is generated via the `/prompts:speckit.plan` workflow.

## Summary

Ingest property tax assessment datasets, normalize and link records to canonical locations, quarantine invalid rows per policy, enforce QA thresholds, and promote a new baseline atomically with auditable run metadata while preserving last known-good production baselines on failures.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only)  
**Storage**: Assessment store with raw, normalized, and production baseline tables  
**Testing**: pytest for Python; frontend testing harness per feature (must meet constitution gates)  
**Target Platform**: Web application (operator UI) + batch ingestion runner  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: Ingestion completes within operational window; UI updates < 100 ms  
**Constraints**: Vanilla stack only; performance budgets enforced; acceptance tests required  
**Scale/Scope**: City-scale assessment datasets keyed by canonical location ID

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Code quality: lint/format clean, modular structure, no unjustified complexity
- [ ] Testing: acceptance tests mapped to `Acceptance Tests/UC-19-AT.md` plus unit/integration
- [ ] UX consistency: shared styles/components used, labels/validation consistent
- [ ] Performance: budgets met or explicit waiver documented
- [ ] Traceability: all work mapped to UC-19 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/019-ingest-tax-assessments/
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
│   │   └── ingest_tax_assessments.py
│   ├── models/
│   │   └── ingest_tax_assessments.py
│   ├── services/
│   │   ├── ingest_tax_assessments.py
│   │   └── ingest_tax_assessments_support.py
│   ├── ingestion/
│   │   ├── ingest_tax_assessments_pipeline.py
│   │   └── ingest_tax_assessments_qa.py
│   └── lib/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   │   └── ingest_tax_assessments.js
│   ├── pages/
│   │   └── ingest-tax-assessments.html
│   ├── services/
│   │   └── ingest_tax_assessments.js
│   └── styles/
│       └── base.css
└── tests/
```

**Structure Decision**: Web app with backend ingestion services and operator UI; linking/QA/promotion handled server-side.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
