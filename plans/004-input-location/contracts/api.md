# API Contract: Normalize Property Input

## Endpoint
`POST /api/normalize-location`

## Request
```json
{
  "input_type": "address",
  "address": "123 Main St, City, Region",
  "coordinates": null
}
```

```json
{
  "input_type": "coordinates",
  "coordinates": { "latitude": 40.12345, "longitude": -75.12345 }
}
```

### Request Rules
- `input_type` is required and must be one of `address`, `coordinates`, `map_click`.
- For `address`, `address` must be provided.
- For `coordinates` or `map_click`, `coordinates` must be provided.

## Response (Success)
```json
{
  "status": "success",
  "canonical_location_id": {
    "canonical_id": "parcel-abc123",
    "unit_type": "parcel",
    "source_unit_id": "abc123"
  }
}
```

## Response (Geocode Error)
```json
{
  "status": "geocode_error",
  "error_code": "GEOCODE_FAILED",
  "error_message": "Normalization could not be completed due to geocoding failure."
}
```

## Response (Boundary Error)
```json
{
  "status": "boundary_error",
  "error_code": "OUTSIDE_SUPPORTED_AREA",
  "error_message": "Location is outside the supported area."
}
```

## Response (Resolution Error)
```json
{
  "status": "resolution_error",
  "error_code": "SPATIAL_UNIT_NOT_FOUND",
  "error_message": "No spatial unit could be resolved for the coordinates."
}
```

## Error Codes
- `GEOCODE_FAILED`
- `OUTSIDE_SUPPORTED_AREA`
- `SPATIAL_UNIT_NOT_FOUND`
