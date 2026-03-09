# UC-28 -- Fully Dressed Scenario Narratives

**Use Case:** Provide Partial Results When Some Open Data is Unavailable

------------------------------------------------------------------------

## Main Success Scenario Narrative -- One Dataset Temporarily Unavailable

A user selects a property at "5432 111 Avenue NW, Edmonton, AB" on the map and clicks "Get Property Estimate".

The Estimate API receives the request and validates  it successfully. It resolves the address to canonical location (53.556, -113.498) using the Location Resolver.

The Estimate API retrieves the baseline tax assessment value from the Feature Store. The query returns successfully: baseline value is $415,000 for this property.

The Estimate API now attempts to retrieve all relevant open-data features needed for the valuation computation. It sends parallel queries to the Feature Store for:
- Crime statistics for the census tract
- Green space coverage within 500m radius
- School locations and proximity data
- Store locations and accessibility
- Comparable property sales (recent 6 months)
- Transit accessibility metrics
- Neighborhood demographic indicators

The Feature Store processes these queries. Most queries return successfully:
- Green space: 12% coverage, retrieved successfully
- Schools: 3 schools within 2 km, retrieved successfully
- Stores: 8 retail locations within 1.5 km, retrieved successfully
- Comparable sales: 15 recent sales, retrieved successfully
- Transit accessibility: LRT station 1.2 km away, retrieved successfully
- Neighborhood demographics: median income $78K, retrieved successfully

However, the crime statistics query fails. The Feature Store returns an error: "Crime dataset currently unavailable - data refresh in progress. Estimated completion: 15 minutes."

The system detects that one dataset (crime statistics) is unavailable. It classifies crime statistics as an "optional" factor (not critical like the baseline assessment).

The Valuation Engine identifies which factors can be computed: baseline assessment is available, and 6 of 7 supporting factors are available (only crime is missing).

The Valuation Engine proceeds to compute the estimate using the available factors:
- Baseline: $415,000
- Green space proximity: +$8,000 (good coverage)
- School proximity: +$18,000 (3 excellent schools nearby)
- Store accessibility: +$6,000 (good retail access)
- Comparable sales: +$12,000 (recent sales trending up)
- Transit access: +$5,000 (LRT proximity)
- Neighborhood demographics: +$7,000 (desirable area)

Final estimated value: $471,000

The Valuation Engine computes a completeness score: 13 of 14 total factors computed = 93% complete.

The confidence score is calculated as 82% (High) based on having most factors available. The missing crime factor would typically contribute ±$5,000-$10,000, so the estimate is still reliable.

The Estimate API assembles the response including:
```json
{
  "baselineValue": 415000,
  "estimatedValue": 471000,
  "adjustments": {
    "greenSpace": 8000,
    "schools": 18000,
    "stores": 6000,
    "comparables": 12000,
    "transit": 5000,
    "demographics": 7000
  },
  "confidence": 82,
  "completeness": "PARTIAL",
  "missingFactors": ["crime_statistics"],
  "warnings": [
    {
      "type": "DATASET_UNAVAILABLE",
      "message": "Crime statistics temporarily unavailable. Estimate computed without crime adjustment.",
      "severity": "MEDIUM"
    }
  ]
}
```

The UI displays the estimate $471,000 with a warning about the missing crime factor. The user receives a usable estimate despite the temporary data unavailability.

------------------------------------------------------------------------

## Alternative Path 5a -- Critical Dataset Missing (Baseline)

A user requests an estimate for a property in a newly annexed area where baseline assessment data is not yet available.

The user selects a property at coordinates (53.382, -113.715) near the rural boundary. The Estimate API resolves the location successfully.

The Estimate API attempts to retrieve the baseline tax assessment value. The Feature Store queries the assessment database but finds no baseline record for this location.

The Feature Store returns: "No baseline assessment value found for parcel at (53.382, -113.715). This property may be outside the current assessment coverage area."

The Estimate API receives the baseline retrieval failure. It evaluates whether the baseline is critical or optional. Per the system design, the baseline assessment is CRITICAL - all estimates must be anchored to the baseline.

Without a baseline, the Valuation Engine cannot compute a final estimated value. The computation cannot proceed.

The Estimate API returns HTTP 424 Failed Dependency:
```json
{
  "error": "BASELINE_REQUIRED",
  "message": "Cannot compute estimate: baseline tax assessment value not available for this location",
  "location": {"lat": 53.382, "lon": -113.715},
  "region": "Rural area - may be outside assessment coverage",
  "suggestion": "This service requires baseline assessment data from the municipal tax assessment database. This property may be outside the current coverage area."
}
```

The user sees a clear message explaining that an estimate cannot be computed for this property due to missing critical baseline data.

------------------------------------------------------------------------

## Alternative Path 5b --  Crime Dataset Unavailable

(This scenario is similar to the main success scenario above where crime data is unavailable. The system proceeds with partial results.)

A user requests an estimate and the crime dataset is unavailable due to a database maintenance window.

The Estimate API proceeds with computing the estimate without crime statistics. The system omits the crime adjustment factor.

The response includes: `"missingFactors": ["crime_statistics"]` and a warning: "Crime statistics unavailable. Typically affects property value by ±$5,000 to ±$10,000 depending on area safety."

The confidence score is reduced from 85% to 78% to account for the missing crime factor. The estimate is still returned successfully with HTTP 200.

------------------------------------------------------------------------

## Alternative Path 5c -- Comparable Property Dataset Unavailable

A user requests an estimate when the comparable property sales dataset is unavailable, significantly reducing estimate accuracy.

The Estimate API retrieves baseline ($390,000) and most supporting factors successfully. However, when querying for comparable sales, the Feature Store returns an error: "Comparable sales dataset unavailable due to data source maintenance."

Comparable sales are a significant factor in the valuation model, typically accounting for ±$15,000 to ±$30,000 adjustment based on recent market trends.

Without comparable sales data, the Valuation Engine can still produce an estimate but it will have very low confidence because recent market conditions cannot be assessed.

The Valuation Engine computes an estimate using only baseline and basic features (schools, parks, walkability). Final estimate: $402,000 with confidence score of 45% (Low).

The Estimate API returns HTTP 200 with the estimate but includes prominent warnings:
```json
{
  "baselineValue": 390000,
  "estimatedValue": 402000,
  "confidence": 45,
  "completeness": "PARTIAL",
  "missingFactors": ["comparable_sales", "market_trends"],
  "warnings": [
    {
      "type": "LOW_CONFIDENCE",
      "severity": "HIGH",
      "message": "Comparable property sales data unavailable. Estimate is low confidence andshould be used for rough comparison only. Market conditions and recent trends could not be assessed."
    }
  ]
}
```

The UI displays the estimate with a prominent warning banner indicating very low confidence due to missing market data.

------------------------------------------------------------------------

## Alternative Path 6a -- Too Many Factors Missing (Below Minimum Threshold)

A user requests an estimate for a rural property where many datasets have no coverage.

The Estimate API retrieves baseline ($285,000) successfully but encounters widespread data unavailability:
- Crime statistics: No coverage in rural area
- Schools: No schools within 10 km (search radius exceeded)
- Stores: Only 1 small store, insufficient for meaningful factor
- Comparable sales: Only 1 sale in past year (need minimum 5 for statistical validity)
- Transit: No public transit in rural areas
- Demographics: Very sparse census data

The Valuation Engine checks the completeness threshold: only 3 of 13 factors could be computed (23% complete). The configured minimum threshold is 40% completeness for producing reliable estimates.

The system determines the estimate would not be reliable with only 23% of factors available.

The Estimate API could return the estimate with HTTP 200 and warnings, or return HTTP 206 Partial Content to explicitly indicate the result is incomplete.

Response includes:
```json
{
  "baselineValue": 285000,
  "estimatedValue": 291000,
  "confidence": 25,
  "completeness": "INSUFFICIENT",
  "missingFactors": ["crime", "schools", "stores", "comparables", "transit", "demographics"],
  "warnings": [
    {
      "type": "INSUFFICIENT_DATA",
      "severity": "CRITICAL",
      "message": "Very limited data available (23% complete). Estimate reliability is very low. Consider this a rough approximation only."
    }
  ]
}
```

The UI shows the estimate but with strong warnings about unreliability due to insufficient data coverage.

------------------------------------------------------------------------

## Alternative Path 4a -- Data Source Timeout with Retry

A user requests an estimate when one open-data source is experiencing slow response times.

The Estimate API sends queries to the Feature Store. Most queries return within 100-200ms. However, the green space coverage query to the GIS database takes over 4 seconds without responding.

The query exceeds the configured timeout of 3 seconds. The system first attempts one automatic retry.

The retry is sent, and this time the green space query responds successfully after 1.5 seconds, returning green space coverage of 18%.

The Valuation Engine receives all factors including the retried green space data. The estimate is computed normally with full confidence.

If the retry had also failed, the system would have proceeded without the green space factor and marked it as unavailable, similar to the main success scenario.

------------------------------------------------------------------------

## Alternative Path 7a -- Strict Mode Requested

A developer API client includes a parameter `"strictMode": true` indicating that all factors must be available or the request should fail rather than returning partial results.

The Estimate API processes the request and detects that crime statistics are unavailable.

The system checks the strictMode parameter and sees it is set to true.

Rather than proceeding with partial results, the system honors the strict mode requirement.

The Estimate API returns HTTP 424 Failed Dependency:
```json
{
  "error": "STRICT_MODE_REQUIREMENT_NOT_MET",
  "message": "Strict mode enabled: all required datasets must be available. Crime statistics dataset is currently unavailable.",
  "missingDatasets": ["crime_statistics"],
  "suggestion": "Disable strict mode to receive partial results, or wait for data refresh to complete (estimated 10 minutes)."
}
```

The developer's application is explicitly told that the strict requirements cannot be met, and the estimate is not returned.
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-28, one or more services exceed predefined latency
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

The actor attempts to perform UC-28 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-28, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
