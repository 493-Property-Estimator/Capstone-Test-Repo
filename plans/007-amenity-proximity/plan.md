# Implementation Plan: Compute Proximity to Amenities for Baseline Desirability

**Branch**: `007-amenity-proximity` | **Date**: 2026-03-10 | **Spec**: `/home/ayra/ECE_493/Capstone-Test-Repo/specs/007-amenity-proximity/spec.md`
**Input**: Feature specification from `/specs/007-amenity-proximity/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement amenity proximity computation: resolve coordinates from canonical location ID, query amenities within a shared radius, compute routing-based distances with Euclidean fallback, aggregate required proximity metrics, derive desirability via weighting rules (with defaults on misconfig), and attach features to the valuation feature set. Handle missing amenities, coordinate-resolution failure, and determinism requirements.

## Rerun Notes

- `/prompts:speckit.plan` rerun on 2026-03-10 to account for necessary data-model gap: determinism metadata for repeated-run consistency.

## Technical Context

**Language/Version**: Python 3.x, JavaScript (ES6+), HTML, CSS  
**Primary Dependencies**: None required (vanilla stack only); spatial DB and distance services accessed via internal adapters  
**Storage**: No new persistent storage for this feature; relies on existing POI datasets  
**Testing**: pytest for Python; integration tests for fallback distance and missing amenity paths  
**Target Platform**: Backend valuation service  
**Project Type**: Backend feature computation module  
**Performance Goals**: p95 < 1.5 s cached estimate, p95 < 3.5 s uncached; feature computation must not regress SLA  
**Constraints**: Vanilla stack only; acceptance tests required  
**Scale/Scope**: Proximity feature computation for schools, parks, hospitals

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Code quality: lint/format clean, modular structure, no unjustified complexity
- [x] Testing: acceptance tests mapped to `Acceptance Tests/UC-07-AT.md` plus unit/integration
- [x] UX consistency: shared styles/components used, labels/validation consistent
- [x] Performance: budgets met or explicit waiver documented
- [x] Traceability: all work mapped to UC-07 and scenario files

## Project Structure

### Documentation (this feature)

```text
specs/007-amenity-proximity/
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
│   ├── services/
│   │   ├── amenity_proximity.py
│   │   ├── distance.py
│   │   └── weighting.py
│   └── models/
│       └── features.py
└── tests/
    ├── integration/
    └── unit/
```

**Structure Decision**: Backend-only feature computation module attached to the valuation pipeline.

## Complexity Tracking

No constitution violations identified in this plan.
