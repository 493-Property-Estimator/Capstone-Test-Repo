# Research: Use assessment baseline

**Date**: 2026-03-11
**Spec**: `specs/016-assessment-baseline/spec.md`

## Goals

- Confirm how assessment baselines are keyed to locations (parcel ID, address, nearest parcel).
- Define deterministic selection and disclosure for ambiguous matches.
- Clarify fallback policy for missing/stale baselines.
- Ensure explainability: baseline provenance, adjustment breakdown, traceability IDs.

## Findings

- Baseline provenance must include assessment year, jurisdiction/source, and assessment unit identifier.
- Deterministic selection is required for ambiguous matches, with explicit disclosure.
- Fallback or failure must be policy-driven and surfaced to the user with a reliability warning.
- Guardrails that cap adjustments must be surfaced as low-confidence flags.

## Open Questions

- What baseline freshness threshold defines “stale”?
- What fallback hierarchy is acceptable (nearest parcel, neighbourhood baseline, none)?
- What rounding rules apply for consistency checks in the breakdown?

## Decisions (initial)

- Use a deterministic rule (e.g., closest centroid) for ambiguous matches and store the selection rationale.
- Provide a structured warning list in API responses; UI renders these warnings verbatim with user-friendly labels.
- Include correlation/request identifiers in successful responses for traceability.
