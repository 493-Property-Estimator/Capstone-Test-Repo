# UC-25 -- Fully Dressed Scenario Narratives

**Use Case:** Toggle Open-Data Layers in the Map UI

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Toggle Schools Layer

A user wants to see where schools are located relative to a property they are considering. The user has the Property Value Estimator map UI open and is viewing a specific neighborhood in Edmonton.

The system displays the base map showing streets, parks, and buildings. On the left side of the map, the system displays a "Map Layers" panel containing toggle switches for various data layers: Schools, Parks/Green Spaces, Census Boundaries, Assessment Zones, Crime Heatmap, and Stores.

The user clicks the toggle switch next to "Schools" to turn on the schools layer.

The system detects the layer toggle action. It first checks whether the schools layer data is already cached locally in the browser from a previous session. The cache is empty for this layer.

The system determines the current map bounding box (visible region): northwest corner (53.565, -113.520), southeast corner (53.545, -113.490). This represents approximately 2 km × 2 km visible area.

The system sends a request to the Layer Data API: `GET /layers/schools?bbox=53.545,-113.520,53.565,-113.490&format=geojson`

The Layer Data API queries the Feature Store database for school locations within the requested bounding box. It finds 8 schools in the visible area.

The Layer Data API returns a GeoJSON response containing 8 school features. Each feature includes:
- School name (e.g., "Riverdale Elementary School")
- Coordinates (lat, lon)
- School type (Elementary, Junior High, Senior High)
- Enrollment capacity

The system receives the GeoJSON data. It processes each school feature and renders them on the map as blue marker icons with a school symbol. Elementary schools use small markers, junior high use medium markers, and senior high schools use large markers for visual distinction.

The system updates the legend panel to include a "Schools" entry showing the three marker sizes and their meanings.

The user sees 8 school markers appear on the map. The user pans the map slightly to the east to explore a different area.

As the user pans, the system dynamically updates the visible bounding box. When the pan ends, the new bounding box is: northwest corner (53.565, -113.505), southeast corner (53.545, -113.475).

The system automatically sends a new request to the Layer Data API with the updated bounding box to fetch schools in the newly visible area.

The Layer Data API returns 5 additional schools. The system renders these new schools while keeping the previously visible schools in memory for smooth panning back.

After exploring, the user decides they no longer need to see schools. The user clicks the "Schools" toggle switch again to turn it off.

The system removes all school markers from the map and removes the schools legend entry. The base map returns to showing only the default layers.

------------------------------------------------------------------------

## Alternative Path 3a -- Rapid Layer Toggle

A user clicks multiple layer toggles in quick succession while exploring different data overlays.

The user has the map open and starts rapidly clicking layer toggles: clicks "Schools" on, then immediately clicks "Parks" on, then immediately clicks "Crime Heatmap" on, all within 2 seconds.

Each click triggers a layer toggle event. The system receives three toggle events in rapid succession.

The system's debouncing logic detects the rapid sequence of requests. Rather than immediately firing three separate API requests to the Layer Data API, it accumulates the requests for 500 milliseconds.

After the debounce delay, the system determines the final desired state: Schools ON, Parks ON, Crime Heatmap ON. The system sends a single batched request to the Layer Data API requesting all three layers for the current bounding box.

The Layer Data API processes the batched request and returns data for all three layers in the response.

The system renders all three layers simultaneously. The user sees schools, parks, and crime heat map overlays appear together on the map without multiple intermediate states or flickering.

------------------------------------------------------------------------

## Alternative Path 5a -- Large Dataset Progressive Loading

A user enables the "Assessment Zones" layer which contains complex polygon boundaries for thousands of assessment parcels.

The user clicks the "Assessment Zones" toggle. The system sends a request to the Layer Data API for assessment zone data in the current bounding box.

The Layer Data API queries the database and determines that the assessment zones dataset for the visible area contains 1,200 polygon features totaling 4.5 MB of GeoJSON data. This is a large dataset that would take several seconds to transfer and render.

The Layer Data API implements progressive loading. It divides the response into chunks and begins streaming the first chunk containing 200 polygons (approximately 750 KB) immediately.

The system receives the first chunk of data after 300ms. Rather than waiting for the complete dataset, it immediately begins rendering the first 200 assessment zone polygons as semi-transparent boundaries overlaid on the map.

While the first chunk renders, the system displays a loading spinner in the corner of the map with text "Loading Assessment Zones: 20% complete".

The Layer Data API continues streaming subsequent chunks. The system receives and renders chunk 2 (400 total polygons), updates the progress indicator to "40% complete", then chunk 3 (600 total), then chunk 4, and so on.

After 2 seconds, all 1,200 polygons have been received and rendered. The loading spinner disappears, and the user can now see the complete assessment zones layer with all parcel boundaries visible.

The progressive loading approach provides early visual feedback rather than a blank screen, improving perceived performance.

------------------------------------------------------------------------

## Alternative Path 6a -- Layer Data API Unavailable

A user attempts to enable a layer when the backend Layer Data API service is experiencing an outage.

The user clicks the "Parks/Green Spaces" toggle to turn on the parks layer. The system sends a request to the Layer Data API for parks data.

The Layer Data API is currently unavailable due to a database maintenance window. The request times out after 5 seconds with no response.

The system detects the timeout failure. It displays an error notification banner at the top of the map:

"Parks/Green Spaces layer unavailable. Please try again later."

The system automatically reverts the toggle switch back to the OFF position to reflect that the layer is not actually displayed.

The system logs the error to the monitoring system with details: timestamp, layer name, error type (timeout), and bounding box for operational troubleshooting.

The toggle switch is temporarily disabled with a "retry" icon appearing next to it for 30 seconds to prevent rapid repeated failed requests.

After 30 seconds, the toggle becomes enabled again, and the user can attempt to load the layer again. If the API service is restored, the subsequent attempt will succeed.

------------------------------------------------------------------------

## Alternative Path 6b -- Incomplete Layer Coverage

A user enables a layer in a region where data coverage is incomplete.

The user is viewing a map area that includes both central Edmonton (well-covered) and rural areas on the periphery (limited coverage). The user toggles on the "Crime Heatmap" layer.

The system sends a request to the Layer Data API for crime data in the visible bounding box. The Layer Data API queries the crime statistics database.

The database contains crime data only for census tracts within Edmonton city limits. The rural areas in the visible bounding box have no crime data available.

The Layer Data API returns a response containing crime data for the urban portion of the bounding box and a coverage indicator showing which regions have data and which do not.

The system renders the crime heatmap only in the areas where data is available. The heatmap shows color intensity variations (green = low crime, yellow = medium, red = high) in the urban areas.

In the rural areas where no data is available, the system renders a grey stippled pattern indicating "No data available".

The system displays a warning banner: "Crime data coverage is incomplete for this view. Grey areas indicate regions where crime statistics are not available."

The legend is updated to include an entry for "No data available" with the grey stippled pattern.

The user understands the limitation and can choose to zoom in on the urban areas where complete coverage exists, or accept the partial view.

------------------------------------------------------------------------

## Alternative Path 7a -- Rendering Performance Degradation

A user has enabled multiple complex layers on a low-performance device (older laptop or tablet), causing the map to render slowly.

The user has enabled Schools, Parks, Crime Heatmap, and Assessment Zones simultaneously. The map view contains thousands of features being rendered at once.

The system monitors rendering performance through the browser's frame rate. It detects that the frame rate has dropped to 15 frames per second (below the target of 30 fps), indicating performance degradation.

The rendering engine automatically reduces the level of detail to improve performance. It simplifies polygon boundaries by reducing vertex counts using the Ramer-Douglas-Peucker algorithm, culls features outside the immediate viewport, and reduces the number of crime heatmap sample points.

The simplified rendering improves the frame rate to 28 fps, providing smoother panning and zooming.

The system displays a notice: "Performance mode active. Some layer details simplified for smoother interaction. Zoom in for full detail."

When the user zooms in to view a smaller area with fewer features, the system automatically restores full detail rendering as performance allows.

------------------------------------------------------------------------

## Alternative Path 9a -- Zoom Out Beyond Layer Resolution

A user zooms out to view the entire Edmonton metropolitan area. Some detail-oriented layers become impractical to display at this zoom level.

The user zooms out to zoom level 10, showing approximately 50 km × 50 km. The "Schools" layer is currently enabled, which would require rendering over 800 individual school markers at this zoom level, creating visual clutter.

The system detects that the current zoom level (10) is below the minimum recommended zoom level for the Schools layer (minimum zoom 13 for readable school markers).

Rather than rendering 800 overlapping markers that would be illegible, the system automatically hides the Schools layer and displays a message overlay on the map:

"Schools layer hidden at this zoom level. Zoom in to zoom level 13 or higher to view individual schools."

The toggle switch for Schools remains in the ON position but becomes dimmed/grayed to indicate the layer is enabled but not currently visible due to zoom constraints.

The legend entry for Schools is also grayed out with text "(hidden - zoom in to view)".

When the user zooms back in to zoom level 13 or higher, the school markers automatically reappear, and the toggle and legend return to normal appearance.

This prevents visual clutter and performance issues at inappropriate zoom levels while maintaining the user's layer selection preferences.
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-25, one or more services exceed predefined latency
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

The actor attempts to perform UC-25 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-25, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
