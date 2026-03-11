# API Contract: Top Contributing Factors

## Endpoint
`POST /api/explain-estimate`

## Request
```json
{
  "estimate_id": "est-123",
  "top_n": 3
}
```

## Response (Success)
```json
{
  "status": "success",
  "increases": [
    {"label": "Proximity to schools", "measured_value": "0.8 km", "impact_direction": "increase", "impact_magnitude": 12000, "impact_format": "currency", "has_map_context": true}
  ],
  "decreases": [
    {"label": "Crime rate", "measured_value": "High", "impact_direction": "decrease", "impact_magnitude": 8000, "impact_format": "currency", "has_map_context": false}
  ],
  "qualitative": false
}
```

## Response (Qualitative)
```json
{
  "status": "qualitative_only",
  "qualitative": true,
  "increases": [
    {"label": "Amenities", "impact_direction": "increase", "impact_format": "normalized"}
  ],
  "decreases": [],
  "limitation_note": "Numeric attribution unavailable for this request."
}
```

## Response (Unavailable)
```json
{
  "status": "unavailable",
  "error_message": "Explanation unavailable. Please retry."
}
```
