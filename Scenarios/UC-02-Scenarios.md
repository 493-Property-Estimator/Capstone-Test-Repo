# UC-02 -- Fully Dressed Scenario Narratives

**Use Case:** Enter Latitude/Longitude to Estimate Property Value

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

A general user wants to estimate the value of a property located in an
area without a formal street address. The user accesses the Property
Value Estimator system and selects the option to estimate a property
value.

The system prompts the user to enter geographic coordinates in the form
of latitude and longitude.

The user enters numeric latitude and longitude values and submits the
request.

The system validates that: - The latitude is within the valid range of
−90 to +90 degrees. - The longitude is within the valid range of −180 to
+180 degrees.

The entered values pass syntactic validation.

The system then verifies that the coordinates fall within the supported
geographic boundary of the system (e.g., within the City of Edmonton).

The coordinates fall within the supported area.

The system converts the coordinates into its internal canonical location
identifier to ensure consistent downstream processing.

Using this canonical location, the system computes the property value
estimate based on the assessment baseline and relevant open-data
features.

The system displays to the user: - A single estimated property value\
- A low/high range\
- Supporting explanatory information

The use case ends successfully with the estimate visible to the user.

------------------------------------------------------------------------

## Alternative Path 4a -- Invalid or Out-of-Range Coordinates

A general user selects the estimate option and enters latitude and
longitude values.

The system validates the coordinate values and detects one of the
following: - The values are not numeric. - The latitude is outside the
range −90 to +90. - The longitude is outside the range −180 to +180.

The system does not proceed to geographic boundary verification or
valuation.

Instead, the system displays a validation error message indicating the
acceptable coordinate ranges and input format.

The user corrects the coordinate values and resubmits them.

The system revalidates the corrected values and resumes the normal flow
at Step 3 of the Main Success Scenario.

If the user abandons the process without correcting the input, the use
case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 5a -- Coordinates Outside Supported Geographic Boundary

A general user enters latitude and longitude values.

The system validates that the values are syntactically correct and
within valid numeric ranges.

The system then verifies whether the coordinates fall within the
supported geographic boundary of the Property Value Estimator system.

The coordinates are determined to be outside the supported region.

The system informs the user that the specified location is outside the
supported geographic area and cannot be processed.

No canonical location ID is generated and no valuation is computed.

The use case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 7a -- Partial Valuation Data Available

A general user enters valid latitude and longitude values.

The system validates the coordinates and confirms that they fall within
the supported geographic boundary.

The system converts the coordinates into a canonical location ID.

During the valuation process, the system detects that one or more
open-data features required for full valuation are unavailable (for
example, missing neighbourhood indicators or temporarily unavailable POI
datasets).

Rather than terminating the process, the system computes a partial
estimate using the available data and the assessment baseline.

The system displays: - A single estimated property value\
- A low/high range\
- A visible warning indicating that some data sources were unavailable
and that the estimate may have reduced accuracy

The use case ends successfully with a qualified estimate presented to
the user.
