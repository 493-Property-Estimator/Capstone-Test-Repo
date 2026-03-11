# Implementation Plan: Use assessment baseline

**Branch**: `016-assessment-baseline` | **Date**: 2026-03-11 | **Spec**: `specs/016-assessment-baseline/spec.md`
**Input**: Feature specification from `/specs/016-assessment-baseline/spec.md`

**Note**: This plan is generated via the `/prompts:speckit.plan` workflow.

## Summary

Anchor estimates to official assessment baselines, compute factor-based adjustments, and return explainable results with stable provenance, deterministic matching, and explicit warnings for ambiguous matches, fallbacks, partial features, and guardrail caps.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only)  
**Storage**: Assessment Data Store + Feature Store/Database (existing sources)  
**Testing**: pytest for Python; frontend testing harness per feature (must meet constitution gates)  
**Target Platform**: Web application (modern desktop + mobile browsers)  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: p95 < 1.5 s cached estimate, p95 < 3.5 s uncached; UI updates < 100 ms  
**Constraints**: Vanilla stack only; performance budgets enforced; acceptance tests required  
**Scale/Scope**: Single estimate request flow; baseline + factor adjustments for a city-sized dataset

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Code quality: lint/format clean, modular structure, no unjustified complexity
- [ ] Testing: acceptance tests mapped to `Acceptance Tests/UC-16-AT.md` plus unit/integration
- [ ] UX consistency: shared styles/components used, labels/validation consistent
- [ ] Performance: budgets met or explicit waiver documented
- [ ] Traceability: all work mapped to UC-16 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/016-assessment-baseline/
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
│   ├── models/
│   ├── services/
│   └── lib/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── styles/
└── tests/
```

**Structure Decision**: Web app with a thin backend API for baseline lookup and valuation, and a frontend UI for baseline-plus-adjustments presentation and warnings.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
