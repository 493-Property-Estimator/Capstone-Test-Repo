# Quickstart: Search by Address in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/024-address-map-search/spec.md`

## Purpose

Validate autocomplete, geocoding resolution, and error handling.

## Prerequisites

- Map UI loads with search bar.
- Autocomplete and geocoding services reachable.

## Suggested Test Flow

1. Type a partial address; verify suggestions and loading state.
2. Select a suggestion; verify map pans/zooms and marker appears.
3. Submit an ambiguous address; verify candidate list selection.
4. Submit out-of-coverage address; verify warning and map unchanged.
5. Simulate geocoding outage; verify retryable error message.

## Example Suggestion (Shape)

```json
{
  "display_text": "123 Main St, Example City",
  "rank": 1,
  "confidence": "high"
}
```
