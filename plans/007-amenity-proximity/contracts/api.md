# API Contract: Amenity Proximity Features

## Endpoint
`POST /api/compute-amenity-proximity`

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
    "nearest_school_distance": 1.2,
    "parks_within_radius": 3,
    "nearest_hospital_distance": 2.4,
    "distance_method": "routing"
  },
  "desirability_score": 0.72
}
```

## Response (Fallback Distance)
```json
{
  "status": "success",
  "metrics": {
    "nearest_school_distance": 1.5,
    "parks_within_radius": 3,
    "nearest_hospital_distance": 2.8,
    "distance_method": "euclidean"
  },
  "desirability_score": 0.70,
  "fallback_used": true
}
```

## Response (No Amenities)
```json
{
  "status": "success",
  "metrics": {
    "nearest_school_distance": 9999,
    "parks_within_radius": 0,
    "nearest_hospital_distance": 9999,
    "distance_method": "routing"
  },
  "desirability_score": 0.40
}
```

## Response (Coordinate Unresolved)
```json
{
  "status": "coordinate_unresolved",
  "error_message": "Coordinates could not be resolved for canonical location."
}
```
