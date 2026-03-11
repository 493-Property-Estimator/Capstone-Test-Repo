# Implementation Plan: Show Top Contributing Factors

**Branch**: `015-top-contributing-factors` | **Date**: 2026-03-10 | **Spec**: `/home/ayra/ECE_493/Capstone-Test-Repo/specs/015-top-contributing-factors/spec.md`
**Input**: Feature specification from `/specs/015-top-contributing-factors/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement explanation view: retrieve feature values and baseline metadata, compute per-factor contributions, rank and format top-N increases/decreases with readable labels and supporting values, and display map context when available. Handle missing features, unsupported attribution with qualitative explanations, explainability failures with retry, policy-based filtering, and deterministic ordering.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only); explainability service accessed via internal adapters  
**Storage**: No new persistent storage for this feature; relies on existing feature values and attribution outputs  
**Testing**: pytest for Python; integration tests for partial explanations, policy filtering, and determinism  
**Target Platform**: Web application (frontend + backend)  
**Project Type**: Web app (frontend + backend)  
**Performance Goals**: p95 < 1.5 s cached estimate, p95 < 3.5 s uncached; explanation load target p95 < 2 s when cached  
**Constraints**: Vanilla stack only; acceptance tests required  
**Scale/Scope**: Top-N factor explanations with map context

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Code quality: lint/format clean, modular structure, no unjustified complexity
- [x] Testing: acceptance tests mapped to `Acceptance Tests/UC-15-AT.md` plus unit/integration
- [x] UX consistency: shared styles/components used, labels/validation consistent
- [x] Performance: budgets met or explicit waiver documented
- [x] Traceability: all work mapped to UC-15 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/015-top-contributing-factors/
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
│   │   └── top_contributing_factors.py
│   ├── services/
│   │   ├── explainability.py
│   │   └── policy_filter.py
│   └── models/
│       └── explanation.py
└── tests/
    ├── integration/
    └── unit/

frontend/
├── src/
│   ├── components/
│   │   ├── explanation-panel.js
│   │   └── factor-item.js
│   ├── pages/
│   │   └── estimate.html
│   ├── services/
│   │   └── explainability-api.js
│   └── styles/
│       └── base.css
└── tests/
    ├── integration/
    └── unit/
```

**Structure Decision**: Web application split into backend explainability and frontend explanation panel with map context.

## Complexity Tracking

No constitution violations identified in this plan.
