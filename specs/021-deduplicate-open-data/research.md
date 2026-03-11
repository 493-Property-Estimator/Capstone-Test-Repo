# Research: Deduplicate open-data entities

**Date**: 2026-03-11
**Spec**: `specs/021-deduplicate-open-data/spec.md`

## Goals

- Define matching evidence and confidence thresholds for auto-merge, review, and reject.
- Clarify QA safeguards and publication rules.
- Ensure deterministic outcomes and auditability.

## Findings

- Medium-confidence candidates go to review; low-confidence candidates are rejected by default.
- Conflicting attributes are resolved using preferred source, then quality, then recency, while preserving conflicts for audit.
- QA must detect suspicious merge rates and distance violations and block publication when violated.
- Publication must be atomic to prevent partially updated canonical entities.

## Open Questions

- What are the configured confidence thresholds for auto-merge, review, and reject?
- What QA thresholds define suspicious merge rates or cluster sizes?
- What category compatibility rules are configured for merge eligibility?

## Decisions (initial)

- Store matching evidence and confidence score per candidate pair.
- Record review candidates separately from auto-merged and rejected candidates.
- Use atomic swap of canonical entities and link tables on publication.
