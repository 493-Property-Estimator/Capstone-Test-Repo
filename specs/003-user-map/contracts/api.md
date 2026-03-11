# API Contract: Map Click Estimate

## Endpoint
`POST /api/estimate-by-map-click`

## Request
```json
{
  "latitude": 40.12345,
  "longitude": -75.12345,
  "click_id": "click-123",
  "timestamp": "2026-03-10T12:00:00Z"
}
```

### Request Rules
- `latitude` and `longitude` are required and must be numeric to 5 decimal places.
- Boundary checks are inclusive (on-boundary accepted).
- `click_id` identifies the request for latest-click-wins handling.

## Response (Success)
```json
{
  "status": "success",
  "click_id": "click-123",
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
  "click_id": "click-123",
  "canonical_location_id": "canon-xyz",
  "estimate": {
    "estimate": 450000,
    "range": { "low": 420000, "high": 480000 },
    "is_partial": true,
    "missing_data_warning": "Some valuation inputs are missing. Estimate is partial."
  }
}
```

## Response (Resolution Error)
```json
{
  "status": "resolution_error",
  "click_id": "click-123",
  "error_code": "CLICK_RESOLUTION_FAILED",
  "error_message": "Location could not be determined from the click.",
  "next_step": "Click again to retry."
}
```

## Response (Boundary Error)
```json
{
  "status": "boundary_error",
  "click_id": "click-123",
  "error_code": "OUTSIDE_SUPPORTED_AREA",
  "error_message": "Location is outside the supported area.",
  "next_step": "Click a location within the supported boundary."
}
```

## Response (Canceled)
```json
{
  "status": "canceled",
  "click_id": "click-122",
  "error_code": "STALE_CLICK",
  "error_message": "A newer click was submitted.",
  "next_step": "Wait for the latest click result."
}
```

## Error Codes
- `CLICK_RESOLUTION_FAILED`
- `OUTSIDE_SUPPORTED_AREA`
- `STALE_CLICK`
