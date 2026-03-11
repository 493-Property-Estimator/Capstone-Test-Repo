# API Contract: Low/High Range

## Endpoint
`POST /api/estimate-range`

## Request
```json
{
  "estimate_request": {"location": {"address": "123 Main St"}}
}
```

## Response (Success)
```json
{
  "status": "success",
  "estimated_value": 525000,
  "low_estimate": 500000,
  "high_estimate": 550000,
  "range_type": "confidence_band",
  "interval_level": "90%",
  "timestamp": "2026-03-10T12:00:00Z",
  "warnings": {
    "range_unavailable": false,
    "range_adjusted": false,
    "reduced_reliability": false
  }
}
```

## Response (Range Unavailable)
```json
{
  "status": "range_unavailable",
  "estimated_value": 525000,
  "timestamp": "2026-03-10T12:00:00Z",
  "warnings": {
    "range_unavailable": true
  }
}
```

## Response (Range Adjusted)
```json
{
  "status": "success",
  "estimated_value": 525000,
  "low_estimate": 510000,
  "high_estimate": 540000,
  "range_type": "confidence_band",
  "interval_level": "90%",
  "timestamp": "2026-03-10T12:00:00Z",
  "warnings": {
    "range_adjusted": true
  }
}
```
