# Feature Specification: Toggle Open-Data Layers in the Map UI

**Feature Branch**: `025-open-data-layers`  
**Created**: 2026-03-10  
**Status**: Draft  
**Input**: User description derived from `Use Cases/UC-25.md`, `Scenarios/UC-25-Scenarios.md`, and `Acceptance Tests/UC-25-AT.md`

## Summary / Goal

Allow a general user to toggle open-data layers on the map so they can visually explore area context that may influence a property's estimated value.

## Actors

- **Primary Actor**: General User
- **Secondary Actors**: Map Rendering Engine, Layer Data API, Feature Database

## Preconditions

- User has the map UI open and operational.
- The requested dataset is available in the backend or cached tile server.
- User has network connectivity.

## Triggers

- User checks or unchecks a map layer toggle in the UI.

## Assumptions

- The map UI already provides the base map experience where layer overlays can be added or removed.
- The set of expected open-data layers includes at least the layers named in the use case and acceptance tests.
- Scenario narratives are supporting detail only; the use case and acceptance tests remain the source of truth.

## Dependencies

- Availability of the map rendering engine
- Availability of the Layer Data API for the current map bounding box
- Availability of the feature database or cached layer dataset source

## Implementation Constraints

- Backend and service-side implementation must remain in Python.
- Frontend implementation must remain in vanilla HTML, CSS, and JavaScript.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn map layers on and off (Priority: P1)

As a general user, I want to enable and disable open-data layers so I can visually inspect different map overlays without leaving the map view.

**Why this priority**: The core value of UC-25 is giving the user direct control over which contextual layers are visible on the map.

**Independent Test**: Can be fully tested by opening the layer panel, enabling one or more layers, verifying the overlays and legend appear, then disabling a layer and confirming it is fully removed.

**Acceptance Scenarios**:

1. **Given** the map UI is loaded, **When** the user opens the layer controls, **Then** labeled toggles for the expected layers are visible with readable default states. (`AT-UC25-001`)
2. **Given** the user enables a single available layer, **When** the system fetches and renders the layer data, **Then** the overlay and matching legend appear on the map. (`AT-UC25-002`)
3. **Given** a layer is already enabled, **When** the user disables it, **Then** the overlay and legend entry are removed with no residual artifacts. (`AT-UC25-003`)
4. **Given** the user enables multiple layers, **When** the overlays are rendered, **Then** all enabled layers remain visible and distinguishable, and disabling one does not affect the others. (`AT-UC25-004`)

---

### User Story 2 - Keep layers in sync with map movement and heavy data (Priority: P1)

As a general user, I want active layers to stay aligned with the current map view and remain usable even when datasets are large or toggles change rapidly.

**Why this priority**: UC-25 explicitly includes refetching by map bounds, progressive loading, and rapid-toggle protection as core behavioral requirements.

**Independent Test**: Can be fully tested by enabling a layer, panning or zooming the map, rapidly toggling layers, and enabling a heavy layer while confirming the UI stays responsive and reflects the final requested state.

**Acceptance Scenarios**:

1. **Given** at least one layer is enabled, **When** the user pans or zooms within supported levels, **Then** the overlay updates for the new visible region and requests are debounced. (`AT-UC25-005`)
2. **Given** a large layer is enabled, **When** the dataset loads slowly, **Then** the UI shows loading progress, renders data progressively, and remains responsive. (`AT-UC25-006`)
3. **Given** the user toggles a layer repeatedly in quick succession, **When** the interaction settles, **Then** the final toggle state is respected without request spam or stuck loading indicators. (`AT-UC25-007`)

---

### User Story 3 - Handle missing or partial layer data gracefully (Priority: P2)

As a general user, I want the map to explain when a layer cannot be fully shown so I understand whether the problem is an outage or incomplete coverage.

**Why this priority**: Graceful degradation is explicitly required for API outage and partial-coverage conditions and prevents misleading map interpretation.

**Independent Test**: Can be fully tested by simulating a layer API outage and by enabling a layer in a region with incomplete coverage, then verifying the user sees the correct warning and map behavior.

**Acceptance Scenarios**:

1. **Given** the Layer Data API is unavailable, **When** the user enables a layer, **Then** the UI shows "Layer unavailable", reverts or disables the toggle, and leaves no broken artifacts. (`AT-UC25-008`)
2. **Given** a layer has incomplete data for the current region, **When** the user enables that layer, **Then** the system renders the available data and warns that coverage is incomplete. (`AT-UC25-009`)

### Edge Cases

- The user toggles multiple layers rapidly.
- A large layer dataset loads slowly.
- The Layer Data API is unavailable.
- Layer coverage is incomplete for the current region.
- Rendering performance degrades on the current device or browser.
- The user zooms out beyond the maximum supported resolution for a fine-grained layer.

## Requirements *(mandatory)*

### Main Flow (verbatim from use case)

1. **User** opens the map UI.
2. **System** displays the base map and a panel containing layer toggles (schools, parks, census boundaries, assessment zones, etc.).
3. **User** selects a layer (e.g., "Schools").
4. **System** determines whether the layer is already cached locally.
5. **System** sends a request to the Layer Data API for the layer dataset in the current map bounding box.
6. **Layer Data API** returns geospatial data for the layer (points, polygons, or heatmap values).
7. **System** renders the layer on top of the base map using appropriate styling.
8. **System** updates the legend/key for the layer (symbols, heatmap intensity scale).
9. **User** pans/zooms the map.
10. **System** dynamically requests additional layer data as the visible region changes.
11. **User** unchecks the layer toggle.
12. **System** removes the layer overlay and legend entry.

### Alternate Flows (verbatim from use case)

- **3a**: User toggles multiple layers rapidly
  - **3a1**: System debounces requests to avoid excessive API calls.
  - **3a2**: System prioritizes the most recent toggle state.
- **5a**: Layer dataset is large and slow to load
  - **5a1**: System shows loading spinner.
  - **5a2**: System loads the dataset progressively (tile-based or chunk-based).
  - **5a3**: Layer becomes visible as partial data arrives.
- **6b**: Layer data exists but is incomplete for current region
  - **6b1**: System renders what is available.
  - **6b2**: System displays a warning that coverage is incomplete.
- **7a**: Rendering performance is poor (device/browser limitations)
  - **7a1**: System reduces rendering detail (simplifies polygons, reduces point density).
  - **7a2**: System warns user that performance mode is active.
- **9a**: User zooms out beyond maximum supported resolution
  - **9a1**: System hides fine-grained layers automatically.
  - **9a2**: System displays message: "Zoom in to view this layer."

### Exception / Error Flows (verbatim from use case)

- **6a**: Layer Data API is unavailable
  - **6a1**: System displays "Layer unavailable" message.
  - **6a2**: System logs error for monitoring and disables toggle temporarily.

### Data Involved

- Layer toggle state
- Layer names such as schools, parks/green spaces, census boundaries, assessment zones, and crime heatmaps
- Current map bounding box
- Geospatial layer data for points, polygons, or heatmap values
- Layer legend or key content, including symbols or heatmap intensity scale
- Layer availability status
- Layer coverage completeness status

### Functional Requirements

- **FR-01-001**: The system MUST display a layer panel or control set containing readable toggles for the expected map layers, and each toggle MUST show a default state.
- **FR-01-002**: When the user enables a layer, the system MUST determine whether that layer is already cached locally, determine the current map bounding box, and request that layer's data for the visible region from the Layer Data API as needed.
- **FR-01-003**: When a layer request is in progress, the system MUST show a loading indicator for that layer.
- **FR-01-004**: When layer data is returned, the system MUST render the layer overlay on top of the base map and update the legend or key for that layer.
- **FR-01-005**: When the user disables an enabled layer, the system MUST remove the layer overlay and its legend entry without leaving residual markers or artifacts.
- **FR-01-006**: The system MUST support multiple enabled layers at the same time, keep them distinguishable, and ensure toggling one layer does not affect other enabled layers.
- **FR-01-007**: When the user pans or zooms the map while a layer is enabled, the system MUST request additional layer data for the new visible region and update the overlay accordingly.
- **FR-01-008**: The system MUST debounce layer-related requests to avoid excessive API calls during rapid toggles or map movement.
- **FR-01-009**: When the user toggles layers rapidly, the system MUST prioritize the most recent toggle state and avoid stuck loading indicators.
- **FR-01-010**: When a layer dataset is large and slow to load, the system MUST show a loading indicator, load the dataset progressively, and make the layer visible as partial data arrives.
- **FR-01-011**: When the Layer Data API is unavailable, the system MUST display a "Layer unavailable" message, disable the affected toggle temporarily or revert it, leave no broken map artifacts, and log the error for monitoring.
- **FR-01-012**: When layer data is incomplete for the current region, the system MUST render the available data and display a warning that coverage is incomplete.
- **FR-01-013**: When rendering performance is poor because of device or browser limitations, the system MUST reduce rendering detail and warn the user that performance mode is active.
- **FR-01-014**: When the user zooms out beyond the maximum supported resolution for a fine-grained layer, the system MUST hide that layer automatically and display a message instructing the user to zoom in to view it.
- **FR-01-015**: When a rendered layer feature supports inspection, the user MUST be able to select that feature and view its available layer details.
- **FR-01-016**: Layer rendering and updates MUST remain responsive during successful enable, pan, zoom, and progressive-loading interactions.

### Traceability

#### Acceptance Tests to Functional Requirements

| Acceptance Test | Related FRs |
| --- | --- |
| AT-UC25-001 | FR-01-001 |
| AT-UC25-002 | FR-01-002, FR-01-003, FR-01-004, FR-01-015, FR-01-016 |
| AT-UC25-003 | FR-01-005 |
| AT-UC25-004 | FR-01-006 |
| AT-UC25-005 | FR-01-007, FR-01-008 |
| AT-UC25-006 | FR-01-010, FR-01-016 |
| AT-UC25-007 | FR-01-008, FR-01-009 |
| AT-UC25-008 | FR-01-011 |
| AT-UC25-009 | FR-01-012 |

#### Flow Sections to Functional Requirements

| Flow Step or Section | Related FRs |
| --- | --- |
| Main Flow 1-3 | FR-01-001 |
| Main Flow 4-8 | FR-01-002, FR-01-003, FR-01-004 |
| Main Flow 9-10 | FR-01-007, FR-01-008 |
| Main Flow 11-12 | FR-01-005 |
| Alternate Flow 3a | FR-01-008, FR-01-009 |
| Alternate Flow 5a | FR-01-010, FR-01-016 |
| Alternate Flow 6b | FR-01-012 |
| Alternate Flow 7a | FR-01-013, FR-01-016 |
| Alternate Flow 9a | FR-01-014 |
| Exception Flow 6a | FR-01-011 |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of map UI loads expose readable layer toggles for the expected layers before any layer is enabled.
- **SC-002**: In acceptance testing, 100% of successful single-layer and multi-layer enable actions display the expected overlays and matching legend entries for the current map view.
- **SC-003**: In acceptance testing, 100% of pan, zoom, large-dataset, and rapid-toggle scenarios preserve a responsive UI and converge to the correct final visible-layer state.
- **SC-004**: In acceptance testing, 100% of simulated outage and partial-coverage scenarios produce explicit user feedback without broken or misleading map overlays.
