# Frontend API Contract

**Purpose**: Shared frontend/backend contract for the Property Value Estimator.

**Audience**: Frontend developer implementing the HTML/JavaScript UI and backend developers implementing Python services.

**Scope**: This contract covers the frontend-facing APIs required for map click selection, address search, estimate retrieval, missing-data warnings, and OpenStreetMap layer overlays.

**Upstream Data Source Standard**: City of Edmonton open-data fetching details are standardized in [`specs/shared-data-fetching.md`](/root/Speckit-Constitution-To-Tasks/specs/shared-data-fetching.md). Backend implementations SHOULD follow that document when integrating external datasets.

## Design Rules

- All backend endpoints MUST return JSON.
- All backend routes SHOULD be exposed under `/api/v1`.
- All timestamps MUST use ISO 8601 UTC strings.
- All coordinates MUST use decimal degrees.
- All responses MUST include `request_id` for tracing.
- Backend business logic MUST remain in Python.
- Frontend MUST treat this document as the source of truth for request and response shapes.

## Standard Headers

### Required Response Headers

- `Content-Type: application/json`
- `X-Request-Id: <same value as response.request_id>`

### Optional Request Headers

- `X-Request-Id: <client-generated-id>`

## Standard Error Response

All non-2xx responses SHOULD use this shape:

```json
{
  "request_id": "9d84d344-7db4-4cc0-a6d2-c7d09f6f32d6",
  "error": {
    "code": "INVALID_QUERY",
    "message": "Search query must contain at least 3 characters.",
    "details": {
      "field": "q",
      "reason": "too_short"
    },
    "retryable": false
  }
}
```

## Shared Data Models

### Coordinate

```json
{
  "lat": 53.5461,
  "lng": -113.4938
}
```

### Bounding Box

```json
{
  "west": -113.7136,
  "south": 53.3958,
  "east": -113.2714,
  "north": 53.7160
}
```

### Location Summary

```json
{
  "canonical_location_id": "loc_edmonton_123456",
  "canonical_address": "123 Main St NW, Edmonton, AB",
  "coordinates": {
    "lat": 53.5461,
    "lng": -113.4938
  },
  "region": "Edmonton",
  "neighbourhood": "Downtown",
  "coverage_status": "supported"
}
```

### Estimate Range

```json
{
  "low": 420000,
  "high": 480000
}
```

### Factor Breakdown Item

```json
{
  "factor_id": "school_distance",
  "label": "Distance to schools",
  "value": -4500,
  "status": "available",
  "summary": "Nearby schools slightly increase value impact confidence."
}
```

Allowed `status` values:

- `available`
- `missing`
- `approximated`

### Warning Item

```json
{
  "code": "ROUTING_FALLBACK_USED",
  "severity": "warning",
  "title": "Approximate distances used",
  "message": "Routing was unavailable, so straight-line distance was used.",
  "affected_factors": ["commute_accessibility", "amenity_proximity"],
  "dismissible": true
}
```

Allowed `severity` values:

- `info`
- `warning`
- `critical`

### Confidence Summary

```json
{
  "score": 0.78,
  "percentage": 78,
  "label": "medium",
  "completeness": "partial"
}
```

Allowed `label` values:

- `high`
- `medium`
- `low`

Allowed `completeness` values:

- `complete`
- `partial`
- `approximate`

### Source Metadata

Use this when the backend needs to preserve traceable upstream dataset details for the frontend.

```json
{
  "provider": "city_of_edmonton",
  "dataset_id": "q7d6-ambg",
  "record_id": "row-001",
  "retrieved_at": "2026-03-17T19:00:00Z",
  "license": "Open Government Licence",
  "attribution": "City of Edmonton Open Data"
}
```

### Source Data Envelope

Frontend endpoints MUST return normalized fields for rendering. They MAY also include a `source_data` object with selected upstream fields that are useful for debugging, inspection, or popup details.

```json
{
  "normalized": {},
  "source_meta": {
    "provider": "city_of_edmonton",
    "dataset_id": "q7d6-ambg",
    "record_id": "row-001",
    "retrieved_at": "2026-03-17T19:00:00Z",
    "license": "Open Government Licence",
    "attribution": "City of Edmonton Open Data"
  },
  "source_data": {
    "house_number": "616",
    "street_name": "EXAMPLE ST",
    "latitude": "53.5461",
    "longitude": "-113.4938"
  }
}
```

## City of Edmonton Data Normalization

The repository references Edmonton open-data usage, and sample upstream calls provided by the team use `data.edmonton.ca` Socrata endpoints. The frontend MUST NOT depend on raw Socrata response shapes directly. The Python backend SHOULD normalize upstream records before returning them to the frontend.

### Standard Upstream Configuration

- Base domain: `https://data.edmonton.ca`
- Resource API pattern: `https://data.edmonton.ca/resource/{dataset_id}.json`
- View Query API pattern: `https://data.edmonton.ca/api/v3/views/{dataset_id}/query.json`
- Current shared app token for team development: `RgTPiI7DaBpKCjcZpy4w5Bik1`
- Recommended backend environment variable name: `CITY_OF_EDMONTON_APP_TOKEN`

The backend SHOULD read the token from configuration even if the initial team spec records the current token value for development.

### Supported Upstream Response Shapes

The backend may ingest either of these upstream formats:

- Array-of-objects dataset rows from endpoints like `/resource/<dataset>.json`
- View query payloads from endpoints like `/api/v3/views/<dataset>/query.json`

### Minimum Upstream Fields to Extract

These are the only upstream fields the shared frontend/backend contract needs to account for right now:

- `house_number`
- `street_name`
- `street_type`
- `street_direction`
- `city`
- `postal_code`
- `latitude`
- `longitude`
- `geometry`
- dataset-specific feature name fields such as `name`, `school_name`, `park_name`, or `neighbourhood`

### Normalized Address Record

When a City of Edmonton dataset is used to resolve or suggest an address, the backend SHOULD normalize it to this shape before returning it through search endpoints:

```json
{
  "address_id": "addr_001",
  "display_text": "616 Example St NW, Edmonton, AB T5J 0A1",
  "address": {
    "house_number": "616",
    "street_name": "Example",
    "street_type": "St",
    "street_direction": "NW",
    "city": "Edmonton",
    "province": "AB",
    "postal_code": "T5J 0A1"
  },
  "coordinates": {
    "lat": 53.5461,
    "lng": -113.4938
  },
  "source_meta": {
    "provider": "city_of_edmonton",
    "dataset_id": "q7d6-ambg",
    "record_id": "row-001",
    "retrieved_at": "2026-03-17T19:00:00Z",
    "license": "Open Government Licence",
    "attribution": "City of Edmonton Open Data"
  }
}
```

### Normalized Map Layer Feature Properties

When the backend transforms City of Edmonton datasets into GeoJSON for map layers, each feature's `properties` object SHOULD use this minimum common structure:

```json
{
  "id": "feature_001",
  "name": "Example Feature",
  "category": "school",
  "address": "616 Example St NW, Edmonton, AB",
  "description": "Optional short label for map popup",
  "source_meta": {
    "provider": "city_of_edmonton",
    "dataset_id": "q7d6-ambg",
    "record_id": "row-001",
    "retrieved_at": "2026-03-17T19:00:00Z",
    "license": "Open Government Licence",
    "attribution": "City of Edmonton Open Data"
  },
  "source_data": {
    "house_number": "616",
    "street_name": "EXAMPLE ST"
  }
}
```

### City of Edmonton Field Mapping Guidance

The backend SHOULD map upstream fields as follows when present:

| Upstream field | Normalized field |
| --- | --- |
| `house_number` | `address.house_number` |
| `street_name` | `address.street_name` |
| `street_type` | `address.street_type` |
| `street_direction` | `address.street_direction` |
| `postal_code` | `address.postal_code` |
| `latitude` | `coordinates.lat` |
| `longitude` | `coordinates.lng` |
| `geometry.coordinates` | `coordinates.lng`, `coordinates.lat` |
| `name` or dataset-specific label field | `name` or `display_text` |

If both scalar lat/lng fields and GeoJSON geometry are present, the backend SHOULD prefer validated geometry coordinates and use scalar fields as fallback.

## 1. Address Autocomplete

Used while the user types into the search bar.

### Endpoint

`GET /api/v1/search/suggestions?q=<query>&limit=<n>`

### Query Parameters

- `q` required string, minimum 3 characters
- `limit` optional integer, default `5`, maximum `10`

### Success Response `200 OK`

```json
{
  "request_id": "f2aa92f3-c740-4e65-a24d-8f2f0e2d9df3",
  "query": "123 main",
  "suggestions": [
    {
      "id": "sug_001",
      "display_text": "123 Main St NW, Edmonton, AB",
      "secondary_text": "Downtown",
      "rank": 1,
      "confidence": "high",
      "source_meta": {
        "provider": "city_of_edmonton",
        "dataset_id": "q7d6-ambg",
        "record_id": "row-001",
        "retrieved_at": "2026-03-17T19:00:00Z",
        "license": "Open Government Licence",
        "attribution": "City of Edmonton Open Data"
      }
    }
  ]
}
```

### Error Statuses

- `400` invalid or too-short query
- `503` search service unavailable

## 2. Address Resolution

Used when the user selects a suggestion or submits a full address.

### Endpoint

`GET /api/v1/search/resolve?q=<full-address>`

### Success Response: Exact Supported Match `200 OK`

```json
{
  "request_id": "3189af1d-9d88-4771-a79d-af5b1d6226d7",
  "status": "resolved",
  "location": {
    "canonical_location_id": "loc_edmonton_123456",
    "canonical_address": "123 Main St NW, Edmonton, AB",
    "coordinates": {
      "lat": 53.5461,
      "lng": -113.4938
    },
    "region": "Edmonton",
    "neighbourhood": "Downtown",
    "coverage_status": "supported"
  },
  "candidates": []
}
```

### Success Response: Ambiguous Match `200 OK`

```json
{
  "request_id": "3189af1d-9d88-4771-a79d-af5b1d6226d7",
  "status": "ambiguous",
  "location": null,
  "candidates": [
    {
      "candidate_id": "cand_001",
      "display_text": "123 Main St NW, Edmonton, AB",
      "coordinates": {
        "lat": 53.5461,
        "lng": -113.4938
      },
      "coverage_status": "supported",
      "source_meta": {
        "provider": "city_of_edmonton",
        "dataset_id": "q7d6-ambg",
        "record_id": "row-001",
        "retrieved_at": "2026-03-17T19:00:00Z",
        "license": "Open Government Licence",
        "attribution": "City of Edmonton Open Data"
      }
    },
    {
      "candidate_id": "cand_002",
      "display_text": "123 Main St SE, Edmonton, AB",
      "coordinates": {
        "lat": 53.5252,
        "lng": -113.4901
      },
      "coverage_status": "supported"
    }
  ]
}
```

### Success Response: Unsupported Region `200 OK`

```json
{
  "request_id": "3189af1d-9d88-4771-a79d-af5b1d6226d7",
  "status": "unsupported_region",
  "location": {
    "canonical_location_id": null,
    "canonical_address": "12 Example Rd, Outside Region",
    "coordinates": {
      "lat": 54.001,
      "lng": -114.002
    },
    "region": "Outside Coverage",
    "neighbourhood": null,
    "coverage_status": "unsupported"
  },
  "candidates": []
}
```

### Success Response: No Match `200 OK`

```json
{
  "request_id": "3189af1d-9d88-4771-a79d-af5b1d6226d7",
  "status": "not_found",
  "location": null,
  "candidates": []
}
```

### Error Statuses

- `400` invalid query
- `503` geocoding service unavailable

## 3. Map Click Location Resolution

Used when the user clicks directly on the OpenStreetMap map.

### Endpoint

`POST /api/v1/locations/resolve-click`

### Request Body

```json
{
  "click_id": "click-123",
  "coordinates": {
    "lat": 53.54612,
    "lng": -113.49377
  },
  "timestamp": "2026-03-17T19:00:00Z"
}
```

### Request Rules

- `click_id` is required and is used for latest-click-wins handling.
- Coordinates are required.
- Boundary checks are inclusive.
- Backend SHOULD preserve 5 decimal places or better.

### Success Response: Resolved `200 OK`

```json
{
  "request_id": "8fcfbb3d-1361-46d5-a350-acd7d2f1d6c0",
  "status": "resolved",
  "click_id": "click-123",
  "location": {
    "canonical_location_id": "loc_edmonton_123456",
    "canonical_address": "123 Main St NW, Edmonton, AB",
    "coordinates": {
      "lat": 53.54612,
      "lng": -113.49377
    },
    "region": "Edmonton",
    "neighbourhood": "Downtown",
    "coverage_status": "supported"
  }
}
```

### Success Response: Outside Coverage `200 OK`

```json
{
  "request_id": "8fcfbb3d-1361-46d5-a350-acd7d2f1d6c0",
  "status": "outside_supported_area",
  "click_id": "click-123",
  "location": null,
  "error": {
    "code": "OUTSIDE_SUPPORTED_AREA",
    "message": "Location is outside the supported area.",
    "details": {},
    "retryable": false
  }
}
```

### Success Response: Resolution Failure `200 OK`

```json
{
  "request_id": "8fcfbb3d-1361-46d5-a350-acd7d2f1d6c0",
  "status": "resolution_error",
  "click_id": "click-123",
  "location": null,
  "error": {
    "code": "CLICK_RESOLUTION_FAILED",
    "message": "Location could not be determined from the click.",
    "details": {},
    "retryable": true
  }
}
```

## 4. Property Estimate

Used after the user selects a location by address, suggestion, or map click.

### Endpoint

`POST /api/v1/estimates`

### Request Body

At least one location selector MUST be provided.

```json
{
  "location": {
    "canonical_location_id": "loc_edmonton_123456",
    "coordinates": {
      "lat": 53.54612,
      "lng": -113.49377
    },
    "address": "123 Main St NW, Edmonton, AB"
  },
  "property_details": {
    "bedrooms": 3,
    "bathrooms": 2,
    "floor_area_sqft": 1450
  },
  "options": {
    "include_breakdown": true,
    "include_warnings": true,
    "include_layers_context": false
  }
}
```

### Success Response: Full Estimate `200 OK`

```json
{
  "request_id": "152ed8ee-1f98-4258-b0ca-1d2a4aa0bd5f",
  "estimate_id": "est_001",
  "status": "ok",
  "location": {
    "canonical_location_id": "loc_edmonton_123456",
    "canonical_address": "123 Main St NW, Edmonton, AB",
    "coordinates": {
      "lat": 53.54612,
      "lng": -113.49377
    },
    "region": "Edmonton",
    "neighbourhood": "Downtown",
    "coverage_status": "supported"
  },
  "baseline_value": 410000,
  "final_estimate": 450000,
  "range": {
    "low": 420000,
    "high": 480000
  },
  "factor_breakdown": [
    {
      "factor_id": "school_distance",
      "label": "Distance to schools",
      "value": 5200,
      "status": "available",
      "summary": "Schools within preferred distance band."
    }
  ],
  "confidence": {
    "score": 0.91,
    "percentage": 91,
    "label": "high",
    "completeness": "complete"
  },
  "warnings": [],
  "missing_factors": [],
  "approximations": []
}
```

### Success Response: Partial Estimate `200 OK`

```json
{
  "request_id": "152ed8ee-1f98-4258-b0ca-1d2a4aa0bd5f",
  "estimate_id": "est_002",
  "status": "partial",
  "location": {
    "canonical_location_id": "loc_edmonton_123456",
    "canonical_address": "123 Main St NW, Edmonton, AB",
    "coordinates": {
      "lat": 53.54612,
      "lng": -113.49377
    },
    "region": "Edmonton",
    "neighbourhood": "Downtown",
    "coverage_status": "supported"
  },
  "baseline_value": 410000,
  "final_estimate": 441000,
  "range": {
    "low": 415000,
    "high": 468000
  },
  "factor_breakdown": [
    {
      "factor_id": "crime_rate",
      "label": "Crime rate",
      "value": 0,
      "status": "missing",
      "summary": "Crime dataset unavailable for this region."
    },
    {
      "factor_id": "commute_accessibility",
      "label": "Commute accessibility",
      "value": -1200,
      "status": "approximated",
      "summary": "Straight-line distance used because routing was unavailable."
    }
  ],
  "confidence": {
    "score": 0.68,
    "percentage": 68,
    "label": "medium",
    "completeness": "partial"
  },
  "warnings": [
    {
      "code": "MISSING_DATA",
      "severity": "warning",
      "title": "Some data is missing",
      "message": "One or more valuation factors were unavailable.",
      "affected_factors": ["crime_rate"],
      "dismissible": true
    },
    {
      "code": "ROUTING_FALLBACK_USED",
      "severity": "warning",
      "title": "Approximate distances used",
      "message": "Routing was unavailable, so straight-line distance was used.",
      "affected_factors": ["commute_accessibility"],
      "dismissible": true
    }
  ],
  "missing_factors": ["crime_rate"],
  "approximations": ["commute_accessibility"]
}
```

### Error Statuses

- `400` malformed payload
- `422` invalid geometry or unresolved location
- `424` baseline value missing
- `503` estimate service unavailable

## 5. Layer Data for Map Overlays

Used for toggled overlays such as schools, parks, census boundaries, and assessment zones.

### Endpoint

`GET /api/v1/layers/{layer_id}?west=<w>&south=<s>&east=<e>&north=<n>&zoom=<z>`

### Path Parameters

- `layer_id` allowed examples:
  - `schools`
  - `parks`
  - `green_spaces`
  - `census_boundaries`
  - `assessment_zones`
  - `hospitals`

### Success Response `200 OK`

```json
{
  "request_id": "dbd4b2a3-16b1-4c6e-adbb-8bbbd24fc090",
  "layer_id": "schools",
  "status": "ok",
  "coverage_status": "complete",
  "legend": {
    "title": "Schools",
    "items": [
      {
        "label": "School",
        "color": "#1f6feb",
        "shape": "circle"
      }
    ]
  },
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-113.4938, 53.5461]
      },
      "properties": {
        "id": "school_001",
        "name": "Example School",
        "category": "public",
        "address": "616 Example St NW, Edmonton, AB",
        "description": "Public school",
        "source_meta": {
          "provider": "city_of_edmonton",
          "dataset_id": "q7d6-ambg",
          "record_id": "row-001",
          "retrieved_at": "2026-03-17T19:00:00Z",
          "license": "Open Government Licence",
          "attribution": "City of Edmonton Open Data"
        },
        "source_data": {
          "house_number": "616",
          "street_name": "EXAMPLE ST"
        }
      }
    }
  ],
  "warnings": []
}
```

### Success Response: Partial Coverage `200 OK`

```json
{
  "request_id": "dbd4b2a3-16b1-4c6e-adbb-8bbbd24fc090",
  "layer_id": "crime_heatmap",
  "status": "partial",
  "coverage_status": "partial",
  "legend": {
    "title": "Crime heatmap",
    "items": []
  },
  "features": [],
  "warnings": [
    {
      "code": "PARTIAL_COVERAGE",
      "severity": "warning",
      "title": "Incomplete layer coverage",
      "message": "This layer does not cover the full visible region.",
      "affected_factors": [],
      "dismissible": true
    }
  ]
}
```

### Error Statuses

- `400` invalid layer or bounds
- `404` unsupported layer id
- `503` layer service unavailable

## 6. Recommended Frontend JavaScript Interface

The frontend should call the backend through a thin wrapper with these methods:

```js
async function getAddressSuggestions(query, limit = 5) {}
async function resolveAddress(query) {}
async function resolveMapClick(payload) {}
async function getEstimate(payload) {}
async function getLayerData({ layerId, west, south, east, north, zoom }) {}
```

Expected usage:

```js
const api = {
  getAddressSuggestions,
  resolveAddress,
  resolveMapClick,
  getEstimate,
  getLayerData
};
```

## 7. Backend Implementation Notes

- Use stable field names exactly as shown to avoid frontend adapter churn.
- Do not mix HTML into responses.
- Use `200 OK` for supported business-state outcomes like `ambiguous`, `not_found`, `partial`, and `unsupported_region`; reserve 4xx and 5xx for transport or request failures.
- `warnings`, `missing_factors`, and `approximations` MUST always be present on estimate responses, even when empty.
- `factor_breakdown` MUST always be present when `include_breakdown` is `true`.
- `confidence.percentage` SHOULD be an integer from `0` to `100`.
- `range.low <= final_estimate <= range.high` MUST always hold.
- The frontend MUST render from normalized fields, not from raw `source_data`.
- `source_meta` SHOULD be included when backend data comes from City of Edmonton datasets or other external open-data providers.
- `source_data` SHOULD be limited to fields useful for UI display, traceability, or debugging; do not pass through full raw upstream records by default.

## 8. Minimum Endpoint Set for Backend Team

If the backend team wants the smallest viable integration target first, implement these in order:

1. `GET /api/v1/search/suggestions`
2. `GET /api/v1/search/resolve`
3. `POST /api/v1/locations/resolve-click`
4. `POST /api/v1/estimates`
5. `GET /api/v1/layers/{layer_id}`
