# Implementation Plan: Fall Back to Straight-Line Distance When Routing Fails

**Branch**: `027-straight-line-fallback` | **Date**: 2026-03-11 | **Spec**: `specs/027-straight-line-fallback/spec.md`
**Input**: Feature specification from `/specs/027-straight-line-fallback/spec.md`

**Note**: This plan is generated via the `/prompts:speckit.plan` workflow.

## Summary

Provide straight-line distance fallback when routing fails, preserve mixed-mode outputs for partial failures, and surface warnings, confidence reduction, and traceable logs.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only)  
**Storage**: Feature store + logging/metrics  
**Testing**: pytest for Python; frontend testing harness per feature (must meet constitution gates)  
**Target Platform**: Web application (API backend)  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: Distance computation within time budget; fallback computed quickly  
**Constraints**: Vanilla stack only; performance budgets enforced; acceptance tests required  
**Scale/Scope**: Distance computations for multiple targets per estimate

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Code quality: lint/format clean, modular structure, no unjustified complexity
- [ ] Testing: acceptance tests mapped to `Acceptance Tests/UC-27-AT.md` plus unit/integration
- [ ] UX consistency: shared styles/components used, labels/validation consistent
- [ ] Performance: budgets met or explicit waiver documented
- [ ] Traceability: all work mapped to UC-27 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/027-straight-line-fallback/
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
│   └── valuation/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/
```

**Structure Decision**: Backend distance service with fallback logic; API surfaces warnings and indicators.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
