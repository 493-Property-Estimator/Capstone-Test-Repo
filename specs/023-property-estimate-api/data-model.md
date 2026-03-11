# Data Model: Provide Property Value Estimate API Endpoint

**Date**: 2026-03-11
**Spec**: `specs/023-property-estimate-api/spec.md`

## Overview

The model covers estimate requests, resolved locations, feature sets, valuation results, cache entries, and error responses.

## Entities

### EstimateRequest

- `request_id` (string, required)
- `property_identifier` (object, required)
- `tuning_params` (object, optional)
- `requested_outputs` (array, optional)
- `received_at` (datetime, required)

### CanonicalLocation

- `location_id` (string, required)
- `geometry` (geometry, required)
- `resolution_method` (string, required)
- `ambiguity_notes` (string, optional)

### FeatureSet

- `baseline_value` (number, required)
- `features` (array, required)
- `missing_features` (array, optional)
- `distance_mode` (enum: `road`, `straight_line`, `mixed`)

### Adjustment

- `category` (string, required)
- `value` (number, required)

### EstimateResult

- `estimate_id` (string, required)
- `baseline_value` (number, required)
- `adjustments` (array of Adjustment, required)
- `final_estimate` (number, required)
- `confidence_score` (float, required)
- `warnings` (array, optional)
- `correlation_id` (string, required)
- `generated_at` (datetime, required)

### CacheEntry

- `signature` (string, required)
- `estimate_id` (string, required)
- `ttl_expires_at` (datetime, required)
- `dataset_versions` (array, required)

### ErrorResponse

- `status_code` (int, required)
- `error_code` (string, required)
- `message` (string, required)
- `details` (object, optional)
- `correlation_id` (string, required)

## Relationships

- `EstimateRequest` -> `CanonicalLocation` (1:1)
- `CanonicalLocation` -> `FeatureSet` (1:1)
- `FeatureSet` -> `EstimateResult` (1:1)
- `EstimateResult` -> `CacheEntry` (0..1)

## Notes

- Error responses are structured and include correlation IDs for traceability.
- Cache entries are invalidated by TTL and dataset version changes.
