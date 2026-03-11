# Implementation Plan: Compute Distance-to-School Signals for Family Suitability

**Branch**: `010-school-distance-signals` | **Date**: 2026-03-10 | **Spec**: `/home/ayra/ECE_493/Capstone-Test-Repo/specs/010-school-distance-signals/spec.md`
**Input**: Feature specification from `/specs/010-school-distance-signals/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement school distance signals: resolve property coordinates, query all schools within shared radius, compute distances per configured method with Euclidean fallback, derive school metrics for elementary and secondary groupings, compute family suitability via thresholds/weights (default on missing config), and attach outputs to the feature set. Omit features when coordinates cannot be resolved and ensure determinism across repeated runs.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only); spatial DB and routing services accessed via internal adapters  
**Storage**: No new persistent storage for this feature; relies on existing school datasets  
**Testing**: pytest for Python; integration tests for routing fallback and no-schools cases  
**Target Platform**: Backend valuation service  
**Project Type**: Backend feature computation module  
**Performance Goals**: p95 < 1.5 s cached estimate, p95 < 3.5 s uncached; feature computation must not regress SLA  
**Constraints**: Vanilla stack only; acceptance tests required  
**Scale/Scope**: School distance metrics and family suitability signals

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Code quality: lint/format clean, modular structure, no unjustified complexity
- [x] Testing: acceptance tests mapped to `Acceptance Tests/UC-10-AT.md` plus unit/integration
- [x] UX consistency: shared styles/components used, labels/validation consistent
- [x] Performance: budgets met or explicit waiver documented
- [x] Traceability: all work mapped to UC-10 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/010-school-distance-signals/
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
│   │   └── school_distance_signals.py
│   ├── services/
│   │   ├── school_distance.py
│   │   ├── routing.py
│   │   └── suitability.py
│   └── models/
│       └── features.py
└── tests/
    ├── integration/
    └── unit/
```

**Structure Decision**: Backend-only feature computation module attached to valuation pipeline.

## Complexity Tracking

No constitution violations identified in this plan.
