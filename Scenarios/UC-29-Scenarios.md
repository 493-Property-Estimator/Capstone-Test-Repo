# UC-29 -- Fully Dressed Scenario Narratives

**Use Case:** Cache Frequently Requested Computations

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Cache Hit

A client application requests a property estimate for a popular property that was recently estimated by another user.

The client application sends a request to `/estimate` for property at address "10234 98 Street NW, Edmonton, AB T5H 2P9". The request includes standard factor weights and no special parameters.

The Estimate API receives the request and validates it successfully. It resolves the address to canonical location ID "EDM-PAR-2847591".

The Estimate API normalizes the request into a canonical signature by combining:
- Canonical property ID: "EDM-PAR-2847591"
- Factor configuration: default weights (schools:0.15, parks:0.10, crime:0.12, etc.)
- User parameters: none (using defaults)
- Dataset versions: baseline_v2023, crime_v20260210, schools_v20260201

The normalization produces a consistent signature regardless of input format (address vs coordinates would produce the same signature for the same property).

The Estimate API generates a cache key by hashing the canonical signature: `cache:estimate:sha256(EDM-PAR-2847591|default_weights|v2023...)` = `cache:estimate:7a3f9c2e...`

The Estimate API sends a GET request to the Cache Service (Redis) with key `cache:estimate:7a3f9c2e`.

The Cache Service finds the key exists and returns the cached estimate record:
```json
{
  "baselineValue": 425000,
  "estimatedValue": 455000,
  "confidence": 85,
  "adjustments": {...},
  "cachedAt": "2026-02-11T14:15:30Z",
  "datasetVersions": {...},
  "ttl": 3600
}
```

The Estimate API receives the cached result (cache hit). It verifies the cached result is still valid:
- TTL not expired: cached at 14:15:30, current time 14:28:45, elapsed 13 minutes < 1 hour TTL ✓
- Dataset versions match: all dataset versions in cache match current versions ✓
- Request parameters compatible: default weights match cached weights ✓

All validity checks pass. The cached result is still fresh and can be reused.

The Estimate API returns the cached estimate immediately to the client with HTTP 200. Total response time: 45ms (compared to 180ms for full computation).

The Logging Service records metrics: `cache_hit=true, response_time=45ms, property=EDM-PAR-2847591`

The client application receives the estimate quickly and displays it to the user.

------------------------------------------------------------------------

## Alternative Path 4a -- Cache Miss, Then Populate

A client application requests an estimate for a property that has not been recently cached.

The Estimate API generates a cache key and queries the Cache Service. The Cache Service returns `null` (key not found) - this is a cache miss.

The Estimate API proceeds with normal computation. It retrieves features from the Feature Store, computes distances via the Distance Service, and runs the Valuation Engine to produce the estimate.

The Valuation Engine returns the complete estimate result after 175ms of computation:
- Baseline: $390,000
- Estimated value: $418,000
- Confidence: 83%
- All factors computed successfully

The Estimate API stores the computed result in the cache before returning it to the client.

It sends a SET command to the Cache Service:
`SET cache:estimate:9f2e4d7a <estimate_json> EX 3600`

This stores the estimate with a TTL (time-to-live) of 3600 seconds (1 hour). After 1 hour, the cache entry will automatically expire.

The Cache Service confirms the entry was stored successfully.

The Estimate API returns the computed estimate to the client with HTTP 200. Total response time: 180ms.

The Logging Service records: `cache_hit=false, cache_populated=true, response_time=180ms`

When another user requests the same property within the next hour, they will experience a cache hit and receive the result in ~45ms instead of 180ms.

------------------------------------------------------------------------

## Alternative Path 6a -- Stale Cache Entry (Expired TTL)

A client requests an estimate for a property that was cached 2 hours ago. The cache TTL is 1 hour.

The Estimate API generates a cache key and queries the Cache Service. The Cache Service checks the key but finds it expired (cached at 12:30, current time 14:45, elapsed 2 hours 15 minutes > 1 hour TTL).

The Cache Service automatically removes the expired entry and returns `null` (cache miss).

The Estimate API treats this as a cache miss. It computes the estimate fresh using current data.

After computing the new estimate, the system stores it in the cache with a fresh 1-hour TTL.

The client receives the newly computed estimate with current data.

Alternatively, if the cache key still exists but the Estimate API detects that dataset versions have changed (e.g., cached estimate used crime_v20260209 but current version is crime_v20260211), the Estimate API would discard the stale cached result and recompute with updated data.

------------------------------------------------------------------------

## Alternative Path 4b -- Cache Service Unavailable

A client requests an estimate when the Redis cache service is down due to maintenance.

The Estimate API generates a cache key and attempts to query the Cache Service with a 200ms timeout.

The Cache Service is unreachable. After 200ms, the query times out with a connection error.

The Estimate API detects the cache failure. Rather than failing the entire request, it logs a warning: "Cache service unavailable, bypassing cache" and proceeds without caching.

It computes the estimate normally through the Feature Store and Valuation Engine.

The computation completes successfully in 185ms. The estimate is returned to the client with HTTP 200.

The Est API attempts to store the result in cache, but this operation also fails. The system silently continues (caching is best-effort, not critical).

The client receives their estimate successfully, unaware that caching was unavailable.

The monitoring system logs the cache unavailability and alerts the operations team: "WARN: Redis cache unavailable. Estimate requests bypassing cache. Response times may increase."

Operations team investigates and restores the cache service. Once restored, subsequent requests resume using cache normally.

------------------------------------------------------------------------

## Alternative Path 2a -- Non-Cacheable Request Parameters

A developer sends an estimate request with special parameters that should not be cached.

The client request includes `"debugMode": true` parameter, which enables verbose logging and diagnostic output. This is a development/troubleshooting mode that should not be cached.

The Estimate API receives the request and begins processing. During request normalization, it checks for non-cacheable parameters.

The system detects `debugMode=true` and marks the request as non-cacheable.

The Estimate API skips the cache lookup entirely. It computes the estimate directly with debug instrumentation enabled, producing extra diagnostic information.

The computation completes and the estimate is returned with debug metadata. The result is NOT stored in the cache because debug mode requests are non-cacheable.

Other non-cacheable scenarios include:
- `"experimentalWeights": true` (using non-standard factor weights)
- `"includeInternalMetrics": true` (including internal timing breakdowns)
- `"bypassCache": true` (explicit cache bypass flag)

This ensures cached results represent only standard production requests, not special debugging or experimental queries.

------------------------------------------------------------------------

## Alternative Path 5a -- Corrupted Cache Entry

A client requests an estimate and the cache contains corrupted data for this property.

The Estimate API queries the Cache Service and receives a cache hit. However, when parsing the cached JSON, the system encounters a parsing error - the cached data is corrupted or incomplete.

The Estimate API detects the corruption:
```
ERROR: Failed to parse cached estimate for key cache:estimate:4f7e2a9d
InvalidJSON: Expected '}', found EOF at position 428
```

Rather than returning an error to the client, the system treats the corrupted cache entry as invalid.

The Estimate API sends a DELETE command to remove the corrupted cache key: `DEL cache:estimate:4f7e2a9d`

The system then proceeds to compute the estimate fresh as if it were a cache miss.

The newly computed clean estimate is stored back in the cache, replacing the corrupted entry.

The client receives a valid estimate with slightly longer response time but successful completion.

The monitoring system logs the corruption event: "WARN: Corrupted cache entry detected and removed for property EDM-PAR-2847591. Cache key: 4f7e2a9d."

------------------------------------------------------------------------

## Alternative Path 4c -- Cache Eviction Pressure

The Property Value Estimator experiences high request volume, causing the cache to reach its maximum size limit. The cache begins evicting older entries using LRU (Least Recently Used) policy.

The cache is configured with a maximum size of 10,000 entries. During peak usage, the system is processing 500 requests per minute for diverse properties across Edmonton.

As new estimates are computed and cached, older cached entries that haven't been accessed recently are automatically evicted by Redis's LRU policy to make room.

A user requests an estimate for property A. The cache key for property A was created 45 minutes ago (within the 1-hour TTL) but hasn't been accessed since. Due to eviction pressure, this entry was removed from cache to make room for more recently used entries.

The Estimate API queries the cache and gets a cache miss (the entry was evicted). It computes the estimate fresh and attempts to store it back in cache.

The Cache Service accepts the new entry and evicts another old entry to make room.

The system functions correctly - the cache hit rate decreases during peak load (from 60% to 45%) but all requests still complete successfully. Response times increase slightly during peak load due to fewer cache hits.

The monitoring system tracks cache eviction rate: "INFO: Cache eviction rate increased to 15 evictions/minute due to high request volume. Consider increasing cache size if sustained."

This provides operational visibility into cache performance without impacting user-facing functionality.
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-29, one or more services exceed predefined latency
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

The actor attempts to perform UC-29 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-29, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
