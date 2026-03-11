# API Contract: Single Estimated Value

## Endpoint
`POST /api/estimate`

## Request
```json
{
  "location": {"address": "123 Main St"},
  "attributes": {"size_sqft": 1800}
}
```

## Response (Success)
```json
{
  "status": "success",
  "estimated_value": 525000,
  "currency": "USD",
  "rounding_rule": "nearest_100",
  "timestamp": "2026-03-10T12:00:00Z",
  "location_summary": "123 Main St, City, Region",
  "baseline_metadata": {"assessment_year": "2024", "source": "assessment", "fallback_used": false},
  "warnings": [],
  "request_id": "req-123"
}
```

## Response (Validation Error)
```json
{
  "status": "validation_error",
  "validation_errors": ["address is required"],
  "request_id": "req-123"
}
```

## Response (Normalization Error)
```json
{
  "status": "normalization_error",
  "error_message": "Location could not be processed.",
  "request_id": "req-123"
}
```

## Response (Valuation Error)
```json
{
  "status": "valuation_error",
  "error_message": "Estimate could not be produced.",
  "request_id": "req-123"
}
```
