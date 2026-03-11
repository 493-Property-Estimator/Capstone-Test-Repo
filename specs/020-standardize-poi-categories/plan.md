# Implementation Plan: Standardize POI categories across sources

**Branch**: `020-standardize-poi-categories` | **Date**: 2026-03-11 | **Spec**: `specs/020-standardize-poi-categories/spec.md`
**Input**: Feature specification from `/specs/020-standardize-poi-categories/spec.md`

**Note**: This plan is generated via the `/prompts:speckit.plan` workflow.

## Summary

Standardize POI categories into a canonical taxonomy with deterministic mappings, governance thresholds for unmapped/conflicts, atomic promotion, and auditable run metadata while preserving last known-good standardized outputs on failures.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only)  
**Storage**: Feature store tables for raw POIs, standardized POIs, and run metadata  
**Testing**: pytest for Python; frontend testing harness per feature (must meet constitution gates)  
**Target Platform**: Web application (operator UI) + batch standardization runner  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: Standardization completes within operational window; UI updates < 100 ms  
**Constraints**: Vanilla stack only; performance budgets enforced; acceptance tests required  
**Scale/Scope**: City-scale POI inventories across multiple sources

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Code quality: lint/format clean, modular structure, no unjustified complexity
- [ ] Testing: acceptance tests mapped to `Acceptance Tests/UC-20-AT.md` plus unit/integration
- [ ] UX consistency: shared styles/components used, labels/validation consistent
- [ ] Performance: budgets met or explicit waiver documented
- [ ] Traceability: all work mapped to UC-20 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/020-standardize-poi-categories/
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
│   │   └── standardize_poi_categories.py
│   ├── models/
│   │   └── standardize_poi_categories.py
│   ├── services/
│   │   ├── standardize_poi_categories.py
│   │   └── standardize_poi_categories_support.py
│   ├── ingestion/
│   │   ├── standardize_poi_categories_pipeline.py
│   │   └── standardize_poi_categories_qa.py
│   └── lib/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   │   └── standardize_poi_categories.js
│   ├── pages/
│   │   └── standardize-poi-categories.html
│   ├── services/
│   │   └── standardize_poi_categories.js
│   └── styles/
│       └── base.css
└── tests/
```

**Structure Decision**: Web app with backend standardization services and operator UI; mapping/QA/promotion handled server-side.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
