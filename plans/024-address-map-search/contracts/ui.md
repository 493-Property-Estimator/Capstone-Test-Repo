# UI Contract: Search by Address in the Map UI

**Date**: 2026-03-11
**Spec**: `specs/024-address-map-search/spec.md`

## Views

### Map Search Bar

Required elements:
- Visible search bar with helper text.
- Autocomplete dropdown with ranked suggestions.
- Loading indicator while fetching suggestions.

### Search Results Handling

- Map pans/zooms to resolved coordinates with marker.
- Candidate list for ambiguous results.
- No-results message leaves map unchanged.
- Out-of-coverage warning leaves map unchanged.
- Geocoding unavailable message supports retry.

## Copy Requirements

- Use consistent labels: "Search", "Suggestions", "Region not supported".
- Error messages must be actionable and non-blocking.
