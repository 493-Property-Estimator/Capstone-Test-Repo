# API Contract: Neighbourhood Indicators

## Endpoint
`POST /api/compute-neighbourhood-indicators`

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
  "boundary": {"boundary_id": "b-123", "boundary_name": "District 7"},
  "indicators": {"median_income": 65000, "crime_index": 0.2},
  "profile_score": 0.7
}
```

## Response (Fallback Used)
```json
{
  "status": "fallback_used",
  "boundary": {"boundary_id": "b-123"},
  "indicators": {"median_income": 60000},
  "profile_score": 0.65,
  "fallback_used": true
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
