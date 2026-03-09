# UC-05 -- Fully Dressed Scenario Narratives

**Use Case:** Estimate Property Value Using Location Only

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

A general user wants to quickly obtain an estimate of a property's value
but does not have or does not wish to provide additional property
details such as size, number of bedrooms, or number of bathrooms.

The user provides a valid location input, which may be a street address,
latitude/longitude coordinates, or a map click selection.

The system normalizes the provided location to a canonical location ID.

The system determines that no additional property attributes have been
supplied.

The system retrieves baseline assessment data and location-derived
features associated with the canonical location ID. These features may
include neighbourhood indicators, proximity to amenities, and other
open-data signals.

Using only the available location-based information and the baseline
assessment data, the system computes an estimated property value.

Because the estimate is based solely on limited input, the system
calculates a low/high range that reflects increased uncertainty relative
to a fully specified property.

The system displays: - A single estimated property value\
- A low/high range\
- A visible indication that the estimate is based on location-only input
and may have reduced accuracy

The use case ends successfully with a qualified estimate presented to
the user.

------------------------------------------------------------------------

## Alternative Path 2a -- Location Normalization Fails

The user provides a location input.

The system attempts to normalize the input to a canonical location ID.

Normalization fails due to reasons such as: - Invalid address or
coordinate input\
- Geocoding failure\
- Unsupported geographic boundary

Because a canonical location ID cannot be generated, the system cannot
retrieve baseline or location-based features.

The system informs the user that the location could not be processed.

No estimate is produced.

The use case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 4a -- Baseline Assessment Data Unavailable

The user provides a valid location input.

The system successfully normalizes the location to a canonical location
ID.

The system attempts to retrieve baseline assessment data for the
canonical location.

Baseline data is unavailable (for example, the parcel has no assessment
record or the dataset is temporarily unavailable).

Rather than terminating immediately, the system applies fallback logic.

The system retrieves higher-level spatial averages, such as grid-level
or neighbourhood-level averages.

Using these fallback values and available location-derived features, the
system computes an approximate estimate.

The system displays: - A single estimated value\
- A low/high range\
- A visible warning indicating that fallback data was used and accuracy
may be reduced

The use case ends successfully with a qualified estimate.

------------------------------------------------------------------------

## Alternative Path 5a -- Insufficient Data for Even a Fallback Estimate

The user provides a location input.

The system successfully normalizes the location to a canonical location
ID.

The system attempts to retrieve baseline assessment data and fallback
spatial averages.

Both primary and fallback data sources are unavailable or insufficient
to compute an estimate.

The system determines that an estimate cannot be generated reliably.

The system informs the user that there is insufficient data to produce
an estimate for the selected location.

No estimate value or range is displayed.

The use case ends in the Failed End Condition.
