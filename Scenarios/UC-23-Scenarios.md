# UC-23 -- Fully Dressed Scenario Narratives

**Use Case:** Provide Property Value Estimate API Endpoint

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Estimate via Address

A developer has integrated the Property Value Estimator API into a real estate application. The developer configures the application with API credentials and endpoint URL provided during registration.

A user of the real estate application enters the property address "10234 98 Street NW, Edmonton, Alberta T5H 2P9" into the application. The application constructs an estimate request containing the address, authentication token, and optional parameters requesting detailed factor breakdowns.

The application sends an authenticated POST request to `/estimate` with the JSON payload containing the property address. The API Gateway receives the request, validates that the payload size is within limits, applies rate limiting to ensure the developer is within quota, and forwards the request to the Estimate API.

The Authentication Service validates the API credentials and confirms the developer's application has permission to access the estimate endpoint. Validation succeeds.

The Estimate API validates the request payload format, confirming all required fields are present and the address structure contains necessary components.

The Estimate API sends the address "10234 98 Street NW, Edmonton, Alberta T5H 2P9" to the Location Resolver service. The Location Resolver successfully geocodes the address to coordinates (53.551086, -113.501847) and returns a canonical address format.

The Estimate API generates a cache key based on the canonical location and request parameters. It checks the cache for a recent matching estimate but finds no cached result for this property.

The Estimate API retrieves the baseline tax assessment value of $425,000 for the property from the Feature Store. It then retrieves available cached features including neighbourhood demographics, grid-level aggregates, and recent comparable sales.

The system identifies that road distance calculations are needed. The Distance Computation Service sends requests to the routing provider for travel distances to nearby schools, green spaces, stores, and work areas. The routing provider returns road distances: nearest elementary school 1.2 km, nearest park 0.8 km, nearest grocery store 1.5 km, downtown core 5.2 km.

The Valuation Engine computes adjustment contributions from all available factors. The baseline is $425,000. Positive adjustments of +$15,000 from proximity to parks and schools, +$8,000 from walkability score of 82, and +$12,000 from low crime index. Negative adjustments of -$5,000 from distance to downtown. The engine aggregates these using configured weighted means.

The Valuation Engine produces a final estimated price of $455,000 with adjustments totaling +$30,000 from the baseline. It generates a confidence score of 85% based on feature availability and data freshness. All required features were available.

The Estimate API assembles the response including baseline value $425,000, final estimate $455,000, factor breakdown showing each adjustment, confidence score 85%, and completeness indicator showing all factors available. The response includes metadata with request correlation ID, timestamps, and processing time of 145ms.

The Estimate API stores the result in the cache with a TTL of 1 hour for reuse of identical requests.

The Estimate API returns HTTP 200 success response with the JSON payload to the client application.

The Logging and Monitoring Service records request metrics including 145ms latency, cache miss, zero missing-data flags, and success status.

The developer's application displays the estimated value of $455,000 to the end user along with confidence indicators and factor breakdowns.

------------------------------------------------------------------------

## Alternative Path 4a -- Unauthenticated Request

A developer attempts to call the estimate API without including authentication credentials in the request header.

The developer's application constructs an estimate request for address "123 Main Street, Edmonton, Alberta" but omits the required `Authorization: Bearer <token>` header.

The application sends the POST request to `/estimate`. The API Gateway receives the request and forwards it to the Authentication Service.

The Authentication Service checks for authentication credentials and finds none present in the request.

The Authentication Service rejects the request. The Estimate API returns HTTP 401 Unauthorized with a JSON response containing error code "AUTHENTICATION_REQUIRED" and message "No authentication credentials provided. Include Authorization header with valid API token."

The system logs the rejected request including the source IP address and timestamp for security auditing purposes.

The developer's application displays an error to its user indicating the estimate could not be retrieved. The developer reviews the error response, identifies the missing authentication header, and corrects the application code to include proper credentials. The developer resubmits the request successfully.

------------------------------------------------------------------------

## Alternative Path 6a -- Insufficient Permissions

A developer has valid API credentials but the associated account lacks permission to access the estimate endpoint. The account may have been downgraded or the permission was not granted during registration.

The developer's application sends an authenticated request to `/estimate` with valid credentials.

The API Gateway receives the request. The Authentication Service validates the credentials and confirms they are authentic.

However, the Authentication Service checks the account permissions and determines that the account role does not include the "property:estimate" scope required for this endpoint.

The Estimate API returns HTTP 403 Forbidden with a JSON response containing error code "INSUFFICIENT_PERMISSIONS" and message "Your account does not have permission to access property estimates. Required scope: property:estimate. Contact support to request access."

The developer's application receives the error. The developer contacts the Property Value Estimator service provider to request the appropriate permissions. After permissions are granted, the developer can successfully call the endpoint.

------------------------------------------------------------------------

## Alternative Path 7a -- Invalid Request Payload

A developer submits a request with missing required fields and malformed geometry.

The developer's application constructs a request but accidentally omits the property reference entirely and includes an invalid coordinate value.

The application sends a POST request to `/estimate` with JSON payload:
```json
{
  "options": {
    "includeFactorBreakdown": true
  },
  "coordinates": {
    "lat": 95.0,
    "lon": -113.5
  }
}
```

The Estimate API receives the request and begins validation. It detects that latitude value 95.0 is outside the valid range of -90 to +90 degrees.

The Estimate API constructs a structured error response listing each validation failure:
```json
{
  "error": "VALIDATION_FAILED",
  "message": "Request payload validation failed",
  "fields": [
    {
      "field": "coordinates.lat",
      "error": "VALUE_OUT_OF_RANGE",
      "message": "Latitude must be between -90 and +90 degrees",
      "providedValue": 95.0,
      "suggestion": "Valid latitude for Edmonton is approximately 53.5 degrees"
    }
  ]
}
```

The Estimate API returns HTTP 400 Bad Request with this structured error payload.

The developer's application displays the validation errors. The developer corrects the coordinates to valid values and resubmits the request successfully.

------------------------------------------------------------------------

## Alternative Path 8a -- Geocoding Failure (Address Not Resolvable)

A developer submits a request with an ambiguous address that cannot be uniquely resolved.

The developer's application sends a request for address "123 Main Street, Edmonton" without specifying the province or postal code.

The Estimate API validates the request format successfully and forwards the address to the Location Resolver.

The Location Resolver searches for matches and finds 15 different properties with similar addresses across different neighborhoods in Edmonton. The resolver returns "AMBIGUOUS" status with the candidate list.

The Estimate API detects that the address cannot be uniquely resolved. It constructs a response indicating ambiguity.

The Estimate API returns HTTP 422 Unprocessable Entity with JSON response:
```json
{
  "error": "ADDRESS_AMBIGUOUS",
  "message": "Multiple properties match the provided address. Please provide more specific details such as postal code or province.",
  "candidates": [
    {"address": "123 Main Street NW, Edmonton, AB T5J 1A1", "neighborhood": "Downtown"},
    {"address": "123 Main Street SW, Edmonton, AB T6X 0P9", "neighborhood": "Riverbend"},
    "... additional candidates ..."
  ],
  "suggestion": "Include postal code or use coordinates for precise identification"
}
```

The developer's application displays the ambiguous address information to its user, asking them to provide more specific details or select from the candidate list.

------------------------------------------------------------------------

## Alternative Path 10a -- Baseline Assessment Unavailable

A developer requests an estimate for a rural property that lacks baseline tax assessment data in the system.

The developer's application sends a request with coordinates (53.123, -114.567) representing a rural property outside the main Edmonton assessment coverage area.

The Estimate API validates the request and resolves the location successfully. The system determines the property is located in a rural area.

The Estimate API attempts to retrieve the baseline tax assessment value from the Feature Store. The Feature Store searches the assessment database but no baseline value is available for this location. The query returns no baseline record.

Without a baseline assessment value, the Valuation Engine cannot compute the final estimate because the system architecture requires anchoring all estimates to the baseline.

The Estimate API determines the estimate cannot be produced. It constructs an error response indicating the missing critical dependency.

The Estimate API returns HTTP 424 Failed Dependency with JSON response:
```json
{
  "error": "BASELINE_UNAVAILABLE",
  "message": "Cannot compute estimate: baseline tax assessment value not available for this location",
  "region": "Rural area outside Edmonton city limits",
  "coordinates": {"lat": 53.123, "lon": -114.567},
  "suggestion": "This service currently covers properties within Edmonton city limits with available assessment data"
}
```

The developer's application displays a message to the user indicating the property is outside the supported coverage area.

------------------------------------------------------------------------

## Alternative Path 12a -- Routing Provider Timeout

A developer requests an estimate during a period when the external routing service is experiencing high latency.

The developer's application sends a request for a property estimate. The Estimate API processes the request normally and reaches the step where road distance calculations are needed.

The Distance Computation Service sends requests to the routing provider for travel distances to schools, parks, stores, and work centers. The routing provider is overloaded and requests begin timing out after 5 seconds with no response.

The Distance Computation Service detects the timeout condition for all routing requests. It marks road distance as unavailable and invokes the fallback strategy.

The Distance Computation Service computes straight-line Euclidean distances as fallbacks: nearest school 0.9 km straight-line, nearest park 0.6 km straight-line, nearest store 1.1 km straight-line, downtown 4.8 km straight-line.

The Distance Computation Service returns the straight-line distances to the Valuation Engine with a fallback flag indicating routing was unavailable.

The Valuation Engine proceeds with the estimate computation using straight-line distances. It applies the configured adjustments but notes that distance accuracy is reduced.

The Estimate API assembles the response with the final estimate and includes a warning indicator.

The response includes:
```json
{
  "baselineValue": 425000,
  "estimatedValue": 448000,
  "confidence": 75,
  "warnings": [
    {
      "type": "ROUTING_UNAVAILABLE",
      "message": "Road distances were approximated using straight-line calculations due to routing service timeout",
      "affectedFactors": ["school_distance", "park_distance", "store_distance", "work_distance"]
    }
  ]
}
```

The Estimate API returns HTTP 200 with the partial result and warning. The developer's application displays the estimate along with a notice that distances are approximated.

------------------------------------------------------------------------

## Alternative Path 13a -- Optional Data Sources Unavailable

A developer requests an estimate when the crime statistics dataset is temporarily unavailable due to maintenance.

The developer's application sends a request for a property estimate. The Estimate API processes the request and reaches the feature retrieval step.

The Estimate API attempts to retrieve all relevant features from the Feature Store including crime data, green space data, school data, store data, and comparable sales.

The Feature Store successfully retrieves most features but the crime statistics database is offline for scheduled maintenance. The crime data query returns an error indicating the dataset is unavailable.

The Estimate API identifies that crime statistics are an optional (not critical) factor. The system determines it can proceed without this factor.

The Valuation Engine computes the estimate using the available factors: baseline assessment, proximity to parks and schools, walkability, comparable sales, but omits the crime adjustment factor.

The Valuation Engine reduces the confidence score from 85% to 72% to account for the missing factor. It notes crime statistics in the missing-data list.

The Estimate API assembles the response including the estimate with reduced confidence and a list of omitted factors:
```json
{
  "baselineValue": 410000,
  "estimatedValue": 428000,
  "confidence": 72,
  "completeness": "PARTIAL",
  "missingFactors": ["crime_statistics"],
  "warnings": [
    {
      "type": "PARTIAL_DATA",
      "message": "Crime statistics unavailable for this region. Estimate computed without crime adjustment.",
      "impact": "MEDIUM"
    }
  ]
}
```

The Estimate API returns HTTP 200 with the partial result. The developer's application displays the estimate along with warnings about missing data factors.

------------------------------------------------------------------------

## Alternative Path 14a -- Cache Service Unavailable

A developer requests an estimate when the cache service is down.

The developer's application sends a request for a property estimate. The Estimate API generates a cache key and attempts to check the cache for existing results.

The cache service (Redis) is unavailable due to a network partition. The cache query times out after 200ms.

The Estimate API detects the cache failure. It logs a warning message "Cache service unavailable, proceeding without caching" to the monitoring system for the operations team to investigate.

Rather than failing the request, the Estimate API continues processing without using the cache. It computes the estimate normally by retrieving features and running the valuation engine.

The estimate completes successfully with all computations performed fresh. Processing time is 180ms instead of the typical 50ms for cache hits.

The Estimate API attempts to store the result in the cache for future requests, but the cache is still unavailable so the storage operation fails silently.

The Estimate API returns HTTP 200 with the complete estimate result. The developer's application receives the estimate successfully, unaware that caching was unavailable.

The monitoring system records the cache unavailability and alerts the operations team to investigate the cache service issue.

------------------------------------------------------------------------

## Alternative Path 18a -- Valuation Computation Timeout

A developer requests an estimate for a property that requires complex computation across many comparable properties, and the valuation engine exceeds its time budget.

The developer's application sends a request for an estimate. The Estimate API processes the request and invokes the Valuation Engine with all required features.

The Valuation Engine begins computing adjustments from the baseline. When processing the comparable sales factor, it identifies 250 recent sales within the comparison radius and begins complex statistical computations including outlier filtering, weighting by distance and similarity, and median price calculations.

The computations are taking longer than expected. The Valuation Engine has a configured timeout of 5 seconds to maintain API responsiveness. After 5 seconds, the computation has not completed.

The Valuation Engine detects the timeout condition and aborts the computation gracefully without completing the estimate.

The Estimate API receives the timeout error from the Valuation Engine. It generates a correlation ID "vln-timeout-7a3b9c2f" for tracking this specific request in logs.

The Estimate API returns HTTP 503 Service Unavailable with JSON response:
```json
{
  "error": "COMPUTATION_TIMEOUT",
  "message": "Property valuation computation exceeded time budget and was aborted to maintain service responsiveness",
  "correlationId": "vln-timeout-7a3b9c2f",
  "suggestion": "Please retry the request. If the issue persists, contact support with the correlation ID."
}
```

The system logs detailed metrics about the timeout including the number of comparable properties, processing time, and the specific computation step that exceeded the budget.

The developer's application receives the error and may implement retry logic to attempt the request again. The developer can also contact support with the correlation ID if timeouts persist for this property.

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

The actor attempts to perform UC-23 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-23, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
