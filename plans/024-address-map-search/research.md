# Research: Search by Address in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/024-address-map-search/spec.md`

## Goals

- Define autocomplete behavior and debounce thresholds.
- Clarify ambiguity handling and out-of-coverage behavior.
- Ensure geocoding failure handling is user-friendly.

## Findings

- Autocomplete suggestions must be ranked and show full address with city.
- Ambiguous resolution must present candidate choices (no auto-select).
- Out-of-coverage searches show warning and keep map unchanged.
- Geocoding outages must show a retryable failure message.

## Open Questions

- What debounce interval is used for autocomplete?
- What coverage polygon defines supported regions?
- What is the expected maximum suggestions count?

## Decisions (initial)

- Show loading state for suggestion fetch latency.
- Keep map unchanged on no-result or out-of-coverage outcomes.
- Log geocoding outages for monitoring.
