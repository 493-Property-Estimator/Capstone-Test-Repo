import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse, wait } from "./helpers/fakeDom.js";
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
    { id: "layer-side-panel" },
    { id: "layer-panel-toggle", tagName: "button" },
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
    return createMockResponse("", { status: 404 });
  }
  return createMockResponse({});
};

await import("../src/app.js");
await wait(5);

test("app shows Auto API badge when live mode is preferred", () => {
  assert.equal(document.getElementById("environment-badge").textContent, "Auto API");
});
