import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse, wait } from "./helpers/fakeDom.js";

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

installDomGlobals();
globalThis.fetch = async () => createMockResponse("ENABLED_LAYERS=schools,assessment_properties\n");

const { createStore } = await import("../src/state/store.js");
const { createLayerController } = await import("../src/features/layers/layerController.js");

test("layer controller handles stale generic requests, property aborts, cache expiry, and prefetch failures", async () => {
  const store = createStore();
  const controlsRoot = document.createElement("div");
  const legendRoot = document.createElement("div");
  const statusElement = document.createElement("div");
  const viewport = { west: -113.6, south: 53.5, east: -113.4, north: 53.6, zoom: 12 };
  const mapAdapter = {
    handler: null,
    getViewport() {
      return { ...viewport };
    },
    setViewportChangeHandler(handler) {
      this.handler = handler;
    },
    renderLayers() {},
    renderPropertyLayer() {}
  };

  const schoolRequest = deferred();
  const propertyRequest = deferred();
  const propertyRequest2 = deferred();
  let getLayerCount = 0;
  let getPropertyCount = 0;
  createLayerController({
    apiClient: {
      getLayerData({ layerId }) {
        getLayerCount += 1;
        if (layerId === "schools" && getLayerCount === 1) {
          return schoolRequest.promise;
        }
        return Promise.resolve({
          coverage_status: "complete",
          legend: { items: [{ label: "School", color: "#123" }] },
          features: [{ type: "Feature", geometry: { type: "Point", coordinates: [-113.49, 53.54] }, properties: {} }]
        });
      },
      getProperties() {
        getPropertyCount += 1;
        if (getPropertyCount === 1) {
          return propertyRequest.promise;
        }
        if (getPropertyCount === 2) {
          return propertyRequest2.promise;
        }
        if (getPropertyCount >= 3) {
          return Promise.reject(new Error("prefetch failed"));
        }
        return Promise.resolve({
          render_mode: "cluster",
          coverage_status: "complete",
          clusters: [{ cluster_id: "c", count: 1, center: { lat: 53.54, lng: -113.49 } }],
          properties: [],
          page: { next_cursor: null },
          warnings: []
        });
      }
    },
    store,
    controlsRoot,
    legendRoot,
    statusElement,
    mapAdapter
  });

  const schoolsToggle = controlsRoot.children[1].children[1];
  schoolsToggle.checked = true;
  schoolsToggle.dispatchEvent({ type: "change", target: schoolsToggle });
  schoolsToggle.checked = false;
  schoolsToggle.dispatchEvent({ type: "change", target: schoolsToggle });
  schoolRequest.resolve({
    coverage_status: "complete",
    legend: { items: [{ label: "School", color: "#123" }] },
    features: [{ type: "Feature", geometry: { type: "Point", coordinates: [-113.49, 53.54] }, properties: {} }]
  });
  await wait(5);
  assert.equal(store.getState().activeLayers.schools.status, "idle");

  const propertyToggle = controlsRoot.children[0].children[1];
  propertyToggle.checked = false;
  propertyToggle.dispatchEvent({ type: "change", target: propertyToggle });
  mapAdapter.handler();
  await wait(250);
  assert.equal(store.getState().propertyLayer.enabled, false);

  propertyToggle.checked = true;
  propertyToggle.dispatchEvent({ type: "change", target: propertyToggle });
  propertyRequest.resolve({
    render_mode: "cluster",
    coverage_status: "complete",
    clusters: [{ cluster_id: "late", count: 1, center: { lat: 53.54, lng: -113.49 } }],
    properties: [],
    page: { next_cursor: null },
    warnings: []
  });
  propertyRequest2.resolve({
    render_mode: "cluster",
    coverage_status: "complete",
    clusters: [{ cluster_id: "new", count: 2, center: { lat: 53.55, lng: -113.48 } }],
    properties: [],
    page: { next_cursor: null },
    warnings: []
  });
  await wait(5);
  assert.equal(store.getState().propertyLayer.status, "ready");
  assert.equal(store.getState().propertyLayer.clusters[0].cluster_id, "new");

  const realNow = Date.now;
  let fakeNow = 1000;
  Date.now = () => fakeNow;
  propertyToggle.checked = true;
  propertyToggle.dispatchEvent({ type: "change", target: propertyToggle });
  await wait(5);
  fakeNow += 31_000;
  mapAdapter.handler();
  await wait(250);
  Date.now = realNow;

  assert.equal(store.getState().propertyLayer.status, "ready");
  assert.equal(getPropertyCount >= 2, true);
});

test("layer controller renders unavailable generic state and partial property state", async () => {
  const store = createStore();
  const controlsRoot = document.createElement("div");
  const legendRoot = document.createElement("div");
  const statusElement = document.createElement("div");
  const mapAdapter = {
    handler: null,
    getViewport() {
      return { west: -113.6, south: 53.5, east: -113.4, north: 53.6, zoom: 12 };
    },
    setViewportChangeHandler(handler) {
      this.handler = handler;
    },
    renderLayers() {},
    renderPropertyLayer() {}
  };

  createLayerController({
    apiClient: {
      getLayerData({ layerId }) {
        if (layerId === "schools") {
          return Promise.reject(new Error("down"));
        }
        return Promise.resolve({
          coverage_status: "partial",
          legend: { items: [] },
          features: []
        });
      },
      getProperties() {
        return Promise.resolve({
          render_mode: "cluster",
          coverage_status: "partial",
          clusters: [],
          properties: [],
          page: { next_cursor: null },
          warnings: []
        });
      }
    },
    store,
    controlsRoot,
    legendRoot,
    statusElement,
    mapAdapter
  });

  const propertyToggle = controlsRoot.children[0].children[1];
  propertyToggle.checked = true;
  propertyToggle.dispatchEvent({ type: "change", target: propertyToggle });
  await wait(5);
  assert.equal(store.getState().propertyLayer.status, "partial");
  assert.match(statusElement.textContent, /partial/i);

  const schoolsToggle = controlsRoot.children[1].children[1];
  schoolsToggle.checked = true;
  schoolsToggle.dispatchEvent({ type: "change", target: schoolsToggle });
  await wait(5);
  assert.equal(store.getState().activeLayers.schools.status, "unavailable");
  assert.match(statusElement.textContent, /unavailable/i);
});
