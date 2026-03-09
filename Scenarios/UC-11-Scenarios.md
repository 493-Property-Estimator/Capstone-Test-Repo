# UC-11 -- Fully Dressed Scenario Narratives

**Use Case:** Compute Commute Accessibility for Work Access Evaluation

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

The valuation engine initiates commute accessibility feature computation
after receiving a valid canonical location ID for a property.

The system retrieves the geographic coordinates associated with the
canonical location ID from the spatial database.

Using these coordinates as the origin, the system identifies relevant
employment centers or commute targets. These may include central
business districts, major employment hubs, transit nodes, or other
predefined workplace clusters as defined in system configuration.

For each identified employment center, the system invokes the routing
service to compute travel time or travel distance along the road
network. The routing computation uses the configured transport mode
(e.g., driving or transit) and any applicable assumptions such as
typical travel speeds.

The routing service processes each origin-destination pair and returns
commute travel metrics.

The system aggregates the commute metrics into structured accessibility
indicators. These may include: - Travel time to the nearest employment
center\
- Average travel time to the nearest N employment centers\
- Weighted accessibility index combining multiple destinations

Using predefined thresholds or weighting rules, the system derives a
commute accessibility indicator. For example, shorter travel times may
correspond to higher accessibility scores.

The system attaches the following to the property's feature set: -
Individual commute metrics\
- Aggregated commute accessibility indicator

The use case ends successfully with commute accessibility features
available for downstream valuation and user-facing reporting.

------------------------------------------------------------------------

## Alternative Path 2a -- Canonical Location ID Cannot Be Resolved to Coordinates

The valuation engine receives a canonical location ID and attempts to
retrieve associated geographic coordinates.

The coordinate lookup fails due to missing records or data
inconsistency.

Without property coordinates, the system cannot compute commute travel
metrics.

The system logs the failure for monitoring and diagnostics.

The system omits commute accessibility computation and proceeds without
applying a work-access adjustment to valuation.

The use case ends without commute-related features attached to the
property.

------------------------------------------------------------------------

## Alternative Path 3a -- No Employment Centers Configured or Found

The valuation engine retrieves valid property coordinates.

The system attempts to identify relevant employment centers based on
configuration.

No employment centers are configured, or none are found within the
relevant geographic scope.

The system records default or neutral commute accessibility values
according to predefined rules. This may include: - Assigning neutral
accessibility scores\
- Recording zero-count employment centers

The system logs the configuration issue.

The use case ends successfully with default commute accessibility
features attached to the property.

------------------------------------------------------------------------

## Alternative Path 4a -- Routing Service Unavailable or Times Out

The valuation engine retrieves property coordinates and identifies
employment centers.

The system attempts to compute travel-based commute metrics using the
routing service.

The routing service fails due to outage, timeout, or configuration
error.

The system logs the routing failure.

Rather than terminating the process, the system falls back to computing
straight-line (Euclidean) distance between the property and each
employment center.

The system aggregates these fallback distance estimates into commute
accessibility metrics.

The system derives the commute accessibility indicator using fallback
distances.

The use case ends successfully with commute accessibility features
computed using fallback logic.

------------------------------------------------------------------------

## Alternative Path 7a -- Commute Weighting Configuration Missing

The valuation engine successfully computes commute travel metrics.

When attempting to derive the commute accessibility indicator, the
system detects that weighting or threshold configuration is missing or
misconfigured.

The system logs the configuration issue.

The system applies default commute weighting parameters defined in
fallback configuration.

Using these default parameters, the system derives the commute
accessibility indicator.

The system attaches commute metrics and the derived indicator to the
property's feature set.

The use case ends successfully with fallback weighting applied.
