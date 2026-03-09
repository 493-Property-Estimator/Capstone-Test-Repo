# UC-27 -- Fully Dressed Scenario Narratives

**Use Case:** Fall Back to Straight-Line Distance When Routing Fails

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Routing Timeout Triggers Fallback

The Estimate API is processing a property valuation request for a property at coordinates (53.551, -113.502). The valuation computation requires distance calculations to nearby amenities.

The Distance Service receives a request to compute distances from the property to several target amenities: the nearest elementary school at (53.558, -113.495), the nearest park at (53.548, -113.508), the nearest grocery store at (53.553, -113.490), and the downtown work center at (53.544, -113.491).

The Distance Service first attempts to use road routing to compute accurate travel distances. It sends a request to the external Routing Service Provider (such as OpenRouteService or Mapbox Directions API) with the origin and four destination coordinates.

The routing provider is experiencing high load. The request to compute the route to the elementary school is processed, returning a road distance of 1.8 km. However, the subsequent requests for the other three destinations time out after exceeding the configured 3-second timeout limit.

The Distance Service detects the partial failure. Three of four routing requests failed to respond within the time limit.

The Distance Service marks road distance as unavailable for the three failed targets. It logs the routing failure: "Routing provider timeout for 3 of 4 targets. Property: (53.551, -113.502). Timestamp: 2026-02-11T14:32:18Z."

For the three failed targets, the Distance Service falls back to computing straight-line (Euclidean) distance. It applies the Haversine formula to calculate great-circle distances accounting for Earth's curvature:

- Park: sqrt((53.548-53.551)² + ((-113.508)-(-113.502))²) adjusted for latitude = 0.67 km straight-line
- Grocery store: 0.89 km straight-line  
- Downtown work center: 1.12 km straight-line

The Distance Service returns distance values to the Valuation Engine along with metadata flags:
```json
{
  "school": {"distance": 1.8, "method": "ROAD"},
  "park": {"distance": 0.67, "method": "STRAIGHT_LINE_FALLBACK"},
  "store": {"distance": 0.89, "method": "STRAIGHT_LINE_FALLBACK"},
  "work_center": {"distance": 1.12, "method": "STRAIGHT_LINE_FALLBACK"}
}
```

The Valuation Engine proceeds with the estimate computation using the mixed distance values. It applies adjustment factors based on these distances: closer amenities increase property value.

The Valuation Engine acknowledges that straight-line distances are approximations and adjusts the confidence calculation accordingly, reducing the overall confidence score from 85% to 78%.

The Estimate API includes a warning indicator in the response metadata: "Routing service unavailable, used straight-line distance approximation for 3 of 4 distance calculations."

The valuation computation completes successfully. The Logging Service records routing outage metrics including the fallback usage count (3 fallbacks) and which targets were affected.

------------------------------------------------------------------------

## Alternative Path 3a -- Partial Results from Routing Provider

The Distance Service sends routing requests for four targets. The routing provider successfully computes routes for two targets but returns errors for the other two.

The Distance Service requests road routes from property (53.551, -113.502) to four amenities. The routing provider responds with:
- School route: SUCCESS, 1.8 km road distance
- Park route: SUCCESS, 1.2 km road distance  
- Grocery store route: ERROR "NO_ROUTE_FOUND" (possibly the store is in a pedestrian-only zone)
- Work center route: ERROR "ROUTING_MATRIX_UNAVAILABLE"

The Distance Service detects the mixed success/failure response. For the two successful routes, it uses the returned road distances directly.

For the two failed routes, the Distance Service falls back to computing straight-line distances:
- Grocery store: 0.89 km straight-line
- Work center: 1.12 km straight-line

The Distance Service returns mixed-mode distance values with clear method indicators:
```json
{
  "school": {"distance": 1.8, "method": "ROAD"},
  "park": {"distance": 1.2, "method": "ROAD"},
  "store": {"distance": 0.89, "method": "STRAIGHT_LINE_FALLBACK"},
  "work_center": {"distance": 1.12, "method": "STRAIGHT_LINE_FALLBACK"}
}
```

The response metadata indicates: "Used road routing where available (school, park); used straight-line fallback for other targets (store, work center)."

The valuation proceeds with the mixed-mode distances, and confidence is adjusted moderately to account for the two approximations.

------------------------------------------------------------------------

## Alternative Path 5a -- Property Coordinates Missing or Invalid

The Distance Service receives a request to compute distances but the property coordinates are missing or invalid.

An estimate request arrives with corrupted coordinate data: property location recorded as (NULL, -113.502) where the latitude is missing.

The Distance Service attempts to compute straight-line fallback distances but cannot proceed without valid origin coordinates.

The Distance Service cannot compute any distance values, neither road routing nor straight-line fallback. It returns an error to the Estimate API: "INVALID_ORIGIN_COORDINATES - Cannot compute distances without valid property location."

The Estimate API receives the distance computation failure. Since distance-based factors are important but not critical (the baseline assessment is still valid), the Est API decides to omit distance-based adjustments rather than failing the entire estimate.

The Estimate API returns HTTP 422 Unprocessable Entity with a message:
```json
{
  "error": "INVALID_LOCATION",
  "message": "Property location coordinates are invalid or missing. Cannot compute distance-based valuation factors.",
  "providedCoordinates": {"lat": null, "lon": -113.502}
}
```

The user sees an error indicating the property location is invalid and should be corrected before an estimate can be computed.

------------------------------------------------------------------------

## Alternative Path 5b -- Target Amenity Coordinates Unavailable

The Distance Service attempts to compute distances but the target amenity dataset is missing.

The Distance Service receives a request to compute distance to nearest schools. It queries the Feature Store for school locations within a 5 km radius of the property.

The Feature Store returns an empty result set with a message: "School dataset unavailable in this region (rural area outside school location coverage)."

The Distance Service cannot compute distances to schools because no target coordinates exist. It returns a "MISSING_DATASET" error specifically for the school factor.

The Valuation Engine receives the distance service response indicating schools dataset is unavailable. It treats this as a missing factor scenario rather than a fallback scenario.

The Valuation Engine omits the school proximity factor from the valuation and reduces the confidence score to account for the missing factor.

The Estimate API response includes the missing factor in the warnings list: "School proximity data unavailable in this region" rather than a fallback indicator.

------------------------------------------------------------------------

## Alternative Path 6a -- Fallback Disabled by Configuration

The system is configured to disallow straight-line fallback for certain use cases requiring high accuracy.

The Estimate API processes a request with a parameter `"strictMode": true` indicating that only road routing should be used, with no approximations allowed.

The Distance Service sends routing requests. The routing provider times out for all targets.

The Distance Service checks the configuration and sees that fallback is disabled for strict mode requests. Rather than computing straight-line distances, it returns a failure status.

The Distance Service responds with: "ROUTING_UNAVAILABLE - Fallback disabled in strict mode configuration."

The Estimate API receives the routing failure. Because strict mode is enabled and fallback is disallowed, the Estimate API cannot complete the valuation without accurate distance data.

The Estimate API returns HTTP 503 Service Unavailable:
```json
{
  "error": "DEPENDENCY_UNAVAILABLE",
  "message": "Routing service unavailable and fallback is disabled. Cannot compute estimate without road distance data.",
  "dependency": "routing_service",
  "strictMode": true
}
```

The developer or user is informed that the estimate cannot be computed at this time due to the routing service being unavailable and the strict accuracy requirement.

------------------------------------------------------------------------

## Alternative Path 7a -- Unreasonable Straight-Line Distance

The Distance Service computes a straight-line distance that is clearly unrealistic, such as crossing a large body of water.

The property is located at (53.551, -113.502) in Edmonton. The system attempts to compute distance to a work center target that was incorrectly geocoded to (53.541, -113.802), which is actually in the middle of the North Saskatchewan River.

The Distance Service computes the straight-line distance as 0.45 km. However, it performs a sanity check against known road routing patterns.

The Distance Service queries a cached routing matrix and finds that typical road routes from this property to locations south across the river are 3-5 km due to needing to cross via bridges. A 0.45 km straight-line distance is clearly unrealistic for this geography.

The Distance Service applies a reasonableness check. The straight-line distance of 0.45 km through water is multiplied by a configurable correction factor of 3.5x (estimated detour factor for this region) to approximate actual travel: 0.45 × 3.5 = 1.58 km adjusted fallback distance.

Alternatively, if the correction factor results in an unreasonable adjustment (e.g., straight-line crossing an unbridged large lake), the Distance Service may completely exclude the factor and mark it as unreliable.

The Distance Service returns: `{"work_center": {"distance": 1.58, "method": "STRAIGHT_LINE_FALLBACK_ADJUSTED", "reliability": "LOW"}}`

The Valuation Engine receives the low-reliability indicator and may choose to reduce the weight of this factor or exclude it entirely depending on configuration, ensuring the unrealistic straight-line distance does not skew the valuation.
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-27, one or more services exceed predefined latency
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

The actor attempts to perform UC-27 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-27, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
