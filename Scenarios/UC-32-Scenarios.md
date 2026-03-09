# UC-32 -- Fully Dressed Scenario Narratives

**Use Case:** Provide Clear Error Messages for Invalid Inputs

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Invalid Input Returns Clear Structured Error

A developer is integrating the Property Value Estimator API into a mobile application. They submit a test request with an incomplete payload to see how the API handles validation errors.

The developer sends a POST request to `/estimate`:
```json
POST https://api.propertyvalueestimator.ca/estimate
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "propertyType": "residential",
  "address": {
    "street": "10234 98 Street NW"
  }
}
```

The Estimate API receives the request and parses the JSON payload successfully (valid JSON structure).

The API identifies the request type as "address-based estimate" based on the presence of the `address` field.

The API performs schema validation against the address input requirements:
- `street`: Present ✓
- `city`: **Missing** ✗ (required field)
- `province`: **Missing** ✗ (required field)
- `postalCode`: Optional, not provided (acceptable)

The validation detects two missing required fields.

The Estimate API constructs a structured error response:
```json
HTTP 422 Unprocessable Entity
Content-Type: application/json

{
  "error": "validation_failed",
  "message": "Request validation failed. 2 errors found.",
  "timestamp": "2026-02-11T15:47:23Z",
  "request_id": "req_9f3e7a2c",
  "errors": [
    {
      "field": "address.city",
      "code": "required_field_missing",
      "message": "City is required for address-based estimation",
      "provided": null,
      "expected": "String (e.g., 'Edmonton', 'Calgary')"
    },
    {
      "field": "address.province",
      "code": "required_field_missing",
      "message": "Province/territory code is required",
      "provided": null,
      "expected": "Two-letter province code (e.g., 'AB', 'BC', 'ON')"
    }
  ],
  "documentation": "https://docs.propertyvalueestimator.ca/api/estimate#address-format"
}
```

The API returns HTTP 422 (Unprocessable Entity) with the detailed error response.

The developer receives the response and examines the structured errors. Each error clearly identifies:
- The specific field that failed validation
- The error code for programmatic handling
- A human-readable explanation
- What was provided (null) vs. what was expected
- A link to documentation for further details

The developer corrects the request by adding the missing fields:
```json
{
  "propertyType": "residential",
  "address": {
    "street": "10234 98 Street NW",
    "city": "Edmonton",
    "province": "AB"
  }
}
```

The developer resubmits the corrected request. This time validation passes and the API returns a successful estimate with HTTP 200.

The developer successfully integrated the API with proper error handling, thanks to the clear error messages.

------------------------------------------------------------------------

## Alternative Path 4a -- Multiple Validation Errors Across Different Fields

A developer sends a request with multiple validation issues in a single payload.

The request contains:
```json
{
  "propertyType": "residential",
  "coordinates": {
    "lat": 91.5,
    "lng": -200.0
  },
  "factorWeights": {
    "schools": 1.5,
    "parks": -0.2,
    "crime": 0.3
  }
}
```

The Estimate API validates the request and detects multiple errors:

1. **Latitude out of range**: 91.5° is invalid (valid range: -90 to 90)
2. **Longitude out of range**: -200.0° is invalid (valid range: -180 to 180)
3. **Factor weight exceeds maximum**: schools weight of 1.5 exceeds max of 1.0
4. **Negative factor weight**: parks weight of -0.2 is negative (not allowed)

Rather than failing on the first error and forcing the developer to fix issues one at a time, the API returns **all validation errors** in a single response:

```json
HTTP 422 Unprocessable Entity

{
  "error": "validation_failed",
  "message": "Request validation failed. 4 errors found.",
  "errors": [
    {
      "field": "coordinates.lat",
      "code": "value_out_of_range",
      "message": "Latitude must be between -90 and 90 degrees",
      "provided": 91.5,
      "expected": "Number in range [-90, 90]",
      "severity": "error"
    },
    {
      "field": "coordinates.lng",
      "code": "value_out_of_range",
      "message": "Longitude must be between -180 and 180 degrees",
      "provided": -200.0,
      "expected": "Number in range [-180, 180]",
      "severity": "error"
    },
    {
      "field": "factorWeights.schools",
      "code": "value_exceeds_maximum",
      "message": "Factor weight cannot exceed 1.0",
      "provided": 1.5,
      "expected": "Number in range [0, 1.0]",
      "severity": "error"
    },
    {
      "field": "factorWeights.parks",
      "code": "value_below_minimum",
      "message": "Factor weight cannot be negative",
      "provided": -0.2,
      "expected": "Number in range [0, 1.0]",
      "severity": "error"
    }
  ]
}
```

Errors are ordered by severity (all "error" level in this case, but warnings would appear after errors if present).

The developer can now fix all four issues in one iteration instead of discovering them sequentially.

------------------------------------------------------------------------

## Alternative Path 4b -- Invalid Geo-Shape (Self-Intersecting Polygon)

A developer attempting to estimate value for a custom property boundary submits a self-intersecting polygon.

The request:
```json
{
  "propertyType": "residential",
  "geoShape": {
    "type": "Polygon",
    "coordinates": [[
      [-113.490, 53.540],
      [-113.485, 53.540],
      [-113.485, 53.545],
      [-113.495, 53.542],
      [-113.490, 53.540]
    ]]
  }
}
```

The polygon is self-intersecting - the boundary crosses itself, which is geometrically invalid.

The Estimate API validates the geo-shape. The geometry validation library detects the self-intersection.

The API returns a detailed error explaining the polygon validity requirements:
```json
HTTP 422 Unprocessable Entity

{
  "error": "validation_failed",
  "message": "Invalid geo-shape provided",
  "errors": [
    {
      "field": "geoShape",
      "code": "invalid_geometry",
      "message": "Polygon is self-intersecting. Polygon boundaries must not cross themselves.",
      "details": {
        "intersection_point": [-113.490, 53.542],
        "segments": ["segment 1-2 intersects segment 3-4"]
      },
      "suggested_fix": "Ensure polygon coordinates form a simple (non-self-intersecting) closed loop. Consider using a geometry simplification tool or checking coordinate ordering.",
      "documentation": "https://docs.propertyvalueestimator.ca/api/geo-shape-validation"
    }
  ]
}
```

The error response includes:
- Clear explanation of what "self-intersecting" means
- The specific point where the intersection occurs
- Suggested corrective actions
- Link to documentation with examples of valid vs. invalid polygons

The developer uses a GIS tool to visualize and correct the polygon coordinates, then resubmits successfully.

------------------------------------------------------------------------

## Alternative Path 2a -- Unresolvable Address Format

A developer submits an address that cannot be geocoded or resolved.

The request:
```json
{
  "propertyType": "residential",
  "address": {
    "street": "123 Nonexistent Boulevard",
    "city": "Edmonton",
    "province": "AB"
  }
}
```

The Estimate API validates the address format (passes - all required fields present and properly formatted).

The API then attempts to geocode the address using the Geocoding Service.

The Geocoding Service searches for "123 Nonexistent Boulevard, Edmonton, AB" but finds no matching results.

The API returns an error indicating the address could not be resolved:
```json
HTTP 404 Not Found

{
  "error": "address_not_found",
  "message": "Could not resolve the provided address to a valid location",
  "address_provided": {
    "street": "123 Nonexistent Boulevard",
    "city": "Edmonton",
    "province": "AB"
  },
  "details": "No matching addresses found in geocoding database. The address may not exist, may be misspelled, or may not be in our coverage area.",
  "suggestions": [
    "Verify the street name and number are correct",
    "Check for common misspellings (e.g., 'Boulevard' vs 'Blvd')",
    "Use coordinates directly if you have them",
    "Try searching with a nearby known address"
  ],
  "alternative_formats": {
    "coordinates": "Provide 'coordinates' with 'lat' and 'lng' instead of 'address'",
    "property_id": "Use 'propertyId' if you have the municipal parcel identifier"
  }
}
```

The error is categorized as 404 Not Found (resource doesn't exist) rather than 422 Validation Error (format is wrong).

The developer checks the address with the property owner and discovers it should be "123 Nonexista**nt** Avenue" (different street type). They correct and retry successfully.

------------------------------------------------------------------------

## Alternative Path 5a -- Sensitive Information in Error Messages

A developer submits a request that fails validation. The request inadvertently includes a sensitive field (e.g., owner's name or identification number) that should not be echoed back in error messages for privacy reasons.

The request:
```json
{
  "propertyType": "residential",
  "address": {...},
  "ownerSocialInsuranceNumber": "123-456-789",
  "requestContext": {
    "userEmail": "owner@example.com"
  }
}
```

The field `ownerSocialInsuranceNumber` is not part of the API schema and fails validation.

The Estimate API detects the invalid field. However, before constructing the error response, the API checks for sensitive data patterns in the invalid field value:
- Social Insurance Numbers (SIN)
- Credit card numbers  
- Email addresses (depending on context)
- Other personally identifiable information

The API detects the SIN pattern in the field value. Rather than including the actual value in the error message, it redacts it:

```json
HTTP 422 Unprocessable Entity

{
  "error": "validation_failed",
  "errors": [
    {
      "field": "ownerSocialInsuranceNumber",
      "code": "unsupported_field",
      "message": "Field is not supported by this API",
      "provided": "[REDACTED]",
      "note": "The Property Value Estimator API does not require or accept personal identification information. Remove this field from your request."
    },
    {
      "field": "requestContext.userEmail",
      "code": "unsupported_field",
      "message": "Field is not supported by this API",
      "provided": "[REDACTED]",
      "note": "Email addresses should not be included in estimation requests"
    }
  ]
}
```

The error response clearly indicates the fields are not supported, but **redacts the actual sensitive values** to prevent accidental logging or exposure of private information.

This protects user privacy even when developers make mistakes in their API integration.

------------------------------------------------------------------------

## Alternative Path 3a -- Unsupported Request Format

A developer attempts to submit an estimate request in XML format instead of JSON, which is not supported by the API.

The developer sends:
```
POST https://api.propertyvalueestimator.ca/estimate
Content-Type: application/xml

<?xml version="1.0"?>
<estimateRequest>
  <propertyType>residential</propertyType>
  <address>
    <street>10234 98 Street NW</street>
    <city>Edmonton</city>
    <province>AB</province>
  </address>
</estimateRequest>
```

The Estimate API receives the request and checks the `Content-Type` header: `application/xml`

The API only supports `application/json`. It cannot parse the XML payload.

Rather than returning a generic "Bad Request" error, the API returns a clear explanation:
```json
HTTP 415 Unsupported Media Type

{
  "error": "unsupported_content_type",
  "message": "Request content type is not supported",
  "provided": "application/xml",
  "supported": ["application/json"],
  "details": "This API only accepts JSON-formatted requests. Please convert your request to JSON format and set Content-Type to 'application/json'.",
  "example": {
    "description": "Example of equivalent JSON request",
    "json": {
      "propertyType": "residential",
      "address": {
        "street": "10234 98 Street NW",
        "city": "Edmonton",
        "province": "AB"
      }
    }
  },
  "documentation": "https://docs.propertyvalueestimator.ca/api/request-format"
}
```

The error includes:
- HTTP 415 status (Unsupported Media Type) - semantically correct status code
- What was provided vs. what is supported
- An example showing how to format the request correctly in JSON
- Documentation link

The developer converts their integration to use JSON and successfully submits requests.
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-32, one or more services exceed predefined latency
thresholds. This may include routing services, database queries, cache
lookups, or open-data retrieval operations.

The system detects the timeout condition and applies one of the
following strategies:

1.  Use fallback computation (e.g., straight-line distance instead of
    routing).
2.  Use last-known cached dataset snapshot.
3.  Skip non-critical feature calculations.
4.  Abort request if time budget is exceeded for critical functionality.

If fallback logic is applied, the response includes an approximation or
fallback flag. If the operation cannot proceed safely, the system
returns HTTP 503 (Service Unavailable) along with a correlation ID for
debugging.

Metrics are recorded to track latency spikes and fallback usage rates.

------------------------------------------------------------------------

## Alternative Path Narrative D: Cache Inconsistency or Stale Data

When the system checks for cached results, it may detect that: - The
cache entry has expired, - The underlying dataset version has changed, -
The cache record is corrupted, - The cache service is unreachable.

If the cache entry is invalid or stale, the system discards it and
recomputes the necessary values. The updated result is stored back into
the cache with a refreshed TTL.

If the cache service itself is unavailable, the system proceeds without
caching and logs the incident for infrastructure monitoring.

------------------------------------------------------------------------

## Alternative Path Narrative E: Partial Data Coverage or Rural Region Limitations

The actor requests processing for a property located in a region with
limited data coverage (e.g., rural areas lacking crime datasets, sparse
commercial data, or incomplete amenity mapping).

The system detects coverage gaps and adjusts the valuation model or
feature output accordingly. The model excludes unavailable factors,
recalculates weights proportionally if configured to do so, and computes
a reduced-confidence estimate.

The output explicitly states which factors were excluded and why. The UI
displays contextual explanations such as "Data not available for this
region." The system does not fail unless minimum required data
thresholds are not met.

------------------------------------------------------------------------

## Alternative Path Narrative F: Security or Authorization Failure

The actor attempts to perform UC-32 without appropriate permissions or
credentials.

The system validates authentication tokens or session state and
determines that the request lacks required authorization. The system
immediately rejects the request with HTTP 401 (Unauthorized) or HTTP 403
(Forbidden), depending on the scenario.

No further processing occurs. The system logs the security event and
returns a structured error response without exposing sensitive internal
information.

------------------------------------------------------------------------

## Alternative Path Narrative G: UI Rendering or Client-Side Constraint Failure (UI-related UCs)

For UI-related use cases, the client device may encounter rendering
limitations (large datasets, slow browser performance, memory
constraints).

The system responds by: - Loading data incrementally, - Simplifying
geometric shapes, - Reducing visual density, - Displaying loading
indicators, - Providing user feedback that performance mode is active.

The system ensures that the UI remains responsive and avoids full-page
failure.

------------------------------------------------------------------------

## Alternative Path Narrative H: Excessive Missing Factors (Below Reliability Threshold)

If too many valuation factors are missing, or if confidence falls below
a defined reliability threshold, the system evaluates whether a usable
result can still be provided.

If reliability remains acceptable, the system returns a clearly labeled
"Low Confidence Estimate." If reliability falls below the minimum viable
threshold, the system returns either: - HTTP 206 Partial Content (if
applicable), - HTTP 200 with high-severity warning, - Or HTTP 424 if
computation is deemed invalid without required baseline inputs.

The user is informed transparently about reliability limitations.

------------------------------------------------------------------------

## Alternative Path Narrative I: Data Freshness Violation

During processing, the system detects that a dataset exceeds allowable
freshness limits (e.g., outdated crime statistics or expired grid
aggregation tables).

The system either: - Uses the stale dataset but marks output as using
outdated data, - Attempts to retrieve updated dataset from source, - Or
blocks processing if freshness is mandatory.

Freshness timestamps are included in the response for transparency.

------------------------------------------------------------------------

## Alternative Path Narrative J: Monitoring and Observability Failure

If monitoring or metrics export fails during execution of UC-32, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
