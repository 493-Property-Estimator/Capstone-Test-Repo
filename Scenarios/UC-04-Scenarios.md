# UC-04 -- Fully Dressed Scenario Narratives

**Use Case:** Normalize Property Input to Canonical Location ID

------------------------------------------------------------------------

## Main Success Scenario -- Narrative

The Property Value Estimator system receives a property input that
requires normalization before valuation can proceed. The input may
originate from an address entry, latitude/longitude input, or a map
click interaction.

If the input is an address, the system sends the address to the
geocoding service to obtain geographic coordinates. The geocoding
service successfully returns latitude and longitude corresponding to the
address.

The system verifies that the coordinates fall within the supported
geographic boundary of the system.

The coordinates are confirmed to be within the supported region.

The system queries the spatial database to determine which spatial unit
contains the coordinates. This spatial unit may be a parcel, assessment
lot, grid cell, or other predefined geographic entity.

A matching spatial unit is found.

The system generates a canonical location ID derived from the resolved
spatial unit according to predefined deterministic rules.

The system forwards the canonical location ID to downstream components
(such as valuation, caching, and feature computation modules).

The use case ends successfully with a stable, valid canonical location
ID available for subsequent processing.

------------------------------------------------------------------------

## Alternative Path 2a -- Geocoding Service Fails or Returns No Match

The system receives an address as input and sends it to the geocoding
service.

The geocoding service: - Fails due to outage or timeout, or\
- Returns no matching coordinates for the address.

Because geographic coordinates cannot be obtained, the system cannot
proceed with spatial boundary verification or spatial unit lookup.

The system logs the normalization failure for monitoring and
diagnostics.

The system returns an error indicating that normalization could not be
completed.

No canonical location ID is generated.

The use case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 4a -- Coordinates Outside Supported Geographic Boundary

The system receives coordinates either directly from user input or from
successful geocoding.

The system verifies whether the coordinates fall within the supported
geographic boundary.

The coordinates are determined to be outside the supported region.

The system logs the boundary validation failure.

The system returns an error indicating that the location is outside the
supported geographic area.

No canonical location ID is generated and no downstream processing
occurs.

The use case ends in the Failed End Condition.

------------------------------------------------------------------------

## Alternative Path 5a -- No Parcel or Spatial Unit Found

The system receives valid in-bound coordinates.

The system queries the spatial database to identify a containing parcel
or predefined spatial unit.

No matching parcel or primary spatial unit is found (for example, the
location falls in a road, river, or unassigned area).

Rather than failing immediately, the system applies fallback logic.

The system assigns the location to a fallback spatial unit, such as a
grid cell or nearest valid parcel, according to predefined rules.

The system generates a canonical location ID based on the fallback
spatial unit.

The system forwards the canonical location ID to downstream components.

The use case ends successfully using the fallback spatial unit.

------------------------------------------------------------------------

## Alternative Path 6a -- Canonical ID Conflict or Duplication Detected

The system resolves the spatial unit and attempts to generate a
canonical location ID.

During ID generation, the system detects: - A duplication conflict, or\
- An inconsistency with previously generated identifiers.

The system applies deterministic resolution rules to ensure stability
and uniqueness (for example, hashing the spatial unit ID with versioning
information).

The system validates that the resulting canonical location ID is unique
and consistent with system constraints.

Once the ID is confirmed valid, the system forwards it to downstream
components.

The use case ends successfully with a stable and unique canonical
location ID.
