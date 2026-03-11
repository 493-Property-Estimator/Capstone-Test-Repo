# API Contract: Green Space Coverage Features

## Endpoint
`POST /api/compute-green-space-coverage`

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
  "green_space_area": {
    "area": 12000,
    "coverage_percent": 25.5
  },
  "desirability_indicator": 0.68
}
```

## Response (No Green Space)
```json
{
  "status": "success",
  "green_space_area": {
    "area": 0,
    "coverage_percent": 0
  },
  "desirability_indicator": 0.10
}
```

## Response (Fallback Used)
```json
{
  "status": "fallback_used",
  "green_space_area": {
    "area": 8000,
    "coverage_percent": 16
  },
  "desirability_indicator": 0.50,
  "fallback_used": true
}
```

## Response (Geometry Unresolved)
```json
{
  "status": "geometry_unresolved",
  "absence_marked": true,
  "error_message": "Geometry could not be resolved for canonical location."
}
```
