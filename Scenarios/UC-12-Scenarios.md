# UC-12 -- Fully Dressed Scenario Narratives

**Use Case:** Compute Neighbourhood Indicators for Local Context

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

The valuation engine initiates neighbourhood context feature computation
after receiving a valid canonical location ID for a property.

The system retrieves the geographic coordinates associated with the
canonical location ID from the spatial database.

Using these coordinates, the system determines which neighbourhood
boundary contains the property. The boundary definition may be based on
census tracts, planning districts, or another configured spatial unit.

Once the appropriate neighbourhood boundary is identified, the system
retrieves neighbourhood-level statistical indicators from the relevant
datasets. These indicators may include population density, median
household income, crime rate index, housing density, tenure mix, or
other contextual metrics defined by system configuration.

The system aggregates and normalizes the retrieved indicators as
required. For example, raw counts may be converted to per-capita values,
or metrics may be normalized to a standard scale.

Using predefined weighting or scoring rules, the system derives a
summarized neighbourhood context profile or composite indicator that
represents overall local context.

The system attaches the following to the property's feature set: -
Individual neighbourhood indicators\
- Normalized values (if applicable)\
- Derived composite neighbourhood context profile

The use case ends successfully with neighbourhood indicators available
for downstream valuation and user-facing reporting.

------------------------------------------------------------------------

## Alternative Path 2a -- Canonical Location ID Cannot Be Resolved to Coordinates

The valuation engine receives a canonical location ID and attempts to
retrieve its geographic coordinates.

The coordinate lookup fails due to missing records or data
inconsistency.

Without valid coordinates, the system cannot determine the corresponding
neighbourhood boundary.

The system logs the failure for monitoring and diagnostics.

The system omits neighbourhood context computation and proceeds without
attaching neighbourhood-related features.

The use case ends without neighbourhood indicators attached to the
property.

------------------------------------------------------------------------

## Alternative Path 3a -- Property Does Not Map Cleanly to a Neighbourhood Boundary

The valuation engine retrieves valid property coordinates.

The system attempts to map the property to a neighbourhood boundary.

The property lies on a boundary edge, overlaps multiple polygons, or
does not fall clearly within a single boundary due to dataset
inconsistencies.

The system applies predefined boundary resolution logic. This may
include: - Assigning the property to the nearest neighbourhood centroid\
- Selecting the boundary with the largest area overlap\
- Applying deterministic tie-breaking rules

The system logs the boundary resolution method used.

The system proceeds to retrieve neighbourhood indicators for the
resolved boundary.

The use case continues from Step 4 of the Main Success Scenario and ends
successfully.

------------------------------------------------------------------------

## Alternative Path 4a -- Statistical Dataset Unavailable or Incomplete

The valuation engine successfully determines the neighbourhood boundary.

The system attempts to retrieve neighbourhood-level indicators from
statistical datasets.

The dataset is unavailable, corrupted, or incomplete.

The system logs the dataset issue.

Rather than failing outright, the system applies fallback logic. This
may include: - Using cached neighbourhood indicator values\
- Using higher-level regional averages (e.g., city-wide averages)

Using fallback values, the system derives the composite neighbourhood
context profile.

The system attaches fallback-based neighbourhood indicators and
composite profile to the property's feature set.

The use case ends successfully with reduced-confidence neighbourhood
context features.

------------------------------------------------------------------------

## Alternative Path 6a -- Composite Weighting Configuration Missing

The valuation engine successfully retrieves and normalizes neighbourhood
indicators.

When attempting to derive the composite neighbourhood context profile,
the system detects that weighting or scoring configuration is missing or
misconfigured.

The system logs the configuration issue.

The system applies default neighbourhood weighting parameters defined in
fallback configuration.

Using these default parameters, the system derives the composite
neighbourhood context profile.

The system attaches individual indicators and the derived composite
profile to the property's feature set.

The use case ends successfully with fallback weighting applied.
