# Data Model: Fall Back to Straight-Line Distance When Routing Fails

**Date**: 2026-03-11
**Spec**: `specs/027-straight-line-fallback/spec.md`

## Overview

The model captures distance requests, routing results, fallback indicators, and logs for routing outages.

## Entities

### DistanceRequest

- `request_id` (string, required)
- `property_coordinates` (object, required)
- `target_coordinates` (array, required)
- `routing_enabled` (bool, required)

### DistanceResult

- `distance_values` (array, required)
- `distance_mode` (enum: `road`, `straight_line`, `mixed`)
- `fallback_used` (bool, required)
- `fallback_reason` (string, optional)

### FallbackLog

- `correlation_id` (string, required)
- `routing_error` (string, required)
- `fallback_used` (bool, required)
- `timestamp` (datetime, required)

## Notes

- Mixed mode indicates a combination of road and straight-line distances.
- Fallback logs include routing failure causes and correlation IDs.
