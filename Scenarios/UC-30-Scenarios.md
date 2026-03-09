# UC-30 -- Fully Dressed Scenario Narratives

**Use Case:** Precompute Grid-Level Features

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Scheduled Batch Job Runs Successfully

The Property Value Estimator runs a nightly scheduled job to precompute aggregated features at a grid level, improving estimate performance.

At 02:00 AM (low-traffic period), the Scheduler (Apache Airflow) triggers the `precompute_grid_features` job. The job is configured to run daily and process the entire Edmonton coverage area.

The Data Pipeline receives the trigger and begins execution. It logs the job start: "Job precompute_grid_features started at 2026-02-11 02:00:15 AM"

The Data Pipeline first loads the latest source datasets:
- Baseline Tax Assessment Data: 147,523 properties (v2026-02-10)
- Crime Data: incidents from last 12 months (v2026-02-09)
- Open Data Layers: parks (245 features), schools (418 features), stores (3,241 features)
- Internal Feature Store: existing property features

All datasets load successfully.

The Data Pipeline retrieves the grid configuration from settings:
- Grid resolution: 500m × 500m cells
- Coverage area: Edmonton city boundary
- Total grid cells: 2,847 cells covering the city

The Data Pipeline divides Edmonton into the 2,847 predefined grid cells. Each cell is identified by its bounding box coordinates.

For each grid cell, the Data Pipeline aggregates features from properties and amenities within that cell:

**Example: Grid Cell C-247 (bounding box: 53.5423°N to 53.5468°N, -113.4987°W to -113.4912°W)**

The pipeline identifies:
- 52 properties in this cell from baseline assessment data
- 3 parks within or intersecting cell boundary
- 7 schools within 1km of cell center
- 14 stores within cell
- 8 crime incidents in last 12 months within cell

The pipeline computes aggregated statistics:
```json
{
  "grid_id": "C-247",
  "bounds": {...},
  "property_stats": {
    "count": 52,
    "mean_baseline_value": 412000,
    "median_baseline_value": 395000,
    "std_dev": 87000
  },
  "amenity_density": {
    "parks_count": 3,
    "schools_count": 7,
    "stores_count": 14,
    "green_space_area_m2": 45000
  },
  "walkability_proxy": 72,
  "crime_stats": {
    "incident_count_12mo": 8,
    "crime_rate_per_1000": 2.4,
    "severity_index": 1.8
  },
  "school_proximity_avg_m": 450
}
```

The pipeline repeats this aggregation for all 2,847 cells. Processing takes approximately 18 minutes.

The Data Pipeline performs sanity checks on aggregated results:
- Check for missing values: All cells have at least property count ✓
- Check for unreasonable outliers: No negative values, no extreme outliers beyond 3 standard deviations ✓
- Check coverage: All grid cells within city boundary have data ✓

All sanity checks pass.

The Data Pipeline writes the aggregated features into the Feature Store database table `grid_features_v2`:
```sql
INSERT INTO grid_features_v2 (grid_id, bounds, property_stats, amenity_density, ...)
VALUES ('C-247', ...), ('C-248', ...), ... (2,847 rows)
```

The write completes successfully, updating all 2,847 grid cells.

The Data Pipeline records metadata:
```json
{
  "job_id": "precompute_20260211_0200",
  "completed_at": "2026-02-11T02:18:47Z",
  "source_versions": {
    "baseline": "v2026-02-10",
    "crime": "v2026-02-09",
    "parks": "v2026-02-08",
    "schools": "v2026-02-05",
    "stores": "v2026-02-10"
  },
  "grid_count": 2847,
  "processing_time_seconds": 1092
}
```

The Data Pipeline marks the job as successful and outputs metrics:
- Total cells processed: 2,847
- Total properties aggregated: 147,523
- Processing time: 18 minutes 12 seconds
- Success rate: 100%

The Monitoring Service records the job completion.

When the Estimate API processes requests later that day, it uses the fresh grid-level features from `grid_features_v2`. Instead of computing neighborhood statistics on-demand for each request, the API retrieves precomputed aggregates from the nearest grid cell, reducing computation time from ~80ms to ~5ms per estimate.

------------------------------------------------------------------------

## Alternative Path 2a -- Open-Data Source Unavailable During Job Run

The scheduled precomputation job starts at 02:00 AM. During execution, one of the open-data sources (crime statistics API) is unavailable due to maintenance.

The Data Pipeline loads source datasets. When attempting to fetch the crime data:
```
GET https://data.edmonton.ca/api/crime_incidents?from=2025-02-11
Response: 503 Service Unavailable
```

The Data Pipeline detects the crime data source failure. It checks for the last known dataset snapshot.

The system finds a snapshot from 2 days ago: crime data v2026-02-09 (current attempt is for v2026-02-11).

The Data Pipeline logs: "WARN: Crime data source unavailable. Using last known snapshot v2026-02-09 (2 days old)."

The pipeline proceeds with the slightly stale crime data snapshot. It aggregates features for all grid cells using:
- Fresh baseline assessment data (v2026-02-10)
- 2-day-old crime data (v2026-02-09)
- Fresh open data layers (parks, schools, stores from v2026-02-10)

The aggregation completes successfully. The metadata records the mixed dataset versions:
```json
{
  "source_versions": {
    "baseline": "v2026-02-10",
    "crime": "v2026-02-09 (snapshot, source unavailable)",
    ...
  }
}
```

Grid features are updated with mostly fresh data. Crime statistics are slightly stale but functional.

The job completes successfully. The Monitoring Service notes the crime data staleness for operational awareness.

------------------------------------------------------------------------

## Alternative Path 4a -- Aggregation Computation Fails for Some Cells

During grid-level feature computation, the pipeline encounters an error processing one specific grid cell.

The Data Pipeline is processing Grid Cell D-892 (a cell near the city boundary with sparse data). When computing the walkability proxy, it encounters a division-by-zero error because the cell contains zero stores.

```python
walkability = (stores_count * 0.4 + parks_area * 0.3 + ...) / total_area
# Error: stores_count = 0, calculation results in invalid value
```

The Data Pipeline catches the error and logs: "ERROR: Failed to compute walkability for grid cell D-892: division by zero"

Rather than failing the entire job, the system marks this specific cell with a partial result:
```json
{
  "grid_id": "D-892",
  "property_stats": {...computed successfully...},
  "amenity_density": {...computed successfully...},
  "walkability_proxy": null,
  "computation_status": "partial",
  "errors": ["walkability_computation_failed"]
}
```

The pipeline continues processing remaining grid cells (2,846 cells complete successfully, 1 cell partial).

At job completion, the Data Pipeline reports:
- Success: 2,846 cells
- Partial: 1 cell (D-892)
- Total: 2,847 cells

The job is marked as "completed with warnings" rather than "failed". Grid features are updated for all cells, with one cell missing the walkability metric.

When the Estimate API uses Grid Cell D-892 later, it detects `walkability_proxy: null` and falls back to computing walkability on-demand for that specific property instead of using the precomputed value.

------------------------------------------------------------------------

## Alternative Path 5a -- Sanity Check Detects Data Quality Issues

The precomputation job completes aggregation but detects anomalies during sanity checks.

After aggregating all 2,847 grid cells, the Data Pipeline performs validation. During outlier detection, it finds Grid Cell F-341 has suspicious values:
- Mean baseline value: $12,500,000 (vs. city-wide median of $390,000)
- This is 32× higher than the city average - likely erroneous data

The sanity check fails: "FAIL: Grid cell F-341 has mean_baseline_value outlier: $12,500,000 exceeds threshold (>10× city median)"

The Data Pipeline investigates. It finds one property in cell F-341 with an erroneous baseline assessment value of $650,000,000 (likely a data entry error - should be $650,000).

The system has two options:
1. Reject the entire grid cell F-341 and mark it as failed
2. Apply outlier filtering and recompute

The Data Pipeline applies outlier filtering. It removes the anomalous $650M property from the aggregation and recomputes cell F-341 statistics:
- Mean baseline value (filtered): $425,000 ✓
- Now within normal range

The sanity check passes after filtering.

The Data Pipeline logs the data quality issue:
```json
{
  "data_quality_issue": {
    "grid_id": "F-341",
    "property_id": "EDM-PAR-3829471",
    "issue": "baseline_value_extreme_outlier",
    "original_value": 650000000,
    "action": "excluded_from_aggregation"
  }
}
```

The grid features are written to the database with the cleaned data. A report is generated for the maintainer to investigate and correct the source data error.

------------------------------------------------------------------------

## Alternative Path 6a -- Database Write Failure

The precomputation job completes aggregation successfully but fails to write results to the database.

After computing all 2,847 grid cell aggregates, the Data Pipeline attempts to write to the Feature Store database.

The write operation attempts:
```sql
BEGIN TRANSACTION;
INSERT INTO grid_features_v2 (grid_id, bounds, ...) VALUES ...;
```

The database returns an error:
```
Error: Deadlock detected. Transaction aborted.
Current active connections: 42
Lock wait timeout exceeded
```

The Feature Store database is experiencing high load from concurrent read operations. The write transaction times out.

The Data Pipeline retries the write operation after a 5-second delay.

The second attempt succeeds - the competing transactions have completed.

The grid features are successfully written to the database.

The Data Pipeline logs: "WARN: Database write failed on first attempt (deadlock). Retry succeeded after 5s."

The job completes successfully with a slightly longer duration (18 minutes 17 seconds instead of 18 minutes 12 seconds).

Alternatively, if the retry also fails, the Data Pipeline would log an error and mark the job as failed. The stale grid features from the previous day would remain in the database. The Estimate API would continue using yesterday's precomputed aggregates until the next successful precomputation job.

------------------------------------------------------------------------

## Alternative Path 3a -- Grid Resolution Configuration Updated

The system administrator updates the grid resolution from 500m × 500m cells to 250m × 250m cells to provide more granular aggregates.

The next scheduled precomputation job starts with the new configuration. The Data Pipeline detects the grid resolution change:
- Previous run: 2,847 cells at 500m resolution
- Current run: 11,388 cells at 250m resolution (4× more cells)

The Data Pipeline logs: "INFO: Grid resolution changed from 500m to 250m. Cell count increased from 2,847 to 11,388."

The pipeline proceeds to aggregate features for all 11,388 cells. Processing takes significantly longer (72 minutes instead of 18 minutes) due to the 4× increase in cells.

The aggregation completes successfully. The new finer-grained grid features are written to the database, replacing the coarser 500m grid.

When the Estimate API uses the new grid features, it benefits from more localized neighborhood statistics, potentially improving estimate accuracy in areas with high property value variance.

The Monitoring Service notes the increased processing time and alerts the operations team: "INFO: Grid precomputation now takes 72 minutes due to resolution increase. Consider adjusting job schedule if needed."
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-30, one or more services exceed predefined latency
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

The actor attempts to perform UC-30 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-30, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
