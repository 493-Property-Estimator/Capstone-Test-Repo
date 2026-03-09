# UC-07 -- Fully Dressed Scenario Narratives

**Use Case:** Compute Proximity to Amenities for Baseline Desirability

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

The valuation engine begins feature computation for a property after
receiving a valid canonical location ID.

The system retrieves the geographic coordinates associated with the
canonical location ID from the spatial database.

Using these coordinates as the reference point, the system queries the
indexed open-data POI datasets to identify relevant amenities within a
predefined search radius. The relevant categories include schools,
parks, and hospitals.

The system identifies candidate amenities within the search radius.

For each relevant amenity, the system computes the distance between the
property location and the amenity. Depending on system configuration,
the distance may be computed using routing-based travel distance or
straight-line (Euclidean) distance.

The system aggregates the proximity information into structured metrics.
These may include: - Distance to the nearest school\
- Number of parks within the search radius\
- Distance to the nearest hospital

The system applies predefined weighting rules to these proximity metrics
to derive a baseline desirability score.

The computed proximity metrics and derived desirability score are
attached to the property's feature set.

The use case ends successfully with proximity features available for
downstream valuation calculations.

------------------------------------------------------------------------

## Alternative Path 3a -- No Amenities Found Within Search Radius

The valuation engine retrieves the geographic coordinates for the
canonical location ID.

The system queries the spatial database for relevant amenities within
the predefined search radius.

No amenities of one or more categories (e.g., no parks within the
radius) are found.

Instead of failing, the system applies predefined fallback rules. These
may include: - Assigning zero counts for count-based metrics\
- Assigning a maximum-distance threshold value for nearest-distance
metrics

The system proceeds to apply weighting rules using these fallback
values.

A baseline desirability score is computed accordingly.

The use case ends successfully with proximity features reflecting the
absence of nearby amenities.

------------------------------------------------------------------------

## Alternative Path 4a -- Distance Computation Service Unavailable

The valuation engine retrieves the geographic coordinates and identifies
nearby amenities.

The system attempts to compute travel-based distances using a routing
service.

The routing or distance computation service fails due to outage,
timeout, or configuration error.

The system detects the failure and logs the incident.

The system falls back to straight-line (Euclidean) distance calculations
using geographic coordinates.

Distances are successfully computed using the fallback method.

The system aggregates the proximity metrics and derives the baseline
desirability score.

The use case ends successfully with proximity features computed using
fallback distance logic.

------------------------------------------------------------------------

## Alternative Path 2a -- Canonical Location ID Cannot Be Resolved to Coordinates

The valuation engine receives a canonical location ID.

The system attempts to retrieve associated geographic coordinates from
the spatial database.

The lookup fails due to missing records or data inconsistency.

Because coordinates cannot be resolved, the system cannot perform
spatial queries for nearby amenities.

The system logs the failure for monitoring and diagnostic purposes.

The system omits proximity-based features and proceeds without applying
a baseline desirability adjustment.

The use case ends with proximity features absent and downstream
valuation continuing without them.

------------------------------------------------------------------------

## Alternative Path 6a -- Weighting Rules Missing or Misconfigured

The system retrieves coordinates and computes proximity metrics
successfully.

When attempting to apply weighting rules to derive the baseline
desirability score, the system detects that weighting parameters are
missing or misconfigured.

The system logs the configuration issue.

The system applies default weighting parameters defined as part of the
system's fallback configuration.

Using these default weights, the system computes the baseline
desirability score.

The computed proximity features and desirability score are attached to
the property's feature set.

The use case ends successfully with fallback weighting applied.
