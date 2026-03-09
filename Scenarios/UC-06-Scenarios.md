# UC-06 -- Fully Dressed Scenario Narratives

**Use Case:** Provide Basic Property Details for More Accurate Estimate

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

A general user wants a more accurate property value estimate than what
is available from location alone. The user accesses the Property Value
Estimator system and provides a valid location input, such as a street
address, latitude/longitude, or map click.

The system normalizes the location to a canonical location ID.

The user then provides one or more basic property attributes, such as
total square footage, number of bedrooms, and number of bathrooms.

The system validates the provided attributes. It confirms that: - The
square footage is a positive numeric value. - The number of bedrooms is
a non-negative numeric value. - The number of bathrooms is a
non-negative numeric value.

The provided attributes pass validation.

The system retrieves baseline assessment data and location-derived
features associated with the canonical location ID.

Using the baseline estimate as a starting point, the system adjusts the
valuation model to incorporate the validated property attributes. For
example, the estimate may increase for larger square footage or
additional bedrooms.

The system computes a refined estimated property value.

Because additional property details have been incorporated, the system
calculates a low/high range that reflects reduced uncertainty compared
to a location-only estimate.

The system displays: - A single estimated property value\
- A low/high range\
- A visible indication that user-provided property details were
incorporated into the estimate

The use case ends successfully with a refined and qualified estimate
presented to the user.

------------------------------------------------------------------------

## Alternative Path 2a -- Location Normalization Fails

The user provides a location input along with property attributes.

The system attempts to normalize the location to a canonical location
ID.

Normalization fails due to reasons such as invalid address input,
geocoding failure, or unsupported geographic boundary.

Because a canonical location ID cannot be generated, the system cannot
retrieve baseline assessment data or apply attribute adjustments.

The system informs the user that the location could not be processed.

No estimate is produced.

The use case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 4a -- Property Attribute Validation Fails

The user provides a valid location input and one or more property
attributes.

The system normalizes the location successfully.

The system validates the provided attributes and detects invalid values,
such as: - Negative square footage - Non-numeric bedroom or bathroom
values - Clearly unrealistic values outside accepted system constraints

The system does not proceed to valuation.

Instead, the system displays actionable validation error messages
indicating which fields are invalid and why.

The user corrects the invalid attributes and resubmits them.

The system revalidates the updated inputs and resumes the normal flow at
Step 3 of the Main Success Scenario.

If the user abandons the process without correcting the attributes, the
use case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 6a -- Partial Attribute Set Provided

The user provides a valid location input and only some property
attributes (for example, square footage but no bedroom count).

The system normalizes the location successfully.

The system validates the provided attributes and confirms they are
valid.

The system retrieves baseline assessment data and location-derived
features.

The system applies valuation adjustments using only the valid attributes
that were supplied.

The system computes a refined estimate using available data.

The system calculates a low/high range that reflects intermediate
uncertainty (more precise than location-only but less precise than fully
specified attributes).

The system displays: - A single estimated value\
- A low/high range\
- An indication that only some user-provided attributes were
incorporated

The use case ends successfully with a qualified estimate.

------------------------------------------------------------------------

## Alternative Path 7a -- Required Baseline or Feature Data Partially Unavailable

The user provides a valid location input and valid property attributes.

The system normalizes the location successfully.

The system validates the attributes successfully.

During data retrieval, the system detects that some baseline or
location-derived features are unavailable.

Rather than terminating the process, the system computes an estimate
using available data and the user-provided attributes.

The system displays: - A single estimated value\
- A low/high range\
- A visible warning indicating that some data sources were unavailable
and that accuracy may be reduced

The use case ends successfully with a qualified estimate presented to
the user.
