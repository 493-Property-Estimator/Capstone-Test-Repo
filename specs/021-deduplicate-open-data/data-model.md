# Data Model: Deduplicate open-data entities

**Date**: 2026-03-11
**Spec**: `specs/021-deduplicate-open-data/spec.md`

## Overview

The model tracks deduplication runs, candidate pairs, canonical entities, source links, QA outcomes, and publication status to ensure safe merges.

## Entities

### DeduplicationRun

- `run_id` (string, required)
- `trigger_type` (enum: `manual`, `scheduled`)
- `started_at` (datetime, required)
- `completed_at` (datetime, optional)
- `status` (enum: `running`, `failed`, `succeeded`)
- `warnings` (array, optional)

### SourceEntity

- `source_id` (string, required)
- `entity_id` (string, required)
- `canonical_category` (string, required)
- `name` (string, required)
- `geometry` (geometry, optional)
- `stable_id` (string, optional)

### MatchCandidate

- `candidate_id` (string, required)
- `run_id` (string, required)
- `entity_a_id` (string, required)
- `entity_b_id` (string, required)
- `distance_m` (float, required)
- `name_similarity` (float, required)
- `category_compatible` (bool, required)
- `stable_id_match` (bool, required)
- `confidence_score` (float, required)
- `decision` (enum: `auto_merge`, `review`, `reject`)

### CanonicalEntity

- `canonical_id` (string, required)
- `canonical_category` (string, required)
- `name` (string, required)
- `geometry` (geometry, optional)
- `source_precedence` (string, required)

### CanonicalLink

- `canonical_id` (string, required)
- `source_id` (string, required)
- `entity_id` (string, required)
- `link_reason` (string, required)

### QaResult

- `qa_id` (string, required)
- `run_id` (string, required)
- `count_reduction` (float, required)
- `overmerge_flags` (array, optional)
- `distance_violations` (int, required)

### PublicationResult

- `publication_id` (string, required)
- `run_id` (string, required)
- `status` (enum: `published`, `failed`)
- `error` (string, optional)

## Relationships

- `DeduplicationRun` -> `MatchCandidate` (1..N)
- `DeduplicationRun` -> `CanonicalEntity` (1..N)
- `CanonicalEntity` -> `CanonicalLink` (1..N)
- `DeduplicationRun` -> `QaResult` (1..1)
- `DeduplicationRun` -> `PublicationResult` (1..1)

## Notes

- Review candidates are retained for audit and rerun decisions.
- Conflicting source attributes are preserved in source records for traceability.
