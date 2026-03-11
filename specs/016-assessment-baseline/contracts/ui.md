# UI Contract: Use assessment baseline

**Date**: 2026-03-11
**Spec**: `specs/016-assessment-baseline/spec.md`

## Views

### Estimate Result View

Required elements:
- Baseline value with provenance (year, jurisdiction/source, assessment unit ID)
- Final estimate displayed as “Baseline + adjustments” framing
- Adjustment breakdown (if provided) or an explicit label when not available
- Warning banner(s) for ambiguous match, fallback, partial features, or guardrails
- Traceability identifier (correlation/request ID)

### Warnings & States

- Ambiguous match: show deterministic selection warning and assumption note.
- Missing/stale baseline: show fallback label or explicit error state; never present as baseline-originated if fallback used.
- Partial features: show missing categories and completeness warning.
- Guardrails: show low-confidence indicator and guardrail flag.

## Copy Requirements

- Use consistent labels across screens: "Assessment baseline", "Final estimate", "Adjustments".
- Warnings must be explicit and not imply missing features had zero impact.
