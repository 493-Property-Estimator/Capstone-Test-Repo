import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse, wait } from "./helpers/fakeDom.js";
import { installMapLibre, latestMapInstance } from "./helpers/fakeMapLibre.js";

function ids() {
  return [
    { id: "map-root", rect: { left: 0, top: 0, width: 900, height: 600 } },
    { id: "map-message" },
    { id: "property-hover-card", rect: { left: 0, top: 0, width: 220, height: 120 } },
    { id: "address-input", tagName: "input" },
    { id: "search-submit", tagName: "button" },
    { id: "suggestions" },
    { id: "candidate-results" },
    { id: "search-helper" },
    { id: "search-status" },
    { id: "layer-controls" },
    { id: "layer-legend" },
    { id: "layer-status" },
    { id: "estimate-submit", tagName: "button" },
    { id: "reset-selection", tagName: "button" },
    { id: "estimate-status" },
    { id: "location-summary" },
    { id: "selection-meta" },
    { id: "estimate-panel" },
    { id: "validation-message" },
    { id: "latitude-input", tagName: "input" },
    { id: "longitude-input", tagName: "input" },
    { id: "bedrooms-input", tagName: "input" },
    { id: "bathrooms-input", tagName: "input" },
    { id: "floor-area-input", tagName: "input" },
    { id: "include-breakdown-input", tagName: "input" },
    { id: "include-top-factors-input", tagName: "input" },
    { id: "include-warnings-input", tagName: "input" },
    { id: "include-layers-context-input", tagName: "input" },
    { id: "factor-crime-input", tagName: "input" },
    { id: "factor-schools-input", tagName: "input" },
    { id: "factor-green-space-input", tagName: "input" },
    { id: "factor-commute-input", tagName: "input" },
    { id: "weight-crime-input", tagName: "input" },
    { id: "weight-schools-input", tagName: "input" },
    { id: "weight-green-space-input", tagName: "input" },
    { id: "weight-commute-input", tagName: "input" },
    { id: "weight-crime-output" },
    { id: "weight-schools-output" },
    { id: "weight-green-space-output" },
    { id: "weight-commute-output" },
    { id: "warning-panel" },
    { id: "warning-indicator", tagName: "button" },
    { id: "environment-badge" },
    { id: "ingestion-form", tagName: "form" },
    { id: "ingestion-reset", tagName: "button" },
    { id: "ingestion-status-pill" },
    { id: "ingestion-status-label" },
    { id: "ingestion-feedback" },
    { id: "ingestion-progress" },
    { id: "ingestion-progress-bar" },
    { id: "ingestion-source-name", tagName: "input" },
    { id: "ingestion-dataset-type", tagName: "select" },
    { id: "ingestion-file-input", tagName: "input" },
    { id: "ingestion-trigger", tagName: "select" },
    { id: "ingestion-validate-only", tagName: "input" },
    { id: "ingestion-overwrite", tagName: "input" },
    { id: "property-detail-panel" },
    { id: "property-detail-title" },
    { id: "property-detail-subtitle" },
    { id: "property-detail-body" },
    { id: "property-detail-close", tagName: "button" }
  ];
}

const { document } = installDomGlobals({ ids: ids() });
installMapLibre(window);
document.querySelectorAll = undefined;

globalThis.fetch = async (url) => {
  if (String(url).endsWith("/app.env")) {
    return createMockResponse("PREFER_LIVE_API=1\nALLOW_MOCK_FALLBACK=0\n");
  }
  if (String(url).includes("/api/v1/properties/")) {
    throw new Error("offline");
  }
  return createMockResponse({});
};

const { __app } = await import("../src/app.js");
await wait(10);

test("app hydration falls back cleanly when detail fetch fails or property id is missing", async () => {
  __app.store.updatePropertyLayer({
    enabled: true,
    renderMode: "property",
    properties: [
      {
        canonical_location_id: "loc-offline",
        canonical_address: "Offline Detail Property",
        coordinates: { lat: 53.55, lng: -113.49 }
      }
    ],
    clusters: []
  });

  __app.store.setState({
    selectedLocation: {
      canonical_location_id: "loc-offline",
      canonical_address: "Offline Detail Property",
      coordinates: { lat: 53.55, lng: -113.49 }
    },
    selectedPropertyDetails: null,
    propertyDetailsDismissed: false
  });
  await wait(25);
  assert.equal(
    __app.store.getState().selectedPropertyDetails?.canonical_location_id,
    "loc-offline"
  );

  const map = latestMapInstance();
  map.emit(
    "click",
    {
      features: [
        {
          geometry: { coordinates: [-113.48, 53.56] },
          properties: {
            canonical_address: "No ID property",
            coordinates: { lat: 53.56, lng: -113.48 }
          }
        }
      ],
      originalEvent: { button: 0 }
    },
    "assessment_properties-points"
  );
  await wait(25);
  assert.equal(
    __app.store.getState().selectedPropertyDetails?.canonical_address,
    "No ID property"
  );
});
