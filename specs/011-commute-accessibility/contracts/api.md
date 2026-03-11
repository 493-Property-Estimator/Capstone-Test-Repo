# API Contract: Commute Accessibility Features

## Endpoint
`POST /api/compute-commute-accessibility`

## Request
```json
{
  "canonical_location_id": "canon-xyz"
}
```

## Response (Success)
```json
{
  "status": "success",
  "metrics": {
    "nearest_travel_time": 12.5,
    "average_travel_time": 20.0,
    "weighted_accessibility_index": 0.6,
    "distance_method": "routing",
    "target_count": 5
  },
  "accessibility_indicator": 0.7
}
```

## Response (Fallback Distance)
```json
{
  "status": "success",
  "metrics": {
    "nearest_travel_time": 15.0,
    "average_travel_time": 22.0,
    "weighted_accessibility_index": 0.55,
    "distance_method": "euclidean",
    "target_count": 5
  },
  "accessibility_indicator": 0.65,
  "fallback_used": true
}
```

## Response (Empty Targets)
```json
{
  "status": "empty_targets",
  "metrics": null,
  "accessibility_indicator": 0.0,
  "target_count": 0
}
```

## Response (Coordinate Unresolved)
```json
{
  "status": "coordinate_unresolved",
  "absence_marked": true,
  "error_message": "Coordinates could not be resolved for canonical location."
}
```
