# UC-03 -- Fully Dressed Scenario Narratives

**Use Case:** Select Location by Clicking on Map

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

A general user wants to quickly evaluate the property value of different
locations without typing an address or entering coordinates. The user
opens the Property Value Estimator system and navigates to the
interactive map interface.

The system loads and displays the map with relevant layers (such as
boundaries, assessment zones, or other available overlays).

The user visually explores the map and clicks on a specific point
representing a location of interest.

The system captures the geographic coordinates corresponding to the
clicked point on the map.

The system verifies that the captured coordinates fall within the
supported geographic boundary of the system.

The coordinates are confirmed to be within the supported area.

The system converts the coordinates into its internal canonical location
identifier to ensure consistent downstream processing.

Using this canonical location, the system computes the property value
estimate based on the assessment baseline and relevant open-data
features.

The system displays: - A single estimated property value\
- A low/high range\
- Supporting explanatory information

The estimate appears at or near the clicked location (e.g., in a popup
or side panel).

The use case ends successfully with the estimate visible to the user.

------------------------------------------------------------------------

## Alternative Path 3a -- Click Outside Supported Geographic Boundary

A general user clicks on a point on the map.

The system captures the geographic coordinates of the clicked location.

The system verifies whether the coordinates fall within the supported
geographic boundary.

The coordinates are determined to be outside the supported area.

The system informs the user that the selected location is outside the
supported geographic region and cannot be processed.

No canonical location ID is generated and no valuation is computed.

The use case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 4a -- Map or Rendering Error Prevents Coordinate Resolution

A general user clicks on the map.

Due to a rendering issue, coordinate projection error, or temporary map
service malfunction, the system is unable to determine valid geographic
coordinates for the clicked point.

The system does not proceed to geographic boundary verification or
valuation.

Instead, the system displays an error message indicating that the
selected location could not be determined.

The user may click again to retry the selection.

If the user retries and coordinates are successfully captured, the
system resumes the normal flow at Step 3 of the Main Success Scenario.

If the user abandons the process, the use case ends in the Failed End
Condition.

------------------------------------------------------------------------

## Alternative Path 7a -- Partial Valuation Data Available

A general user clicks on a valid location within the supported
geographic boundary.

The system captures the coordinates and converts them into a canonical
location ID.

During the valuation process, the system detects that one or more
open-data feature datasets required for full valuation are unavailable
(for example, missing neighbourhood indicators or temporarily
unavailable POI datasets).

Rather than terminating the process, the system computes a partial
estimate using the available data and the assessment baseline.

The system displays: - A single estimated property value\
- A low/high range\
- A visible warning indicating that some data sources were unavailable
and that the estimate may have reduced accuracy

The use case ends successfully with a qualified estimate presented to
the user.
