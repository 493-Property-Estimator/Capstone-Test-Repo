# UC-01 -- Fully Dressed Scenario Narratives

**Use Case:** Enter Street Address to Estimate Property Value

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

A general user wants to estimate the value of a property but does not
know its geographic coordinates. The user accesses the Property Value
Estimator system and selects the option to estimate a property value.

The system displays an input field prompting the user to enter a street
address. The user types a complete street address and submits it.

The system validates the address format to ensure it contains the
required structural components (such as street number and street name).
The format is valid.

The system then sends the address to the geocoding service. The
geocoding service successfully returns geographic coordinates
corresponding to the address.

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

## Alternative Path 4a -- Invalid Address Format

A general user selects the estimate option and enters a street address.

The system checks the format of the entered address and detects that
required components are missing or malformed (for example, no street
number or incomplete structure).

The system does not proceed with geocoding. Instead, it displays a clear
validation error message indicating that the address format is invalid
and specifies what information is missing.

The user corrects the address and resubmits it.

The system revalidates the updated input and resumes the normal flow at
Step 3 of the Main Success Scenario.

If the user abandons the process without correcting the address, the use
case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 6a -- Geocoding Failure or No Match

A general user enters a properly formatted street address.

The system validates the format successfully and sends the address to
the geocoding service.

The geocoding service: - Fails due to a temporary service outage, or\
- Returns no matching location for the provided address.

The system detects that no valid coordinates were returned.

The system informs the user that the address could not be found or
verified. It suggests rechecking the spelling or entering a different
address.

The user may: - Enter a corrected or different address, returning to
Step 3 of the Main Success Scenario, or\
- Abandon the request.

If the user abandons the process or repeated attempts fail, the use case
ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 8a -- Partial Data Available for Valuation

A general user enters a valid street address.

The system validates and geocodes the address successfully and
normalizes it to a canonical location ID.

When computing the estimate, the system detects that one or more
open-data features required for full valuation are unavailable (for
example, missing census indicators or temporarily unavailable POI data).

Rather than terminating the process, the system computes a partial
estimate using the available data and the assessment baseline.

The system displays: - A single estimated value\
- A low/high range\
- A visible warning indicating that some data sources were unavailable
and the estimate may have reduced accuracy

The use case ends successfully with a qualified estimate presented to
the user.
