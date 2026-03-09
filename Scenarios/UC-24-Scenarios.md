# UC-24 -- Fully Dressed Scenario Narratives

**Use Case:** Search by Address in the Map UI

------------------------------------------------------------------------

## Main Success Scenario Narrative -- Address Search with Autocomplete

A user wants to view property valuation context for a specific address in Edmonton. The user opens the Property Value Estimator web application in their browser.

The system loads the map UI successfully, displaying a base map of Edmonton with default zoom level showing the city overview. The UI displays a prominent search bar at the top with placeholder text "Search for an address".

The user clicks on the search bar and begins typing "10234 98 Stre". After typing these characters, the system waits 300 milliseconds to debounce rapid keystrokes.

The system sends the partial input "10234 98 Stre" to the Autocomplete service. The Autocomplete service queries its indexed address database and identifies potential matches based on the partial input.

The Autocomplete service returns a list of five suggested addresses ranked by relevance:
1. "10234 98 Street NW, Edmonton, AB T5H 2P9"
2. "10234 98 Street SW, Edmonton, AB T6X 1T2"
3. "10234 98 Avenue NW, Edmonton, AB T5K 0A4"
4. "10234 98A Street NW, Edmonton, AB T5H 2K8"
5. "10232 98 Street NW, Edmonton, AB T5H 2P8"

The system displays these suggestions in a dropdown list below the search bar. Each suggestion shows the full address with postal code for disambiguation.

The user recognizes the first suggestion as their desired property and clicks on "10234 98 Street NW, Edmonton, AB T5H 2P9" in the dropdown list.

The system selects the address and sends the full query "10234 98 Street NW, Edmonton, AB T5H 2P9" to the Geocoding/Location Resolver service.

The Geocoding service successfully resolves the address to geographic coordinates: latitude 53.551086, longitude -113.501847. It also returns the canonical address format and neighborhood context "Riverdale".

The system animates the map, panning and zooming smoothly to center on coordinates (53.551086, -113.501847) with an appropriate zoom level to show the property and surrounding neighborhood (zoom level 16).

The system places a prominent red marker pin at the resolved property location. The marker is labeled with the canonical address "10234 98 Street NW".

The system displays an info card showing the canonical address, neighborhood "Riverdale", and a button labeled "Get Property Estimate".

The user can now see the property location on the map, explore surrounding features, toggle layers, or click "Get Property Estimate" to request a valuation.

------------------------------------------------------------------------

## Alternative Path 3a -- Incomplete Input

A user opens the map UI and wants to search for a property. The user clicks on the search bar and types only "10".

The system detects that the input consists of only 2 characters, which is too short to produce meaningful autocomplete suggestions.

The system does not call the Autocomplete service to avoid unnecessary API requests and impractical results. Instead, it displays a hint message below the search bar: "Enter more details to see suggestions".

The user continues typing and adds more characters: "10234 98". The input now has 8 characters including the space.

The system recognizes the input is now sufficient length. After the debounce delay of 300ms, the system sends "10234 98" to the Autocomplete service.

The Autocomplete service returns relevant suggestions, and the system displays them in the dropdown. The user continues as in the main success scenario.

------------------------------------------------------------------------

## Alternative Path 5a -- No Autocomplete Suggestions

A user types an address that does not match any known entries in the autocomplete database.

The user enters "99999 Fake Street" into the search bar. After the debounce delay, the system sends this query to the Autocomplete service.

The Autocomplete service searches its database but finds no addresses matching the pattern "99999 Fake Street". It returns an empty suggestion list.

The system displays a message in the dropdown area: "No suggestions found. Press Enter to search anyway."

The user decides to press the Enter key to submit the full query despite having no suggestions.

The system sends "99999 Fake Street" to the Geocoding/Location Resolver service for direct geocoding without suggestions.

The system continues with the geocoding response (which may succeed if the geocoder has broader coverage, or fail as described in Alternative Path 9a).

------------------------------------------------------------------------

## Alternative Path 7a -- Ambiguous Address with Multiple Candidates

A user submits a search for an address without sufficient detail to uniquely identify the property.

The user types "123 Main Street"  without specifying a quadrant (NW, NE, SW, SE) or postal code. The user presses Enter to submit the search.

The system sends the query "123 Main Street" to the Geocoding/Location Resolver service.

The Geocoding service searches for matching addresses and finds multiple candidates:
- "123 Main Street NW, Edmonton, AB T5J 1A1" (Downtown)
- "123 Main Street NE, Edmonton, AB T5A 0X2" (Eastwood)
- "123 Main Street SW, Edmonton, AB T6X 0P9" (Riverbend)
- "123 Main Street SE, Edmonton, AB T6C 2H8" (Mill Woods)

The Geocoding service returns all four candidates with their coordinates and neighborhood information, along with a status indicating "AMBIGUOUS".

The system detects the ambiguous result. Rather than panning the map to one arbitrary location, it displays a "Did you mean?" panel on the side of the map showing all four candidates.

For each candidate, the system shows:
- The full address with postal code
- The neighborhood name
- A small preview thumbnail of the map location
- A "Select" button

The user reviews the list and recognizes "123 Main Street NW, Edmonton, AB T5J 1A1" in Downtown as their desired property. The user clicks the "Select" button next to that candidate.

The system treats the selected address as if it were the original query. It pans and zooms the map to the selected coordinates, places a marker, and displays the property information panel. The user can now proceed to request an estimate.

------------------------------------------------------------------------

## Alternative Path 8a -- Geocoding Service Unavailable

A user attempts to search for an address during a period when the external geocoding service is experiencing an outage.

The user enters "10234 98 Street NW, Edmonton" into the search bar and presses Enter.

The system sends the query to the Autocomplete service which returns suggestions normally. The user selects a suggestion.

The system sends the full address to the Geocoding/Location Resolver service for coordinate resolution. The geocoding service is currently unavailable due to a network issue or service outage.

After waiting for the configured timeout of 3 seconds, the system receives an error response indicating the geocoding service is unreachable.

The system detects the service failure. It displays an error message in a notification banner at the top of the map UI:

"Search unavailable right now. Please try again in a moment. If the issue persists, you can click directly on the map to select a location."

The map remains at its current position and no marker is placed. The search bar returns to its empty state.

The system logs the geocoding service failure to the monitoring system with details including timestamp, attempted address, and error code for operational awareness.

The user waits a few seconds and tries the search again. If the service is restored, the search succeeds. Alternatively, the user can use the map click functionality (UC-03) to select a property location directly.

------------------------------------------------------------------------

## Alternative Path 9a --   Address Not Found

A user searches for an address that does not exist or is incorrectly spelled.

The user enters "12 Nonexistent Boulevard, Edmonton" into the search bar and presses Enter.

The system sends the query to the Geocoding/Location Resolver service. The geocoding service searches its database and external data sources but cannot find any property matching the provided address.

The Geocoding service returns a "NOT_FOUND" status with no coordinates.

The system detects that no matching address was found. It displays a message overlay on the map:

"No matching address found. Please check the spelling and try again."

Below the primary message, the system shows additional help text:

"Try providing more details such as:
- Postal code (e.g., T5J 1A1)
- Quadrant (NW, NE, SW, SE)
- Or use coordinates in lat, lon format"

The map remains in its current state without panning or placing any marker. The search bar retains the entered text "12 Nonexistent Boulevard, Edmonton" so the user can correct it easily.

The user reviews the message, realizes the address is incorrect, and modifies the search query to correct the spelling or provide more specific details. The user resubmits the search, which can proceed normally if the corrected address is valid.

------------------------------------------------------------------------

## Alternative Path 10a -- Address Outside Supported Coverage

A user searches for an address that is outside the supported geographic coverage area of the Property Value Estimator system.

The user enters "123 Main Street, Calgary, AB" into the search bar. The user presses Enter.

The system sends the query to the Geocoding/Location Resolver service. The geocoding service successfully resolves the address to coordinates (51.0447, -114.0719) in Calgary with canonical address "123 Main Street SW, Calgary, AB T2P 1M7".

The system receives the coordinate response and checks whether the location falls within the supported coverage boundaries. The system's coverage is limited to the Edmonton metropolitan area (bounding box approximately 53.3°-53.8°N, 113.8°-113.2°W).

The system determines that Calgary coordinates (51.0447, -114.0719) fall outside the supported boundary.

The system displays a warning notification:

"Region not supported. This property is located in Calgary, which is outside our current coverage area. Property Value Estimator currently only supports properties in the Edmonton metropolitan region."

Optionally, the system pans the map to show the boundary edge closest to the searched location, highlighting the coverage area in a semi-transparent overlay. For Calgary, this would pan to the southern edge of Edmonton coverage.

The map displays a gray marker at the approximate direction of the searched location with a label "Searched location: Calgary (out of coverage)".

The user understands the address is not supported and can either:
- Search for a different address within Edmonton
- Use the contact information displayed to request coverage expansion

------------------------------------------------------------------------

## Additional Scenario -- Rapid Successive Searches

A user quickly changes their mind while searching and types a different address before the first search completes.

The user types "10234 98 Street" and suggestions appear. Before selecting a suggestion, the user changes their mind and immediately clears the search bar.

The user types a completely different address "5432 111 Avenue". The Autocomplete service is still processing the previous query "10234 98 Street".

The system's debounce logic detects the interruption. It cancels any pending autocomplete requests for "10234 98 Street" to avoid showing outdated results.

The system sends only the most recent query "5432 111 Avenue" to the Autocomplete service after the debounce delay.

The Autocomplete service returns suggestions for "5432 111 Avenue", and the system displays these suggestions, ignoring any responses from the canceled previous query.

This ensures the user always sees suggestions relevant to their current input without confusion from stale results.
    the output as partial or degraded.

In degraded scenarios, the system includes: - A reduced
confidence/completeness score, - A list of omitted factors, - Clear
warnings for UI display or API response metadata.

The monitoring subsystem logs the dependency failure for operational
follow-up.

------------------------------------------------------------------------

## Alternative Path Narrative C: Timeout or Performance Threshold Exceeded

While processing UC-24, one or more services exceed predefined latency
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

The actor attempts to perform UC-24 without appropriate permissions or
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

If monitoring or metrics export fails during execution of UC-24, the
system continues primary business processing. However, it logs the
failure locally and flags the observability subsystem for maintenance.

Core functionality remains unaffected unless monitoring failure impacts
critical dependencies.

------------------------------------------------------------------------
