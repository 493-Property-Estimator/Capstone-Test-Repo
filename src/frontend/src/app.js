import { createStore } from "./state/store.js";
import { apiClient } from "./services/api/apiClient.js";
import { createMapAdapter } from "./map/mapAdapter.js";
import { createSearchController } from "./features/search/searchController.js";
import { createMapSelectionController } from "./features/mapSelection/mapSelectionController.js";
import { createLayerController } from "./features/layers/layerController.js";
import { createEstimateController } from "./features/estimate/estimateController.js";
import { createWarningController } from "./features/warnings/warningController.js";
import { createPropertyDetailController } from "./features/propertyDetails/propertyDetailController.js";
import { DEFAULT_LOCATION, PREFER_LIVE_API } from "./config.js";

const store = createStore();

const mapMessageElement = document.getElementById("map-message");

function findMatchingProperty(propertyLayer, location) {
  if (!location) {
    return null;
  }

  const selectedId = location.canonical_location_id;
  const selectedCoordinates = location.coordinates;

  return (propertyLayer?.properties || []).find((property) => {
    if (selectedId && property.canonical_location_id === selectedId) {
      return true;
    }

    if (!selectedCoordinates || !property.coordinates) {
      return false;
    }

    return (
      Math.abs(Number(property.coordinates.lat) - Number(selectedCoordinates.lat)) < 0.00001
      && Math.abs(Number(property.coordinates.lng) - Number(selectedCoordinates.lng)) < 0.00001
    );
  }) || null;
}

const mapAdapter = createMapAdapter({
  root: document.getElementById("map-root"),
  messageElement: mapMessageElement,
  onMapClick: () => {},
  onViewportChange: () => {},
  propertyCardElement: document.getElementById("property-hover-card"),
  propertyDetailPanelElement: document.getElementById("property-detail-panel"),
  onPropertySelect: (property) => {
    const location = {
      canonical_location_id: property.canonical_location_id,
      canonical_address: property.canonical_address,
      coordinates: property.coordinates,
      region: "Edmonton",
      neighbourhood: property.details?.neighbourhood || property.neighbourhood || null,
      coverage_status: "supported"
    };
    store.setState({
      selectedLocation: location,
      selectedPropertyDetails: property,
      propertyDetailsDismissed: false
    });
  },
  onSelectionCleared() {
    store.setState({
      selectedLocation: null,
      selectedPropertyDetails: null,
      propertyDetailsDismissed: false,
      estimate: null,
      warningsCollapsed: false
    });
  }
});

const handleMapClick = createMapSelectionController({
  apiClient,
  store,
  mapAdapter,
  mapMessageElement
});

mapAdapter.setClickHandler(handleMapClick);

const searchController = createSearchController({
  apiClient,
  input: document.getElementById("address-input"),
  submitButton: document.getElementById("search-submit"),
  suggestionsRoot: document.getElementById("suggestions"),
  candidateResultsRoot: document.getElementById("candidate-results"),
  helperText: document.getElementById("search-helper"),
  statusElement: document.getElementById("search-status"),
  onLocationResolved(location) {
    const matchedProperty = findMatchingProperty(store.getState().propertyLayer, location);
    store.setState({
      selectedLocation: location,
      selectedPropertyDetails: matchedProperty,
      propertyDetailsDismissed: false
    });
    mapAdapter.setView(location, { zoom: 17 });
  }
});

createLayerController({
  apiClient,
  store,
  controlsRoot: document.getElementById("layer-controls"),
  legendRoot: document.getElementById("layer-legend"),
  statusElement: document.getElementById("layer-status"),
  mapAdapter
});

createEstimateController({
  apiClient,
  store,
  submitButton: document.getElementById("estimate-submit"),
  resetButton: document.getElementById("reset-selection"),
  statusElement: document.getElementById("estimate-status"),
  locationSummary: document.getElementById("location-summary"),
  selectionMeta: document.getElementById("selection-meta"),
  estimatePanel: document.getElementById("estimate-panel"),
  validationMessage: document.getElementById("validation-message"),
  formElements: {
    latitudeInput: document.getElementById("latitude-input"),
    longitudeInput: document.getElementById("longitude-input"),
    bedroomsInput: document.getElementById("bedrooms-input"),
    bathroomsInput: document.getElementById("bathrooms-input"),
    floorAreaInput: document.getElementById("floor-area-input")
  }
});

createWarningController({
  store,
  warningPanel: document.getElementById("warning-panel"),
  warningIndicator: document.getElementById("warning-indicator")
});

createPropertyDetailController({
  store,
  panel: document.getElementById("property-detail-panel"),
  titleElement: document.getElementById("property-detail-title"),
  subtitleElement: document.getElementById("property-detail-subtitle"),
  bodyElement: document.getElementById("property-detail-body"),
  closeButton: document.getElementById("property-detail-close")
});

/* node:coverage disable */
store.subscribe((state) => {
  if (state.selectedPropertyDetails || state.propertyDetailsDismissed || !state.selectedLocation) {
    return;
  }

  const match = findMatchingProperty(state.propertyLayer, state.selectedLocation);

  if (match) {
    store.setState({ selectedPropertyDetails: match });
  }
});
/* node:coverage enable */

/* node:coverage ignore next */
document.getElementById("environment-badge").textContent = PREFER_LIVE_API ? "Auto API" : "Mock API";

document.getElementById("reset-selection").addEventListener("click", () => {
  store.setState({
    selectedLocation: DEFAULT_LOCATION,
    selectedPropertyDetails: null,
    propertyDetailsDismissed: false,
    estimate: null,
    warningsCollapsed: false
  });
  mapAdapter.resetView();
  searchController.clear();
});

export const __app = {
  store,
  mapAdapter,
  searchController
};
