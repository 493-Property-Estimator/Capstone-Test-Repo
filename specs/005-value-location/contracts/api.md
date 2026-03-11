# API Contract: Location-Only Estimate

## Endpoint
`POST /api/estimate-location-only`

## Request
```json
{
  "input_type": "address",
  "address": "123 Main St, City, Region",
  "coordinates": null
}
```

### Request Rules
- `input_type` is required and must be one of `address`, `coordinates`, `map_click`.
- No additional attributes (size, bedrooms, bathrooms) may be provided.

## Response (Success)
```json
{
  "status": "success",
  "estimate": {
    "estimate": 450000,
    "range": { "low": 420000, "high": 480000 },
    "location_only_indicator": "Location-only estimate",
    "reduced_accuracy_warning": null
  }
}
```

## Response (Fallback Success)
```json
{
  "status": "success",
  "estimate": {
    "estimate": 450000,
    "range": { "low": 410000, "high": 490000 },
    "location_only_indicator": "Location-only estimate",
    "reduced_accuracy_warning": "Fallback spatial averages used; accuracy reduced."
  }
}
```

## Response (Normalization Error)
```json
{
  "status": "normalization_error",
  "error_message": "Location could not be processed."
}
```

## Response (Insufficient Data)
```json
{
  "status": "insufficient_data",
  "error_message": "Estimate cannot be generated due to insufficient data."
}
```
