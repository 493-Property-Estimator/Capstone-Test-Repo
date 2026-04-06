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
    { id: "warning-panel" },
    { id: "warning-indicator", tagName: "button" },
    { id: "environment-badge" },
    { id: "property-detail-panel" },
    { id: "property-detail-title" },
    { id: "property-detail-subtitle" },
    { id: "property-detail-body" },
    { id: "property-detail-close", tagName: "button" }
  ];
}

installDomGlobals({ ids: ids() });
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
