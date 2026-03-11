# Quickstart: Provide Partial Results When Some Open Data is Unavailable

**Date**: 2026-03-11
**Spec**: `specs/028-partial-open-data-results/spec.md`

## Purpose

Validate partial-result handling, strict mode, and baseline failures.

## Prerequisites

- Baseline assessment data available.
- Open-data sources can be toggled to simulate outages.

## Suggested Test Flow

1. Disable one optional dataset; verify HTTP 200 with missing-factor warnings.
2. Disable comparables; verify very low confidence and partial estimate.
3. Trigger multiple dataset outages; verify high-severity warning with HTTP 200.
4. Disable baseline; verify HTTP 424 failure.
5. Send strict mode request with missing factor; verify HTTP 424 with missing list.

## Example Partial Response (Shape)

```json
{
  "estimated_value": 450000,
  "missing_factors": ["crime"],
  "confidence_score": 0.42,
  "completeness_score": 0.6,
  "warnings": ["crime data unavailable"]
}
```
