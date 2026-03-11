# API Contract: Address Estimate

## Endpoint
`POST /api/estimate-by-address`

## Request
```json
{
  "address": "123 Main St, City, Region 12345",
  "attempt": 1,
  "session_id": "optional-session-id",
  "selected_candidate_id": "optional-provider-id"
}
```

### Request Rules
- `address` is required for first submission.
- `attempt` increments on retries; max 3 attempts (Clarifications).
- `selected_candidate_id` is required when user selects from disambiguation list.

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
  "error_code": "INVALID_ADDRESS",
  "error_message": "Address is missing street number and street name.",
  "missing_components": ["street_number", "street_name"],
  "next_step": "Please correct the address and resubmit."
}
```

## Response (Geocoding Error)
```json
{
  "status": "geocode_error",
  "error_code": "GEOCODE_NO_MATCH",
  "error_message": "Address could not be found.",
  "next_step": "Re-enter a different address.",
  "attempt": 1,
  "attempts_remaining": 2
}
```

## Response (Ambiguous Matches)
```json
{
  "status": "ambiguous",
  "candidates": [
    {
      "provider_id": "cand-1",
      "formatted_address": "123 Main St, City, Region",
      "locality": "City",
      "coordinates": { "latitude": 40.0, "longitude": -75.0 }
    }
  ],
  "next_step": "Select the correct address."
}
```

## Response (Failure)
```json
{
  "status": "failure",
  "error_code": "MAX_ATTEMPTS_EXCEEDED",
  "error_message": "Geocoding failed after 3 attempts.",
  "next_step": "Try again later or use a different address."
}
```

## Error Codes
- `INVALID_ADDRESS`
- `GEOCODE_NO_MATCH`
- `GEOCODE_UNAVAILABLE`
- `MAX_ATTEMPTS_EXCEEDED`
