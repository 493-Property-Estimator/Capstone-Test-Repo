# UC-08 -- Fully Dressed Scenario Narratives

**Use Case:** Compute Travel-Based Distance for Accessibility

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

The valuation engine initiates accessibility feature computation for a
property after receiving a valid canonical location ID and a set of
relevant destination points (such as schools, hospitals, employment
centers, or other key amenities).

The system retrieves the geographic coordinates associated with the
canonical location ID from the spatial database.

The system retrieves the geographic coordinates for each destination in
the provided destination set.

Using the property coordinates and destination coordinates, the system
invokes the routing service to compute travel-based distances or travel
times along the road network.

The routing service processes each origin-destination pair and
calculates travel distance or travel time based on real road network
paths and configured transport mode assumptions.

The routing service returns travel-based distance values to the system.

The system aggregates the travel-based metrics. These may include: -
Travel time to the nearest destination in each category\
- Average travel time to the nearest three destinations\
- Minimum travel distance across categories

The aggregated travel-based accessibility metrics are attached to the
property's feature set for downstream valuation.

The use case ends successfully with real-world travel-based
accessibility features available to the valuation model.

------------------------------------------------------------------------

## Alternative Path 2a -- Canonical Location ID Cannot Be Resolved to Coordinates

The valuation engine receives a canonical location ID and a set of
destinations.

The system attempts to retrieve geographic coordinates for the canonical
location ID.

The coordinate lookup fails due to missing data or data inconsistency.

Without property coordinates, the system cannot invoke the routing
service.

The system logs the failure for monitoring and diagnostics.

The system omits travel-based accessibility features and proceeds
without applying travel-based adjustments to valuation.

The use case ends without accessibility features.

------------------------------------------------------------------------

## Alternative Path 4a -- Routing Service Unavailable or Times Out

The valuation engine retrieves valid coordinates for both property and
destinations.

The system invokes the routing service to compute travel-based
distances.

The routing service fails due to outage, timeout, or configuration
error.

The system detects the routing failure and logs the incident.

Rather than terminating the process, the system falls back to computing
straight-line (Euclidean) distances between the property and each
destination.

The system aggregates these fallback distance metrics into accessibility
features.

The use case ends successfully with accessibility features computed
using fallback distance logic.

------------------------------------------------------------------------

## Alternative Path 4b -- No Viable Travel Path Found

The valuation engine retrieves coordinates and invokes the routing
service.

The routing service determines that no viable travel path exists between
the property and one or more destinations (for example, the property is
in an isolated or inaccessible area).

The routing service returns a failure or unreachable status for the
affected routes.

The system records a predefined maximum travel distance threshold or
sentinel value for those unreachable destinations.

The system continues aggregation using these threshold values.

Travel-based accessibility metrics are computed accordingly.

The use case ends successfully with accessibility features reflecting
limited connectivity.

------------------------------------------------------------------------

## Alternative Path 6a -- Destination List Empty

The valuation engine initiates accessibility computation but receives an
empty destination list due to configuration or upstream data issue.

The system retrieves property coordinates successfully.

Because there are no destinations to evaluate, the system cannot compute
travel distances.

The system records accessibility metrics as zero-count, null, or
predefined default values according to system rules.

The system logs the configuration issue for monitoring.

The use case ends with default or neutral accessibility features
attached to the property.
