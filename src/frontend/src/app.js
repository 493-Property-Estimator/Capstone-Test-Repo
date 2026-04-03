import { createStore } from "./state/store.js";
import { apiClient } from "./services/api/apiClient.js";
import { createMapAdapter } from "./map/mapAdapter.js";
import { createSearchController } from "./features/search/searchController.js";
import { createMapSelectionController } from "./features/mapSelection/mapSelectionController.js";
import { createLayerController } from "./features/layers/layerController.js";
import { createEstimateController } from "./features/estimate/estimateController.js";
import { createWarningController } from "./features/warnings/warningController.js";
import { DEFAULT_LOCATION, USE_MOCK_API } from "./config.js";

const store = createStore();

const mapMessageElement = document.getElementById("map-message");

const mapAdapter = createMapAdapter({
  root: document.getElementById("map-root"),
  messageElement: mapMessageElement,
  onMapClick: () => {},
  onViewportChange: () => {},
<<<<<<< HEAD:src/frontend/src/app.js
  onSelectionCleared() {
    store.setState({
      selectedLocation: null,
      estimate: null,
      warningsCollapsed: false
    });
  }
=======
  propertyCardElement: document.getElementById("property-hover-card")
>>>>>>> master:frontend/src/app.js
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
<<<<<<< HEAD:src/frontend/src/app.js
=======

document.getElementById("environment-badge").textContent = USE_MOCK_API
  ? "Mock API"
  : "Live API";

document.getElementById("example-address-1").addEventListener("click", () => {
  searchController.setQuery("10234 98 Street NW, Edmonton");
  searchController.resolveQuery("10234 98 Street NW, Edmonton");
});

document.getElementById("example-address-2").addEventListener("click", () => {
  searchController.setQuery("5432 111 Avenue NW, Edmonton");
  searchController.resolveQuery("5432 111 Avenue NW, Edmonton");
});

document.getElementById("example-property-abbottsfield").addEventListener("click", () => {
  const location = {
    canonical_location_id: "loc-d1c3fbc1d0aa7f62",
    canonical_address: "870 ABBOTTSFIELD ROAD NW, Edmonton, AB",
    coordinates: {
      lat: 53.57632901357068,
      lng: -113.39230350026378
    },
    region: "Edmonton",
    neighbourhood: "ABBOTTSFIELD",
    coverage_status: "supported"
  };

  store.setState({ selectedLocation: location });
  mapAdapter.setView(location);
  document.getElementById("latitude-input").value = String(location.coordinates.lat);
  document.getElementById("longitude-input").value = String(location.coordinates.lng);
});

document.getElementById("search-ambiguous").addEventListener("click", () => {
  searchController.setQuery("123 Main Street");
  searchController.resolveQuery("123 Main Street");
});

document.getElementById("search-unsupported").addEventListener("click", () => {
  searchController.setQuery("123 Main Street, Calgary, AB");
  searchController.resolveQuery("123 Main Street, Calgary, AB");
});

document.getElementById("reset-selection").addEventListener("click", () => {
  store.setState({
    selectedLocation: DEFAULT_LOCATION,
    estimate: null,
    warningsCollapsed: false
  });
  mapAdapter.resetView();
  searchController.clear();
});
>>>>>>> master:frontend/src/app.js
