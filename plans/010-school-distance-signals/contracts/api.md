# API Contract: School Distance Signals

## Endpoint
`POST /api/compute-school-distance`

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
    "nearest_elementary_distance": 1.2,
    "nearest_secondary_distance": 2.4,
    "average_distance_top_n": 3.1,
    "distance_method": "routing",
    "sentinel_value_used": false
  },
  "family_suitability": 0.7
}
```

## Response (Fallback Distance)
```json
{
  "status": "success",
  "metrics": {
    "nearest_elementary_distance": 1.5,
    "nearest_secondary_distance": 2.8,
    "average_distance_top_n": 3.5,
    "distance_method": "euclidean",
    "sentinel_value_used": false
  },
  "family_suitability": 0.65,
  "fallback_used": true
}
```

## Response (No Schools)
```json
{
  "status": "success",
  "metrics": {
    "nearest_elementary_distance": 9999,
    "nearest_secondary_distance": 9999,
    "average_distance_top_n": 9999,
    "distance_method": "routing",
    "sentinel_value_used": true
  },
  "family_suitability": 0.1
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
