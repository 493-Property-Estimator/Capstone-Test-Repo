import { createStore } from "./state/store.js";
import { apiClient } from "./services/api/apiClient.js";
import { createMapAdapter } from "./map/mapAdapter.js";
import { createSearchController } from "./features/search/searchController.js";
import { createMapSelectionController } from "./features/mapSelection/mapSelectionController.js";
import { createLayerController } from "./features/layers/layerController.js";
import { createEstimateController } from "./features/estimate/estimateController.js";
import { createWarningController } from "./features/warnings/warningController.js";
import { createPropertyDetailController } from "./features/propertyDetails/propertyDetailController.js";
import { createIngestionController } from "./features/ingestion/ingestionController.js";
import { DEFAULT_LOCATION, PREFER_LIVE_API } from "./config.js";

const store = createStore();

const mapMessageElement = document.getElementById("map-message");
const propertyDetailCache = new Map();

const noopMapClick = () => {};

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
function setupAppNavigation() {
  const pageIds = new Set(["estimator", "ingestion"]);
  const menuButton = document.getElementById("app-menu-toggle");
  const sidebar = document.getElementById("app-sidebar-nav");
  const overlay = document.getElementById("app-sidebar-overlay");
  const links = typeof document.querySelectorAll === "function"
    ? Array.from(document.querySelectorAll("[data-page-target]"))
    : [];

  const setSidebarOpen = (open) => {
    if (!sidebar || !overlay || !menuButton) {
      return;
    }

    sidebar.classList.toggle("is-open", open);
    overlay.classList.toggle("is-hidden", !open);
    menuButton.setAttribute("aria-expanded", String(open));
  };

  const setPage = (pageId) => {
    if (!pageIds.has(pageId)) {
      return;
    }

    if (document.body?.dataset) {
      document.body.dataset.page = pageId;
    } else if (typeof document.body?.setAttribute === "function") {
      document.body.setAttribute("data-page", pageId);
    }
    links.forEach((link) => {
      link.classList.toggle("is-active", link.dataset.pageTarget === pageId);
    });

    setSidebarOpen(false);
  };

  menuButton?.addEventListener("click", () => {
    const isOpen = sidebar?.classList.contains("is-open");
    setSidebarOpen(!isOpen);
  });

  overlay?.addEventListener("click", () => setSidebarOpen(false));

  links.forEach((link) => {
    link.addEventListener("click", () => {
      setPage(link.dataset.pageTarget);
    });
  });

  const initialPage = document.body?.dataset?.page || "estimator";
  setPage(initialPage);
}

/* node:coverage disable */
function mergePropertyDetails(baseProperty, detailedProperty) {
  if (!detailedProperty) {
    return baseProperty;
  }

  return {
    ...baseProperty,
    ...detailedProperty,
    details: {
      ...(baseProperty?.details || {}),
      ...(detailedProperty?.details || {})
    }
  };
}
/* node:coverage enable */

async function hydratePropertyDetails(property) {
  if (!property?.canonical_location_id) {
    return property || null;
  }

  const cachedProperty = propertyDetailCache.get(property.canonical_location_id);
  if (cachedProperty) {
    return mergePropertyDetails(property, cachedProperty);
  }

  if (property.details && Object.keys(property.details).length > 0) {
    propertyDetailCache.set(property.canonical_location_id, property);
    return property;
  }

  try {
    const response = await apiClient.getPropertyDetail(property.canonical_location_id);
    const detailedProperty = response?.property || null;
    const mergedProperty = mergePropertyDetails(property, detailedProperty);
    propertyDetailCache.set(property.canonical_location_id, mergedProperty);
    return mergedProperty;
  } catch {
    return property;
  }
}

setupAppNavigation();

const mapAdapter = createMapAdapter({
  root: document.getElementById("map-root"),
  messageElement: mapMessageElement,
  onMapClick: noopMapClick,
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
    const baseState = {
      selectedLocation: location,
      selectedPropertyDetails: property,
      propertyDetailsDismissed: false
    };
    store.setState(baseState);

    hydratePropertyDetails(property).then((detailedProperty) => {
      if (!detailedProperty?.canonical_location_id) {
        return;
      }

      const selectedId = store.getState().selectedLocation?.canonical_location_id;
      if (selectedId !== detailedProperty.canonical_location_id) {
        return;
      }

      store.setState({ selectedPropertyDetails: detailedProperty });
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

noopMapClick();

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
    floorAreaInput: document.getElementById("floor-area-input"),
    includeBreakdownInput: document.getElementById("include-breakdown-input"),
    includeTopFactorsInput: document.getElementById("include-top-factors-input"),
    includeWarningsInput: document.getElementById("include-warnings-input"),
    includeLayersContextInput: document.getElementById("include-layers-context-input"),
    factorCrimeInput: document.getElementById("factor-crime-input"),
    factorSchoolsInput: document.getElementById("factor-schools-input"),
    factorGreenSpaceInput: document.getElementById("factor-green-space-input"),
    factorCommuteInput: document.getElementById("factor-commute-input"),
    weightCrimeInput: document.getElementById("weight-crime-input"),
    weightSchoolsInput: document.getElementById("weight-schools-input"),
    weightGreenSpaceInput: document.getElementById("weight-green-space-input"),
    weightCommuteInput: document.getElementById("weight-commute-input"),
    weightCrimeOutput: document.getElementById("weight-crime-output"),
    weightSchoolsOutput: document.getElementById("weight-schools-output"),
    weightGreenSpaceOutput: document.getElementById("weight-green-space-output"),
    weightCommuteOutput: document.getElementById("weight-commute-output")
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

createIngestionController({
  apiClient,
  form: document.getElementById("ingestion-form"),
  resetButton: document.getElementById("ingestion-reset"),
  statusPill: document.getElementById("ingestion-status-pill"),
  statusLabel: document.getElementById("ingestion-status-label"),
  feedbackRoot: document.getElementById("ingestion-feedback"),
  progressRoot: document.getElementById("ingestion-progress"),
  progressBar: document.getElementById("ingestion-progress-bar"),
  fields: {
    sourceNameInput: document.getElementById("ingestion-source-name"),
    datasetTypeInput: document.getElementById("ingestion-dataset-type"),
    fileInput: document.getElementById("ingestion-file-input"),
    triggerInput: document.getElementById("ingestion-trigger"),
    validateOnlyInput: document.getElementById("ingestion-validate-only"),
    overwriteInput: document.getElementById("ingestion-overwrite")
  }
});

/* node:coverage disable */
store.subscribe((state) => {
  if (state.selectedPropertyDetails || state.propertyDetailsDismissed || !state.selectedLocation) {
    return;
  }

  const match = findMatchingProperty(state.propertyLayer, state.selectedLocation);

  if (match) {
    hydratePropertyDetails(match).then((detailedProperty) => {
      if (!detailedProperty?.canonical_location_id) {
        return;
      }

      const selectedId = store.getState().selectedLocation?.canonical_location_id;
      if (selectedId !== detailedProperty.canonical_location_id) {
        return;
      }

      if (store.getState().selectedPropertyDetails) {
        return;
      }

      store.setState({ selectedPropertyDetails: detailedProperty });
    });
  }
});
/* node:coverage enable */

/* node:coverage ignore next */
const environmentBadge = document.getElementById("environment-badge");
if (environmentBadge) {
  environmentBadge.textContent = PREFER_LIVE_API ? "Auto API" : "Mock API";
}

const resetSelectionButton = document.getElementById("reset-selection");
resetSelectionButton?.addEventListener("click", () => {
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
  searchController,
  findMatchingProperty
};
