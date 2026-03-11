# Implementation Plan: Show Missing-Data Warnings in UI

**Branch**: `026-missing-data-warnings` | **Date**: 2026-03-11 | **Spec**: `specs/026-missing-data-warnings/spec.md`
**Input**: Feature specification from `/specs/026-missing-data-warnings/spec.md`

**Note**: This plan is generated via the `/prompts:speckit.plan` workflow.

## Summary

Surface missing or approximated data in the estimate UI with confidence indicators, severity-specific warnings, expandable details, and non-blocking dismissal while keeping estimates usable.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only)  
**Storage**: N/A (UI rendering of API metadata)  
**Testing**: pytest for Python; frontend testing harness per feature (must meet constitution gates)  
**Target Platform**: Web application (modern desktop + mobile browsers)  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: UI updates < 100 ms; warning panel interactions remain responsive  
**Constraints**: Vanilla stack only; performance budgets enforced; acceptance tests required  
**Scale/Scope**: Estimate result UI warnings and confidence display

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Code quality: lint/format clean, modular structure, no unjustified complexity
- [ ] Testing: acceptance tests mapped to `Acceptance Tests/UC-26-AT.md` plus unit/integration
- [ ] UX consistency: shared styles/components used, labels/validation consistent
- [ ] Performance: budgets met or explicit waiver documented
- [ ] Traceability: all work mapped to UC-26 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/026-missing-data-warnings/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── warning-panel.js
│   │   └── confidence-indicator.js
│   ├── pages/
│   │   └── estimate.html
│   ├── services/
│   │   └── estimate-api.js
│   └── styles/
│       └── base.css
└── tests/

backend/
└── src/
    ├── api/
    │   └── missing_data_warnings.py
    └── services/
        └── warning_metadata.py
```

**Structure Decision**: Frontend UI renders warnings and confidence from API metadata; backend logs malformed metadata.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
