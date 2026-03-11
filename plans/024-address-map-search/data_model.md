# Data Model: Search by Address in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/024-address-map-search/spec.md`

## Overview

The model captures user search input, autocomplete suggestions, geocoding results, and map navigation state.

## Entities

### SearchInput

- `query` (string, required)
- `submitted_at` (datetime, required)
- `input_length` (int, required)

### Suggestion

- `suggestion_id` (string, required)
- `display_text` (string, required)
- `rank` (int, required)
- `confidence` (string, optional)

### GeocodeResult

- `canonical_address` (string, required)
- `coordinates` (object, required)
- `coverage_status` (enum: `supported`, `unsupported`)
- `candidates` (array, optional)

### MapState

- `center` (coordinates, required)
- `zoom` (number, required)
- `marker` (coordinates, optional)

## Notes

- Ambiguous geocoding results retain candidate lists for user selection.
- Out-of-coverage results keep the current map state unchanged.
