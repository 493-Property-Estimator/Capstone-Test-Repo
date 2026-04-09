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
document.body.dataset = { page: "unknown" };

const estimatorLink = document.createElement("button");
estimatorLink.dataset = { pageTarget: "estimator" };
const ingestionLink = document.createElement("button");
ingestionLink.dataset = { pageTarget: "ingestion" };
const invalidLink = document.createElement("button");
invalidLink.dataset = { pageTarget: "unknown" };
document.querySelectorAll = () => [estimatorLink, ingestionLink, invalidLink];

globalThis.fetch = async (url) => {
  if (String(url).endsWith("/app.env")) {
    return createMockResponse("PREFER_LIVE_API=0\n");
  }
  return createMockResponse({});
};

await import("../src/app.js");
await wait(10);

test("app navigation uses dataset-backed page switching and ignores invalid pages", () => {
  assert.equal(document.body.dataset.page, "unknown");

  estimatorLink.click();
  assert.equal(document.body.dataset.page, "estimator");
  assert.equal(estimatorLink.classList.contains("is-active"), true);
  assert.equal(ingestionLink.classList.contains("is-active"), false);

  const menuToggle = document.getElementById("app-menu-toggle");
  const overlay = document.getElementById("app-sidebar-overlay");
  const sidebar = document.getElementById("app-sidebar-nav");

  menuToggle.click();
  assert.equal(sidebar.classList.contains("is-open"), true);
  assert.equal(overlay.classList.contains("is-hidden"), false);

  ingestionLink.click();
  assert.equal(document.body.dataset.page, "ingestion");
  assert.equal(estimatorLink.classList.contains("is-active"), false);
  assert.equal(ingestionLink.classList.contains("is-active"), true);
  assert.equal(sidebar.classList.contains("is-open"), false);

  invalidLink.click();
  assert.equal(document.body.dataset.page, "ingestion");
});
