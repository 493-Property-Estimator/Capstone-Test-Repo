# UI Contract: Deduplicate open-data entities

**Date**: 2026-03-11
**Spec**: `specs/021-deduplicate-open-data/spec.md`

## Views

### Deduplication Dashboard

Required elements:
- Run list with status, trigger type, entity types, and timestamps.
- QA summary: count reduction, over-merge flags, distance violations.
- Review candidate counts and rejection counts.

### Run Detail View

- Matching configuration and thresholds used for the run.
- Review list for medium-confidence candidates.
- Precedence outcomes for conflicting attributes.
- Publication status and rollback outcomes.

## Copy Requirements

- Use consistent labels: "Deduplication", "Review candidates", "Publication".
- Failure states must clarify production canonical entities remain unchanged.
