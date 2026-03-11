# Quickstart: Deduplicate open-data entities

**Date**: 2026-03-11
**Spec**: `specs/021-deduplicate-open-data/spec.md`

## Purpose

Validate candidate generation, confidence thresholds, QA gating, and publication.

## Prerequisites

- Multi-source entities ingested with provenance and geometry.
- Deduplication configuration set (thresholds, category compatibility rules).

## Suggested Test Flow

1. Run deduplication with overlapping sources; verify canonical entities and links.
2. Verify auto-merge, review, and reject buckets align with confidence thresholds.
3. Simulate close-but-distinct entities and confirm they are not auto-merged.
4. Simulate QA violations and confirm publication is blocked.
5. Simulate publication failure and confirm last known-good canonical entities remain.

## Example Run Metadata (Shape)

```json
{
  "run_id": "dedupe-20260311-001",
  "status": "succeeded",
  "count_reduction": 0.18,
  "review_candidates": 42,
  "rejected_candidates": 13
}
```
