# API Contract: Coordinate Estimate

## Endpoint
`POST /api/estimate-by-coordinates`

## Request
```json
{
  "latitude": 40.12345,
  "longitude": -75.12345
}
```

### Request Rules
- `latitude` and `longitude` are required and must be numeric to 5 decimal places.
- Boundary checks are inclusive (on-boundary accepted).

## Response (Success)
```json
{
  "status": "success",
  "canonical_location_id": "canon-xyz",
  "estimate": {
    "estimate": 450000,
    "range": { "low": 420000, "high": 480000 },
    "is_partial": false,
    "missing_data_warning": null
  }
}
```

## Response (Partial Data)
```json
{
  "status": "partial_data",
  "canonical_location_id": "canon-xyz",
  "estimate": {
    "estimate": 450000,
    "range": { "low": 420000, "high": 480000 },
    "is_partial": true,
    "missing_data_warning": "Some valuation inputs are missing. Estimate is partial."
  }
}
```

## Response (Validation Error)
```json
{
  "status": "validation_error",
  "error_code": "INVALID_COORDINATES",
  "error_message": "Coordinates must be numeric and within valid ranges.",
  "next_step": "Correct the coordinates and resubmit."
}
```

## Response (Boundary Error)
```json
{
  "status": "boundary_error",
  "error_code": "OUTSIDE_SUPPORTED_AREA",
  "error_message": "Location is outside the supported area.",
  "next_step": "Provide coordinates within the supported boundary."
}
```

## Response (Failure)
```json
{
  "status": "failure",
  "error_code": "ESTIMATE_FAILED",
  "error_message": "Estimate could not be computed.",
  "next_step": "Try again later."
}
```

## Error Codes
- `INVALID_COORDINATES`
- `OUTSIDE_SUPPORTED_AREA`
- `ESTIMATE_FAILED`
