# Shared Data Fetching Specification

**Purpose**: Standardize how the backend fetches and normalizes upstream open-data sources for the Property Value Estimator.

**Audience**: Python backend developers, frontend developer consuming normalized API responses, and future contributors adding new open-data integrations.

## Source of Truth

This document is the shared source of truth for external data fetching. Feature-specific specs may describe behavior, but they SHOULD NOT redefine upstream base URLs, token handling, or raw external response handling differently from this document.

## Current External Provider

### City of Edmonton Open Data

- Provider name: `city_of_edmonton`
- Base domain: `https://data.edmonton.ca`
- Resource API pattern: `https://data.edmonton.ca/resource/{dataset_id}.json`
- View Query API pattern: `https://data.edmonton.ca/api/v3/views/{dataset_id}/query.json`
- Shared development app token: `RgTPiI7DaBpKCjcZpy4w5Bik1`
- Recommended environment variable: `CITY_OF_EDMONTON_APP_TOKEN`

## Token Handling Rules

- The Python backend SHOULD read the City of Edmonton app token from `CITY_OF_EDMONTON_APP_TOKEN`.
- If the environment variable is not set in the team development environment, the backend MAY fall back to the current shared development token `RgTPiI7DaBpKCjcZpy4w5Bik1`.
- The frontend MUST NOT call City of Edmonton APIs directly with the token.
- The frontend MUST consume only normalized backend endpoints.
- Before production deployment, the shared development token SHOULD be rotated or replaced with environment-managed secrets.

## Standard Request Patterns

### 1. Dataset Resource Request

Use this when reading dataset rows directly.

```text
GET https://data.edmonton.ca/resource/{dataset_id}.json
```

Example:

```text
GET https://data.edmonton.ca/resource/q7d6-ambg.json
```

### 2. Dataset Query Request

Use this when querying dataset views with filtering and pagination.

```text
GET https://data.edmonton.ca/api/v3/views/{dataset_id}/query.json?app_token=<token>&pageSize=<n>&pageNumber=<n>&query=<soql-like-query>
```

Examples:

```text
GET https://data.edmonton.ca/api/v3/views/qi6a-xuwt/query.json?app_token=RgTPiI7DaBpKCjcZpy4w5Bik1&pageSize=1000&pageNumber=1&query=SELECT * WHERE house_number = '1815' AND street_name LIKE 'HASWELL WAY'
```

```text
GET https://data.edmonton.ca/api/v3/views/q7d6-ambg/query.json?pageNumber=1&pageSize=1000&app_token=RgTPiI7DaBpKCjcZpy4w5Bik1&query=SELECT * WHERE `house_number`='616'
```

## Standard Backend Request Builder

The backend SHOULD centralize City of Edmonton request construction in one module or service.

Required request inputs:

- `provider`
- `dataset_id`
- `endpoint_type`
- `page_size`
- `page_number`
- `query`

Recommended Python-side config shape:

```python
CITY_OF_EDMONTON = {
    "provider": "city_of_edmonton",
    "base_url": "https://data.edmonton.ca",
    "resource_path_template": "/resource/{dataset_id}.json",
    "view_query_template": "/api/v3/views/{dataset_id}/query.json",
    "app_token": "RgTPiI7DaBpKCjcZpy4w5Bik1",
    "app_token_env": "CITY_OF_EDMONTON_APP_TOKEN",
    "default_page_size": 1000,
    "default_page_number": 1,
}
```

## Standard Upstream Response Shapes

The backend MUST support these raw upstream response styles:

### Array-of-Objects Resource Rows

```json
[
  {
    "house_number": "616",
    "street_name": "EXAMPLE ST",
    "latitude": "53.5461",
    "longitude": "-113.4938"
  }
]
```

### View Query Payload

The exact City of Edmonton view-query payload can vary by dataset, so the backend adapter MUST extract row objects from the dataset-specific result structure before normalization.

The frontend/backend contract only depends on the normalized fields below, not on the raw Socrata wrapper shape.

## Minimum Normalized Fields

The backend SHOULD normalize upstream dataset rows into these fields when available:

- `house_number`
- `street_name`
- `street_type`
- `street_direction`
- `city`
- `province`
- `postal_code`
- `lat`
- `lng`
- `name`
- `category`
- `address`
- `dataset_id`
- `record_id`

## Field Mapping Rules

| Upstream field | Normalized field |
| --- | --- |
| `house_number` | `house_number` |
| `street_name` | `street_name` |
| `street_type` | `street_type` |
| `street_direction` | `street_direction` |
| `city` | `city` |
| `postal_code` | `postal_code` |
| `latitude` | `lat` |
| `longitude` | `lng` |
| `geometry.coordinates[1]` | `lat` |
| `geometry.coordinates[0]` | `lng` |
| `name` or dataset-specific label field | `name` |

If both scalar latitude/longitude and GeoJSON geometry exist, the backend SHOULD prefer validated GeoJSON geometry.

## Normalized Address Record

```json
{
  "provider": "city_of_edmonton",
  "dataset_id": "q7d6-ambg",
  "record_id": "row-001",
  "house_number": "616",
  "street_name": "Example",
  "street_type": "St",
  "street_direction": "NW",
  "city": "Edmonton",
  "province": "AB",
  "postal_code": "T5J 0A1",
  "address": "616 Example St NW, Edmonton, AB T5J 0A1",
  "lat": 53.5461,
  "lng": -113.4938
}
```

## Normalized Layer Feature Record

```json
{
  "provider": "city_of_edmonton",
  "dataset_id": "q7d6-ambg",
  "record_id": "row-001",
  "id": "feature_001",
  "name": "Example School",
  "category": "school",
  "address": "616 Example St NW, Edmonton, AB",
  "lat": 53.5461,
  "lng": -113.4938
}
```

## Frontend Exposure Rules

- The frontend MUST receive normalized backend responses only.
- The frontend MAY receive `source_meta` and limited `source_data` for traceability.
- The frontend MUST NOT be required to parse Socrata row wrappers, query metadata wrappers, or raw City of Edmonton field naming directly.

## Contract Alignment

The normalized results defined here MUST align with:

- [`frontend_api_contract.md`](/root/Speckit-Constitution-To-Tasks/frontend_api_contract.md)
- [`specs/024-address-map-search/contracts/api.md`](/root/Speckit-Constitution-To-Tasks/specs/024-address-map-search/contracts/api.md)
- [`specs/025-open-data-layers/contracts/api.md`](/root/Speckit-Constitution-To-Tasks/specs/025-open-data-layers/contracts/api.md)
- [`specs/023-property-estimate-api/contracts/api.md`](/root/Speckit-Constitution-To-Tasks/specs/023-property-estimate-api/contracts/api.md)

## Implementation Guidance

- Put all City of Edmonton HTTP calls behind one Python service module.
- Do not hardcode dataset-specific parsing logic inside route handlers.
- Normalize upstream records before business logic uses them.
- Preserve `dataset_id`, `provider`, and `record_id` where available for debugging and traceability.
- Keep pagination configurable even when initial calls use `pageSize=1000` and `pageNumber=1`.
