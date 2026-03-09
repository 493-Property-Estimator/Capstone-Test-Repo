# UC-31 -- Fully Dressed Scenario Narratives

**Use Case:** Provide Health Checks and Service Metrics

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Health Check Returns Healthy Status

The monitoring system performs a routine health check to ensure the Property Value Estimator services are operational.

A Prometheus monitoring agent sends a GET request to the health endpoint:
```
GET https://api.propertyvalueestimator.ca/health
Authorization: Bearer <monitoring_token>
```

The Backend Service receives the health check request at 14:32:15.

The Backend Service first checks its own internal status:
- API server process: Running ✓
- Thread pool: 45 active threads of 100 available (healthy) ✓
- Memory usage: 2.1 GB of 4.0 GB allocated (52%, healthy) ✓
- CPU usage: 34% average over last 1 minute (healthy) ✓

Internal checks pass. The service proceeds to check critical dependencies.

**Checking Feature Store Database:**
The service sends a lightweight query: `SELECT 1 FROM health_check_table`
Response time: 8ms, status: SUCCESS ✓

**Checking Cache Service (Redis):**
The service sends: `PING`
Response: `PONG`, response time: 3ms ✓

**Checking Routing Provider:**
The service sends a test routing request to GraphHopper for a known location pair:
Request: Route from (53.5461, -113.4938) to (53.5445, -113.4912)
Response time: 125ms, status: SUCCESS ✓

**Checking Valuation Engine:**
The service invokes a health check on the valuation computation module:
Request: Validate computation pipeline availability
Response: READY, processing capacity: 95% ✓

**Checking Open-Data Feature Sources (optional check):**
The service attempts to fetch schools layer metadata:
Request: GET /open-data/schools/metadata
Response time: 210ms, status: SUCCESS ✓

All dependency checks pass. The Backend Service assigns overall status as **Healthy**.

The Backend Service constructs the health response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-11T14:32:16Z",
  "version": "v2.3.1",
  "uptime_seconds": 432180,
  "dependencies": {
    "feature_store": {
      "status": "up",
      "latency_ms": 8,
      "last_check": "2026-02-11T14:32:16Z"
    },
    "cache_service": {
      "status": "up",
      "latency_ms": 3
    },
    "routing_provider": {
      "status": "up",
      "latency_ms": 125
    },
    "valuation_engine": {
      "status": "up",
      "capacity_pct": 95
    },
    "open_data_sources": {
      "status": "up",
      "latency_ms": 210
    }
  },
  "internal": {
    "threads_active": 45,
    "threads_max": 100,
    "memory_used_gb": 2.1,
    "memory_allocated_gb": 4.0,
    "cpu_usage_pct": 34
  }
}
```

The Backend Service returns HTTP 200 with the health response.

The Monitoring System receives the healthy status and records it. The service status dashboard shows a green indicator for the Property Value Estimator service.

The monitoring system also requests the metrics endpoint:
```
GET https://api.propertyvalueestimator.ca/metrics
```

The Backend Service returns metrics in Prometheus format:
```
# HELP property_estimator_requests_total Total number of estimate requests
# TYPE property_estimator_requests_total counter
property_estimator_requests_total{status="success"} 147823
property_estimator_requests_total{status="error"} 234

# HELP property_estimator_latency_seconds Request latency distribution
# TYPE property_estimator_latency_seconds histogram
property_estimator_latency_seconds_bucket{le="0.1"} 89234
property_estimator_latency_seconds_bucket{le="0.5"} 145123
property_estimator_latency_seconds_sum 25432.18
property_estimator_latency_seconds_count 148057

# HELP property_estimator_cache_hit_ratio Cache hit ratio
# TYPE property_estimator_cache_hit_ratio gauge
property_estimator_cache_hit_ratio 0.62

# HELP property_estimator_routing_fallback_total Routing fallback usage count
# TYPE property_estimator_routing_fallback_total counter
property_estimator_routing_fallback_total 847

# HELP property_estimator_valuation_time_seconds Valuation engine processing time
# TYPE property_estimator_valuation_time_seconds histogram
property_estimator_valuation_time_seconds_sum 8932.45
property_estimator_valuation_time_seconds_count 148057
```

The Monitoring System collects these metrics and stores them in the time-series database. Grafana dashboards visualize the metrics for the operations team.

------------------------------------------------------------------------

## Alternative Path 3a -- Feature Store Database is Down (Unhealthy)

The monitoring system performs a health check when the Feature Store database is experiencing an outage.

The Backend Service performs internal checks (all pass), then checks dependencies.

When checking the Feature Store:
```
SELECT 1 FROM health_check_table
Error: Connection timeout after 5000ms
CRITICAL: Feature Store database unreachable
```

The Feature Store check fails. This is a critical dependency - without the Feature Store, estimate requests cannot be fulfilled.

The Backend Service assigns overall status as **Unhealthy** due to critical dependency failure.

The health response includes the failure details:
```json
{
  "status": "unhealthy",
  "timestamp": "2026-02-11T09:15:42Z",
  "version": "v2.3.1",
  "dependencies": {
    "feature_store": {
      "status": "down",
      "error": "Connection timeout after 5000ms",
      "last_successful_check": "2026-02-11T09:10:35Z"
    },
    "cache_service": {"status": "up"},
    "routing_provider": {"status": "up"},
    "valuation_engine": {"status": "up"},
    "open_data_sources": {"status": "up"}
  },
  "message": "Critical dependency unavailable: Feature Store"
}
```

The Backend Service returns HTTP 503 (Service Unavailable) with the unhealthy status.

The Monitoring System receives the unhealthy status and triggers an alert:
```
ALERT: Property Value Estimator - UNHEALTHY
Critical dependency down: Feature Store database
Started: 2026-02-11 09:15:42
Severity: CRITICAL
```

The alert is sent to the on-call engineer via PagerDuty. The service status dashboard shows a red indicator.

Meanwhile, any estimate requests to the API fail with HTTP 503 errors because the Feature Store is unreachable.

The operations team investigates and restores the Feature Store database. Once restored, subsequent health checks return to healthy status and the alert auto-resolves.

------------------------------------------------------------------------

## Alternative Path 4a -- Routing Provider Down, Service Degraded

The monitoring system performs a health check when the Routing Provider (GraphHopper) is experiencing an outage.

The Backend Service checks internal status (passes), then checks dependencies.

Feature Store: ✓ UP
Cache Service: ✓ UP
Routing Provider: ✗ DOWN (connection refused)
Valuation Engine: ✓ UP
Open Data Sources: ✓ UP

The Routing Provider is down. However, this is not a critical dependency because the system can fall back to straight-line distance calculations (UC-27: routing fallback).

The Backend Service assigns overall status as **Degraded** (not fully healthy, but not completely unable to serve requests).

The health response:
```json
{
  "status": "degraded",
  "timestamp": "2026-02-11T11:42:18Z",
  "dependencies": {
    "feature_store": {"status": "up"},
    "cache_service": {"status": "up"},
    "routing_provider": {
      "status": "down",
      "error": "Connection refused",
      "impact": "Falling back to straight-line distance calculations"
    },
    "valuation_engine": {"status": "up"},
    "open_data_sources": {"status": "up"}
  },
  "message": "Non-critical dependency unavailable: Routing Provider. Service operating with reduced functionality."
}
```

The Backend Service returns HTTP 200 (service is still operational) with degraded status.

The Monitoring System triggers a warning-level alert (not critical):
```
WARN: Property Value Estimator - DEGRADED
Non-critical dependency down: Routing Provider
Fallback behavior active
Severity: WARNING
```

Estimate requests continue to succeed but use straight-line distance calculations instead of road routing. Estimate quality may be slightly reduced but service remains available.

------------------------------------------------------------------------

## Alternative Path 6a -- Metrics Storage System Unreachable

The Backend Service attempts to export metrics but the Prometheus metrics collector is temporarily unreachable.

A monitoring agent requests the `/metrics` endpoint:
```
GET https://api.propertyvalueestimator.ca/metrics
```

The Backend Service collects internal metrics from memory (request counts, latency histograms, cache hit ratios, etc.). These metrics are maintained in-memory regardless of whether the metrics collector is reachable.

The Backend Service attempts to push additional metrics to the remote Prometheus push gateway but receives a connection timeout.

Rather than failing the `/metrics` endpoint request, the Backend Service returns the locally available metrics from memory:
```
property_estimator_requests_total{status="success"} 147823
property_estimator_latency_seconds_sum 25432.18
...
```

HTTP 200 is returned with the available metrics.

However, some advanced metrics that require querying external storage (historical trends, aggregated cross-service metrics) are unavailable. These are omitted from the response.

The Monitoring System receives partial metrics and logs a warning: "Some metrics unavailable due to storage system outage."

The Backend Service's core functionality is unaffected - metrics collection is best-effort and does not impact estimate request processing.

------------------------------------------------------------------------

## Alternative Path 5a -- Health Endpoint Rate Limited

A misconfigured monitoring tool sends health check requests at an extremely high rate (100 requests per second) instead of the expected 1 request per 10 seconds.

The Backend Service detects the excessive health check rate from the monitoring client's IP address:
- Expected rate: 1 req/10s (0.1 req/s)
- Actual rate: 100 req/s (1000× normal rate)

To protect the service from being overwhelmed by health check traffic, the Backend Service applies rate limiting to the `/health` endpoint.

After the monitoring client exceeds 10 requests in a 10-second window, subsequent health check requests are rejected:
```
HTTP 429 Too Many Requests
Retry-After: 8

{
  "error": "rate_limit_exceeded",
  "message": "Health check rate limit exceeded. Maximum 10 requests per 10 seconds.",
  "retry_after_seconds": 8
}
```

The monitoring client receives HTTP 429 and backs off.

The Backend Service logs the rate limiting event: "WARN: Health endpoint rate limited for client 10.20.30.40. Rate: 100 req/s (limit: 1 req/s)"

The operations team investigates the monitoring configuration and corrects the polling interval from 10ms to 10s.

Once corrected, health checks resume at normal rate and succeed.

------------------------------------------------------------------------

## Alternative Path 8a -- Sensitive Metrics Must Be Redacted

The `/metrics` endpoint is accessed by an external monitoring partner who should not see certain internal sensitive metrics.

The metrics endpoint supports authentication-based metric filtering. When accessed with a restricted API token, sensitive metrics are redacted.

External monitoring partner requests:
```
GET https://api.propertyvalueestimator.ca/metrics
Authorization: Bearer <external_partner_token>
```

The Backend Service identifies this as an external restricted token. It returns only non-sensitive metrics:
```
# Public metrics (allowed)
property_estimator_requests_total{status="success"} 147823
property_estimator_latency_seconds_sum 25432.18

# Sensitive metrics (redacted)
# property_estimator_feature_store_query_time - REDACTED
# property_estimator_internal_cache_size - REDACTED
# property_estimator_database_connection_pool - REDACTED
```

The external partner receives operational metrics (request counts, latency) but does not see internal infrastructure metrics (database connection pools, cache sizes, etc.) that could expose architectural details.

When the internal monitoring system requests metrics with a full-access token, all metrics (including sensitive ones) are returned.

This allows controlled metric visibility for external partners while maintaining full visibility for internal operations.
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-31, one or more services exceed predefined latency
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

The actor attempts to perform UC-31 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-31, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
