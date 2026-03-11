# Research: UC-05 Location-Only Estimate Planning

## Decision: Fixed minimum widening rule for location-only ranges
**Rationale**: Clarification and FR-01-083 require a minimum widening rule for all location-only estimates, and ranges must be at least as wide as comparable standard-input estimates.
**Alternatives considered**: Dynamic widening based solely on variance; no minimum widening (rejected).

## Decision: Fallback averaging hierarchy grid → neighbourhood
**Rationale**: Clarification and FR-01-143 require grid-level averages first, then neighbourhood if grid is unavailable.
**Alternatives considered**: Neighbourhood first; nearest parcel (rejected).

## Decision: Location-only indicator always shown, reduced-accuracy warning only on fallback
**Rationale**: FR-01-090 and FR-01-098 require a location-only indicator for all successful responses, with additional warning only when fallback data is used.
**Alternatives considered**: Always showing reduced-accuracy warning; only showing indicator on fallback (rejected).
