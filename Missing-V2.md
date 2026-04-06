# Missing Requirements Review (V2)

This file tracks requirements that remain open after re-checking the current `src/` implementation against the specs and correcting frontend issues that were previously listed here.

## Frontend items corrected in the current implementation

The following frontend-related claims from earlier reviews are no longer accurate:

- Ambiguous address candidate selection no longer stores the raw synthetic `cand_<id>` value as the canonical location identifier. The frontend now normalizes candidate IDs before storing them.
- Property-detail refinement is no longer “UI-only.” The frontend sends bedrooms, bathrooms, and floor area in the estimate request, and the backend normalizes `floor_area_sqft` into estimator-compatible attributes.
- Estimate-response presentation is no longer limited to the single point estimate. The frontend now renders baseline metadata, estimate timestamp, top positive/negative factors, cache status, missing factors, approximations, and property-detail incorporation metadata.
- The estimate form now includes env-driven criteria controls for optional output/tuning parameters. Users can choose requested factor families and weighting sliders for safety, schools, green space, and commute priorities. These values are sent in the request payload as optional API parameters.

These corrected frontend pieces primarily affect specs `006-property-details-estimate`, `013-single-value-estimate`, `015-top-contributing-factors`, `016-assessment-baseline`, `023-property-estimate-api`, `024-address-map-search`, and `026-missing-data-warnings`.

## Remaining open items

The remaining gaps are predominantly backend or platform concerns rather than frontend inadequacies.

### 1) Canonical location normalization is still incomplete in backend flows

**Specs affected**: `001-user-geocode`, `002-user-coords`, `003-user-map`, `004-input-location`, `024-address-map-search`

- Coordinate-only estimate requests can succeed, but there is still no explicit backend normalization flow that always produces a stable canonical ID with the parcel/grid fallback semantics described in spec `004`.
- The frontend can now consume canonical IDs correctly when they are returned, but the backend still owns the incomplete normalization behavior.

### 2) Estimate API contract gaps remain around auth and unsupported inputs

**Specs affected**: `023-property-estimate-api`, `032-invalid-input-errors`

- No authentication/authorization enforcement is active on `/api/v1/estimates`.
- Polygon/property-ID support remains only partial compared with the full spec.
- Some structured corrective guidance is present, but the backend still does not fully satisfy all invalid-input and unsupported-input requirements.

### 3) Optional factor families are still not fully implemented end-to-end

**Specs affected**: `007-amenity-proximity`, `008-travel-accessibility`, `009-green-space-coverage`, `010-school-distance-signals`, `011-commute-accessibility`, `012-neighbourhood-indicators`

- The frontend can now request factor families and present richer estimate diagnostics, but several of the underlying datasets/calculations are still backend-estimator gaps.
- Crime, richer green-space metrics, employment-center commute outputs, and fuller neighbourhood indicators remain incomplete or partial in the active backend/estimator path.

### 4) Refresh orchestration and monitoring remain partial

**Specs affected**: `022-schedule-refresh-jobs`, `031-health-service-metrics`

- Refresh orchestration is still workflow/CLI driven rather than continuously scheduled in-app.
- Health/metrics coverage is still narrower than the full monitoring specification.

### 5) Grid precompute remains narrower than spec scope

**Specs affected**: `030-precompute-grid-features`

- Precompute support exists, but the active implementation still does not cover the broader cell-level aggregate families and observability/retry semantics described by the specification.

## Summary

At this point, the notable frontend user-story gaps from the earlier review have been addressed. The remaining issues in this file should be treated as backend, estimator, data-pipeline, or observability work rather than missing frontend functionality.
