import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";
import { installMapLibre } from "./helpers/fakeMapLibre.js";

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
    { id: "app-menu-toggle", tagName: "button" },
    { id: "app-sidebar-nav" },
    { id: "app-sidebar-overlay" },
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
globalThis.fetch = async (url) => {
  if (String(url).endsWith("/app.env")) {
    return createMockResponse("PREFER_LIVE_API=0\n");
  }
  if (String(url).includes("./mock-data/assessment-properties-tiles/index.json")) {
    return createMockResponse({ tiles: [] });
  }
  if (String(url).includes("./mock-data/assessment-properties.geojson")) {
    return createMockResponse({ type: "FeatureCollection", features: [] });
  }
  return createMockResponse({});
};

// Provide `document.querySelectorAll` and `document.body.dataset` so app navigation
// covers dataset + link branches in app.js.
document.body.dataset = { page: "estimator" };
const estimatorLink = document.createElement("a");
estimatorLink.dataset = { pageTarget: "estimator" };
const ingestionLink = document.createElement("a");
ingestionLink.dataset = { pageTarget: "ingestion" };
const bogusLink = document.createElement("a");
bogusLink.dataset = { pageTarget: "bogus" };
document.querySelectorAll = () => [estimatorLink, ingestionLink, bogusLink];

const { __app } = await import("../src/app.js");

test("app helper matches properties by id, by coordinates, and handles missing inputs", () => {
  const propertyLayer = {
    properties: [
      {
        canonical_location_id: "loc-1",
        coordinates: { lat: 53.5, lng: -113.4 }
      },
      {
        canonical_location_id: "loc-2",
        coordinates: { lat: 53.6, lng: -113.5 }
      },
      {
        canonical_location_id: "loc-3"
      }
    ]
  };

  assert.equal(__app.findMatchingProperty(propertyLayer, null), null);
  assert.equal(
    __app.findMatchingProperty(undefined, { canonical_location_id: "loc-1" }),
    null
  );
  assert.equal(
    __app.findMatchingProperty(propertyLayer, { canonical_location_id: "loc-2" })?.canonical_location_id,
    "loc-2"
  );
  assert.equal(
    __app.findMatchingProperty(propertyLayer, {
      canonical_location_id: null,
      coordinates: null
    }),
    null
  );
  assert.equal(
    __app.findMatchingProperty(propertyLayer, {
      coordinates: { lat: 53.5, lng: -113.4 }
    })?.canonical_location_id,
    "loc-1"
  );
  assert.equal(
    __app.findMatchingProperty(propertyLayer, {
      coordinates: { lat: 0, lng: 0 }
    }),
    null
  );
});

test("app navigation opens sidebar and switches pages", () => {
  const menuToggle = document.getElementById("app-menu-toggle");
  const sidebar = document.getElementById("app-sidebar-nav");
  const overlay = document.getElementById("app-sidebar-overlay");

  menuToggle.click();
  assert.equal(sidebar.classList.contains("is-open"), true);
  assert.equal(overlay.classList.contains("is-hidden"), false);
  assert.equal(menuToggle.getAttribute("aria-expanded"), "true");

  overlay.click();
  assert.equal(sidebar.classList.contains("is-open"), false);
  assert.equal(overlay.classList.contains("is-hidden"), true);
  assert.equal(menuToggle.getAttribute("aria-expanded"), "false");

  bogusLink.click();
  assert.equal(document.body.dataset.page, "estimator");

  ingestionLink.click();
  assert.equal(document.body.dataset.page, "ingestion");
  assert.equal(ingestionLink.classList.contains("is-active"), true);
  assert.equal(estimatorLink.classList.contains("is-active"), false);
});

test("app reset handler restores default selection state", () => {
  __app.store.setState({
    selectedLocation: {
      canonical_location_id: "loc-1",
      canonical_address: "Changed",
      coordinates: { lat: 53.5, lng: -113.4 }
    },
    selectedPropertyDetails: {
      canonical_location_id: "loc-1"
    },
    propertyDetailsDismissed: true,
    estimate: { estimate: { value: 123456 } },
    warningsCollapsed: true
  });

  document.getElementById("reset-selection").click();

  const state = __app.store.getState();
  assert.equal(state.selectedPropertyDetails, null);
  assert.equal(state.propertyDetailsDismissed, false);
  assert.equal(state.estimate, null);
  assert.equal(state.warningsCollapsed, false);
  assert.equal(state.selectedLocation.canonical_address, "Edmonton, AB");
});
