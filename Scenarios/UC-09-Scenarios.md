# UC-09 -- Fully Dressed Scenario Narratives

**Use Case:** Compute Green Space Coverage for Environmental
Desirability

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

The valuation engine initiates environmental feature computation after
receiving a valid canonical location ID for a property.

The system retrieves the spatial representation associated with the
canonical location ID. Depending on system design, this may be a point
(coordinates) or a parcel boundary polygon.

Using the property's spatial geometry as the reference, the system
defines a predefined analysis buffer around the property. The buffer may
be a circular radius (e.g., 500 meters) or a polygonal zone defined by
configuration.

The system queries the indexed land use or green space dataset to
identify all green space geometries that intersect with the analysis
buffer. Green space categories may include public parks, forests,
recreational fields, and other designated open spaces as defined by
system rules.

The system computes the total area of green space within the analysis
buffer by calculating the intersection between green space polygons and
the buffer area.

The system calculates green space coverage as a percentage:

Green Space Coverage = (Green Space Area within Buffer / Total Buffer
Area) × 100

Using predefined thresholds or weighting rules, the system derives an
environmental desirability indicator based on the calculated coverage
percentage.

The system attaches the following to the property's feature set: - Total
green space area within buffer\
- Green space coverage percentage\
- Derived environmental desirability indicator

The use case ends successfully with environmental features available for
downstream valuation and user-facing reporting.

------------------------------------------------------------------------

## Alternative Path 2a -- Canonical Location ID Cannot Be Resolved to Spatial Geometry

The valuation engine receives a canonical location ID and attempts to
retrieve associated spatial geometry.

The spatial lookup fails due to missing geometry records or data
inconsistency.

Without property geometry, the system cannot define an analysis buffer.

The system logs the failure for monitoring and diagnostics.

The system omits green space coverage computation and proceeds without
environmental adjustment.

The use case ends without environmental features attached to the
property.

------------------------------------------------------------------------

## Alternative Path 4a -- Land Use Dataset Unavailable or Incomplete

The valuation engine retrieves the property's spatial geometry and
defines the analysis buffer successfully.

The system attempts to query the land use dataset.

The dataset is unavailable, corrupted, or incomplete.

The system logs the dataset issue.

Instead of failing outright, the system applies fallback logic. This may
include: - Using cached green space coverage values if available\
- Using higher-level regional averages (e.g., neighbourhood-level
coverage)

The system derives an environmental desirability indicator using the
fallback data.

The system attaches fallback-based environmental features to the
property's feature set.

The use case ends successfully with reduced-confidence environmental
features.

------------------------------------------------------------------------

## Alternative Path 4b -- No Green Space Found Within Analysis Buffer

The valuation engine retrieves spatial geometry and defines the analysis
buffer.

The system queries the land use dataset and finds no green space
geometries intersecting the buffer.

The computed green space area within the buffer is zero.

The system calculates green space coverage as 0%.

Using predefined thresholds, the system derives a low environmental
desirability indicator consistent with zero coverage.

The system attaches: - Green space area = 0\
- Coverage percentage = 0%\
- Derived environmental desirability score

The use case ends successfully with environmental features reflecting
absence of nearby green space.

------------------------------------------------------------------------

## Alternative Path 7a -- Threshold or Weighting Configuration Missing

The valuation engine successfully computes green space area and coverage
percentage.

When attempting to derive the environmental desirability indicator, the
system detects that threshold or weighting configuration is missing or
misconfigured.

The system logs the configuration issue.

The system applies default environmental weighting parameters defined in
fallback configuration.

Using these default parameters, the system derives the environmental
desirability indicator.

The system attaches the environmental features to the property's feature
set.

The use case ends successfully with fallback weighting applied.
