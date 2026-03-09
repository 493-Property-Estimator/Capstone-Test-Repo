# UC-10 -- Fully Dressed Scenario Narratives

**Use Case:** Compute Distance-to-School Signals for Family Suitability

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

The valuation engine initiates school proximity feature computation
after receiving a valid canonical location ID for a property.

The system retrieves the geographic coordinates associated with the
canonical location ID from the spatial database.

Using these coordinates as the origin point, the system queries the
indexed school dataset to identify relevant schools within a predefined
search radius. School categories may include elementary, middle, and
high schools, depending on system configuration.

The system identifies candidate schools within the search radius.

For each identified school, the system computes the distance from the
property location. Depending on configuration, the system may compute
travel-based distance using a routing service or straight-line
(Euclidean) distance.

The system aggregates the computed distances into structured metrics.
These may include: - Distance to nearest elementary school\
- Distance to nearest secondary school\
- Average distance to the nearest N schools

Using predefined thresholds or weighting rules, the system derives a
family suitability signal. For example, shorter distances may increase
suitability, while greater distances may reduce it.

The system attaches the following to the property's feature set: -
School distance metrics\
- Derived family suitability signal

The use case ends successfully with school proximity features available
for downstream valuation and user-facing reporting.

------------------------------------------------------------------------

## Alternative Path 2a -- Canonical Location ID Cannot Be Resolved to Coordinates

The valuation engine receives a canonical location ID and attempts to
retrieve its geographic coordinates.

The coordinate lookup fails due to missing records or data
inconsistency.

Without property coordinates, the system cannot compute distances to
schools.

The system logs the failure for monitoring and diagnostics.

The system omits school proximity computation and proceeds without
applying a family suitability adjustment.

The use case ends without school-related features attached to the
property.

------------------------------------------------------------------------

## Alternative Path 3a -- No Schools Found Within Search Radius

The valuation engine retrieves valid property coordinates.

The system queries the school dataset for schools within the predefined
search radius.

No schools are found within the radius.

Instead of failing, the system applies predefined fallback logic. This
may include: - Assigning maximum-distance or sentinel values for
nearest-school metrics\
- Recording zero count for nearby schools

Using these fallback values, the system derives a family suitability
signal consistent with low accessibility to schools.

The system attaches school distance metrics (reflecting absence) and the
derived family suitability signal to the property's feature set.

The use case ends successfully with features reflecting limited school
proximity.

------------------------------------------------------------------------

## Alternative Path 4a -- Routing/Distance Service Unavailable

The valuation engine retrieves property coordinates and identifies
nearby schools.

The system attempts to compute travel-based distances using the routing
service.

The routing service fails due to outage, timeout, or configuration
error.

The system logs the routing failure.

Rather than terminating the process, the system falls back to
straight-line (Euclidean) distance calculations.

The system aggregates fallback distance metrics into structured school
distance metrics.

The system derives the family suitability signal using fallback
distances.

The use case ends successfully with school proximity features computed
using fallback logic.

------------------------------------------------------------------------

## Alternative Path 6a -- Weighting/Threshold Configuration Missing

The valuation engine successfully computes school distance metrics.

When attempting to derive the family suitability signal, the system
detects that threshold or weighting configuration is missing or
misconfigured.

The system logs the configuration issue.

The system applies default family suitability thresholds or weighting
parameters defined in fallback configuration.

Using these default parameters, the system derives the family
suitability signal.

The system attaches the school distance metrics and derived signal to
the property's feature set.

The use case ends successfully with fallback weighting applied.
