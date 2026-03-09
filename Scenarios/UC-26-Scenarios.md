# UC-26 -- Fully Dressed Scenario Narratives

**Use Case:** Show Missing-Data Warnings in UI

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Display Partial Data Warnings

A user has selected a property at coordinates (53.551, -113.502) in Edmonton and clicks the "Get Estimate" button to request a property valuation.

The system sends the estimate request to the Estimate API with the property location. The Estimate API processes the request through all computation steps.

During processing, the Estimate API retrieves the baseline assessment value successfully ($410,000). It then attempts to retrieve all relevant open-data features for the valuation computation.

The system successfully retrieves most features: proximity to schools (3 schools within 2 km), green space coverage (15% within 500m radius), walkability score (78), comparable property sales (12 recent sales), and neighborhood demographics.

However, when the system attempts to retrieve crime statistics for this property's census tract, the Feature Store returns an error indicating that crime data is temporarily unavailable due to an ongoing data refresh operation.

The Valuation Engine computes the estimate using all available factors except crime statistics. It calculates a final estimated value of $445,000 based on the baseline plus positive adjustments from good school proximity (+$22,000), high walkability (+$8,000), and strong comparable sales (+$15,000).

The Valuation Engine generates a completeness score of 85% (11 of 13 factors successfully computed). It produces a confidence indicator of "Medium-High" reflecting the partial data availability.

The Estimate API assembles a response containing:
- Baseline value: $410,000
- Estimated value: $445,000
- Confidence: 75 (Medium-High)
- Completeness: "PARTIAL"
- Missing factors list: ["crime_statistics"]
- Warning metadata indicating crime data unavailable

The UI receives the estimate response. It parses the response and identifies that the missing factors list contains one entry: crime statistics.

The UI displays the main estimate prominently: "$445,000 estimated value (baseline $410,000)".

Below the estimate, the UI displays a confidence indicator using a horizontal bar graph that is 75% filled with green, labeled "Confidence: Medium-High (75%)".

The UI displays a warning panel with a yellow information icon and text: "This estimate was computed with partial data. Some factors were unavailable."

Inside the warning panel, the UI lists the missing factors:
- "Crime Statistics: Data temporarily unavailable in this region"

The UI includes an expandable "Details" section. When the user clicks "Show Details", it expands to reveal:

"Impact of Missing Data:
- Crime statistics typically adjust property values by ±$5,000 to ±$15,000 depending on area safety ratings
- Without this factor, the estimate range may be wider and less precise
- Data refresh is in progress; try again in 30 minutes for a complete estimate"

The user can see clearly that the estimate is usable but should not be considered as precise as a full-data estimate. The user can proceed with this qualified estimate or return later for a complete valuation.

------------------------------------------------------------------------

## Alternative Path 4a -- Many Factors Missing (Very Low Confidence)

A user requests an estimate for a rural property on the outskirts of Edmonton where data coverage is limited.

The user clicks on a property location at coordinates (53.385, -113.725) near the rural boundary. The user clicks "Get Estimate".

The Estimate API processes the request. It successfully retrieves the baseline assessment value ($285,000) from the tax assessment database.

However, when attempting to retrieve supporting features, the system encounters multiple unavailable datasets:
- Crime statistics: No coverage in rural areas
- School proximity: No schools within the standard 5 km search radius
- Comparable sales: Only 2 sales in past year (minimum 8 required for statistical validity)
- Transit accessibility: No public transit coverage
- Store proximity: Only 1 small convenience store within 10 km
- Green space: Satellite imagery unavailable for vegetation analysis

The Valuation Engine determines that only 3 of 13 factors are computable (baseline, basic road distance to downtown, parcel size). The completeness score is 23%, which falls below the "low confidence" threshold of 40%.

The Valuation Engine computes a very rough estimate of $292,000 with a confidence score of 25 (Very Low).

The Estimate API returns the result with a high-severity warning flag.

The UI receives the response and detects the very low confidence score. Rather than displaying a standard warning panel, it displays a prominent red warning banner across the top of the screen:

"WARNING: Very Limited Data Available"

The estimate is displayed but with reduced visual emphasis, shown in gray instead of the normal bold text: "$292,000 (estimated, very low confidence)".

The UI displays a large warning message:

"This estimate has very limited reliability due to insufficient data in this region. Many important factors could not be evaluated:
- Crime statistics (unavailable)
- School proximity (no schools in area)
- Comparable sales (insufficient data)
- Transit access (unavailable)
- Commercial proximity (limited)
- Green space analysis (unavailable)

Recommendation: This estimate should be used for rough comparison only. Consider searching properties in more central areas with better data coverage, or consult professional appraisal services for this location."

The UI includes a button "Search Nearby Properties" that would help the user find alternative properties with better data coverage.

------------------------------------------------------------------------

## Alternative Path 4b -- Minor Factors Missing (Small Confidence Reduction)

A user requests an estimate for a well-covered urban property. One minor optional factor is unavailable.

The user selects a property at "5432 111 Avenue NW, Edmonton" and requests an estimate.

The Estimate API processes the request and successfully retrieves 12 of 13 factors. The only missing factor is "Employment Center Proximity" data, which is a minor contributing factor typically accounting for only ±$2,000 adjustment.

The Valuation Engine computes the estimate using all available factors. The completeness score is 92% and confidence is 88 (High).

The Estimate API returns the result with a low-severity warning for the single minor missing factor.

The UI receives the response. Because the confidence is still high (above 85%), the UI displays the estimate prominently with normal emphasis: "$485,000 estimated value".

Rather than showing a large warning panel, the UI displays a small, non-intrusive notice using an information icon next to the confidence indicator:

"Confidence: High (88%) ⓘ"

When the user hovers over or clicks the information icon, a tooltip appears: "One minor factor unavailable: Employment center proximity data. Impact on estimate accuracy: minimal."

This approach informs the user of the limitation without causing alarm, since the estimate remains highly reliable despite the minor missing factor.

------------------------------------------------------------------------

## Alternative Path 7a -- Fallback Computation Used

A user requests an estimate during a period when the routing service is down, requiring fallback to straight-line distance calculations.

The user selects a property and requests an estimate. The Estimate API processes the request and attempts to compute road travel distances to schools, parks, stores, and work centers.

The routing service is unavailable. The Distance Computation Service falls back to computing straight-line (Euclidean) distances for all distance-based factors.

The Valuation Engine computes the estimate using straight-line distances instead of road distances. The final estimate is $438,000 with confidence 78%.

The Estimate API includes a warning flag indicating that fallback calculations were used: `"warnings": [{"type": "ROUTING_FALLBACK", "affectedFactors": ["school_distance", "park_distance", "store_distance", "work_distance"]}]`

The UI receives the response and detects the routing fallback warning. It displays the estimate with a fallback indicator:

"$438,000 estimated value"

Below the estimate, the UI displays a warning with an orange information icon:

"Routing Unavailable: Distances Approximated"

The warning message explains: "Road travel distances were approximated using straight-line calculations because routing service is temporarily unavailable. Straight-line distances may differ from actual travel distances by ±10-15%. This may affect accuracy of:
- School proximity factor
- Park proximity factor
- Store accessibility factor
- Work commute factor

The estimate confidence has been adjusted to account for the approximation."

A badge appears next to each affected factor in the detailed breakdown showing "~approx." to indicate approximation.

------------------------------------------------------------------------

## Alternative Path 7b -- Coverage Gap

A user requests an estimate for a property in a census tract where certain datasets have known coverage gaps.

The user selects a downtown property in an area undergoing rapid redevelopment. The census data for this tract is from 3 years ago and does not reflect recent demographic changes.

The Estimate API computes the estimate but notes that the neighborhood demographics data is stale (last updated 3 years ago, threshold is 2 years).

The UI displays the estimate with a note about data currency:

"$512,000 estimated value

⚠ Data Currency Notice: Neighborhood demographic data for this census tract is outdated (last updated February 2023). This area has undergone significant redevelopment since then. The demographic factors used in this estimate may not reflect current neighborhood characteristics."

------------------------------------------------------------------------

## Alternative Path 8a -- User Dismisses Warnings

A user understands the warnings but wants to proceed with using the estimate anyway.

After reviewing the estimate with partial data warnings displayed, the user clicks a "Dismiss" or close button (X) on the warning panel.

The system collapses the warning panel, but retains a small persistent warning indicator. A yellow triangle icon with an exclamation mark remains visible next to the confidence score.

The estimate remains displayed normally. The user can continue exploring the map, comparing properties, or adjusting estimate parameters.

If the user wants to see the warnings again, they can click on the warning icon, and the warning panel reopens showing the complete missing-data information.

The dismissed state is stored in browser session storage so that if the user refreshes the page, the warnings remain collapsed but the indicator persists.

------------------------------------------------------------------------

## Alternative Path 5a -- Malformed API Response

A user requests an estimate, but the Estimate API returns a response with incomplete or malformed missing-data metadata.

The UI receives an estimate response where the metadata section is malformed or missing the expected completeness fields. The JSON might be missing the `missingFactors` array or have an unexpected structure.

The UI's error handling detects the malformed metadata. Rather than failing completely, it displays a generic cautionary message:

"Some data may be missing. $445,000 estimated value"

Below this, the UI shows: "Data quality information unavailable. Use this estimate with caution."

The system logs the malformed response error to the monitoring system with the full response payload for debugging:

`ERROR: Estimate response metadata malformed for property (53.551, -113.502). Missing 'missingFactors' field. Falling back to generic warning.`

This ensures the user still receives the estimate and a general warning, while the development team can investigate the metadata issue.
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-26, one or more services exceed predefined latency
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

The actor attempts to perform UC-26 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-26, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
