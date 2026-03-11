# API Contract: Property Details Estimate

## Endpoint
`POST /api/estimate-with-details`

## Request
```json
{
  "input_type": "address",
  "address": "123 Main St, City, Region",
  "coordinates": null,
  "attributes": {
    "size_sqft": 1800,
    "bedrooms": 3,
    "bathrooms": 2
  }
}
```

### Request Rules
- `input_type` is required and must be one of `address`, `coordinates`, `map_click`.
- `attributes` must include one or more of `size_sqft`, `bedrooms`, `bathrooms`.

## Response (Success)
```json
{
  "status": "success",
  "estimate": {
    "estimate": 525000,
    "range": { "low": 505000, "high": 545000 },
    "attributes_incorporated": ["size_sqft", "bedrooms", "bathrooms"],
    "partial_attributes_indicator": null,
    "reduced_accuracy_warning": null
  }
}
```

## Response (Partial Attributes)
```json
{
  "status": "success",
  "estimate": {
    "estimate": 500000,
    "range": { "low": 480000, "high": 520000 },
    "attributes_incorporated": ["size_sqft"],
    "partial_attributes_indicator": "Only some attributes were incorporated.",
    "reduced_accuracy_warning": null
  }
}
```

## Response (Partial Data Warning)
```json
{
  "status": "success",
  "estimate": {
    "estimate": 510000,
    "range": { "low": 490000, "high": 530000 },
    "attributes_incorporated": ["size_sqft", "bedrooms"],
    "partial_attributes_indicator": null,
    "reduced_accuracy_warning": "Some baseline or feature data was unavailable; accuracy reduced."
  }
}
```

## Response (Validation Error)
```json
{
  "status": "validation_error",
  "error_message": "Invalid attributes: size must be positive; beds/baths must be non-negative."
}
```

## Response (Normalization Error)
```json
{
  "status": "normalization_error",
  "error_message": "Location could not be processed."
}
```
