import { createStore } from "./state/store.js";
import { apiClient } from "./services/api/apiClient.js";
import { createMapAdapter } from "./map/mapAdapter.js";
import { createSearchController } from "./features/search/searchController.js";
import { createMapSelectionController } from "./features/mapSelection/mapSelectionController.js";
import { createLayerController } from "./features/layers/layerController.js";
import { createEstimateController } from "./features/estimate/estimateController.js";
import { createWarningController } from "./features/warnings/warningController.js";

const store = createStore();

const mapMessageElement = document.getElementById("map-message");

const mapAdapter = createMapAdapter({
  root: document.getElementById("map-root"),
  messageElement: mapMessageElement,
  onMapClick: () => {},
  onViewportChange: () => {},
  onSelectionCleared() {
    store.setState({
      selectedLocation: null,
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

createSearchController({
  apiClient,
  input: document.getElementById("address-input"),
  submitButton: document.getElementById("search-submit"),
  suggestionsRoot: document.getElementById("suggestions"),
  candidateResultsRoot: document.getElementById("candidate-results"),
  helperText: document.getElementById("search-helper"),
  statusElement: document.getElementById("search-status"),
  onLocationResolved(location) {
    store.setState({ selectedLocation: location });
    mapAdapter.setView(location);
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
  statusElement: document.getElementById("estimate-status"),
  locationSummary: document.getElementById("location-summary"),
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
