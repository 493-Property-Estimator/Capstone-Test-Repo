# API Contract: Travel Accessibility Features

## Endpoint
`POST /api/compute-travel-accessibility`

## Request
```json
{
  "canonical_location_id": "canon-xyz",
  "destinations": [
    {"destination_id": "school-1", "category": "school", "coordinates": {"latitude": 40.1, "longitude": -75.1}}
  ]
}
```

## Response (Success)
```json
{
  "status": "success",
  "metrics": {
    "nearest_travel_time": 12.5,
    "average_travel_time": 18.3,
    "distance_method": "routing",
    "sentinel_value_used": false
  }
}
```

## Response (Fallback Distance)
```json
{
  "status": "success",
  "metrics": {
    "nearest_travel_time": 15.0,
    "average_travel_time": 20.0,
    "distance_method": "euclidean",
    "sentinel_value_used": false
  },
  "fallback_used": true
}
```

## Response (Unreachable Routes)
```json
{
  "status": "success",
  "metrics": {
    "nearest_travel_time": 9999,
    "average_travel_time": 9999,
    "distance_method": "routing",
    "sentinel_value_used": true
  }
}
```

## Response (Coordinate Unresolved)
```json
{
  "status": "coordinate_unresolved",
  "error_message": "Coordinates could not be resolved for canonical location."
}
```
