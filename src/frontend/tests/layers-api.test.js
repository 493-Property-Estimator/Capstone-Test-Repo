import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse, wait } from "./helpers/fakeDom.js";

async function loadStore() {
  globalThis.fetch = async () => createMockResponse("");
  const { createStore } = await import("../src/state/store.js");
  return createStore();
}

function createViewport() {
  return {
    west: -113.6,
    south: 53.5,
    east: -113.4,
    north: 53.6,
    zoom: 12
  };
}

test("api client uses live APIs, falls back to mock on configured failures, and propagates validation errors", async () => {
  installDomGlobals();
  const mockFetchCalls = [];
  const propertyGeoJson = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [-113.49, 53.54] },
        properties: {
          id: "prop-1",
          name: "870 ABBOTTSFIELD ROAD NW",
          address: "870 ABBOTTSFIELD ROAD NW, Edmonton, AB",
          description: "Assessment: $165,000 | Neighbourhood: ABBOTTSFIELD | Ward: Métis | Tax class: Residential"
        }
      }
    ]
  };

  globalThis.fetch = async (url, options = {}) => {
    mockFetchCalls.push({ url, options });
    if (String(url).endsWith("/app.env")) {
      return createMockResponse("PREFER_LIVE_API=1\nSEARCH_PROVIDER=osrm\n");
    }
    if (String(url).includes("/search/suggestions")) {
      return createMockResponse({ suggestions: [{ display_text: "Live result" }] });
    }
    if (String(url).includes("/search/resolve")) {
      return createMockResponse(
        {
          error: { message: "Search temporarily unavailable" }
        },
        { status: 500 }
      );
    }
    if (String(url).includes("/locations/resolve-click")) {
      return createMockResponse({ status: "resolved", location: { canonical_address: "Clicked" } });
    }
    if (String(url).includes("/estimates")) {
      return createMockResponse(
        {
          error: { message: "Coordinates must be within the supported Edmonton area." }
        },
        { status: 422 }
      );
    }
    if (String(url).includes("/layers/schools")) {
      return createMockResponse({}, { status: 404 });
    }
    if (String(url).includes("/properties")) {
      return createMockResponse(
        {
          render_mode: "cluster",
          clusters: [{ cluster_id: "c-1", count: 2, center: { lat: 53.54, lng: -113.49 } }],
          properties: [],
          page: { next_cursor: null },
          coverage_status: "complete",
          warnings: []
        },
        { status: 424 }
      );
    }
    if (String(url).includes("./mock-data/assessment-properties-tiles/index.json")) {
      return createMockResponse({
        tiles: [
          {
            file: "tile-1.json",
            west: -113.7,
            south: 53.3,
            east: -113.2,
            north: 53.8,
            count: 1
          }
        ]
      });
    }
    if (String(url).includes("./mock-data/assessment-properties-tiles/tile-1.json")) {
      return createMockResponse(propertyGeoJson);
    }
    if (String(url).includes("./mock-data/assessment-properties.geojson")) {
      return createMockResponse(propertyGeoJson);
    }
    return createMockResponse({});
  };

  const { apiClient } = await import("../src/services/api/apiClient.js");

  const suggestions = await apiClient.getAddressSuggestions("10234");
  assert.equal(suggestions.suggestions[0].display_text, "Live result");

  const resolved = await apiClient.resolveAddress("10234 98 Street NW");
  assert.equal(resolved.status, "resolved");

  const clickResponse = await apiClient.resolveMapClick({ coordinates: { lat: 53.5, lng: -113.4 } });
  assert.equal(clickResponse.location.canonical_address, "Clicked");

  await assert.rejects(
    () => apiClient.getEstimate({ location: { coordinates: { lat: 0, lng: 0 } } }),
    /supported Edmonton area/
  );

  const layerData = await apiClient.getLayerData({ layerId: "schools", ...createViewport() });
  assert.equal(layerData.features.length, 2);

  const propertyData = await apiClient.getProperties(createViewport());
  assert.equal(propertyData.render_mode, "cluster");

  const providerCall = mockFetchCalls.find((call) => String(call.url).includes("/search/suggestions"));
  assert.match(String(providerCall.url), /provider=osrm/);
});

test("layer controller handles property caching, generic layer toggles, partial states, and outages", async () => {
  const { document } = installDomGlobals();
  const store = await loadStore();
  const { createLayerController } = await import("../src/features/layers/layerController.js");

  const controlsRoot = document.createElement("div");
  const legendRoot = document.createElement("div");
  const statusElement = document.createElement("div");
  const viewport = createViewport();
  const renderCalls = {
    layers: [],
    property: []
  };

  const mapAdapter = {
    viewportHandler: null,
    renderLayers(activeLayers) {
      renderCalls.layers.push(activeLayers);
    },
    renderPropertyLayer(propertyLayer) {
      renderCalls.property.push(propertyLayer);
    },
    getViewport() {
      return { ...viewport };
    },
    setViewportChangeHandler(handler) {
      this.viewportHandler = handler;
    }
  };

  let propertyCallCount = 0;
  const apiClient = {
    async getLayerData({ layerId }) {
      if (layerId === "parks") {
        throw new Error("Layer down");
      }
      return {
        coverage_status: layerId === "schools" ? "partial" : "complete",
        legend: {
          title: layerId,
          items: [{ label: layerId, color: "#123456" }]
        },
        features: [{ type: "Feature", geometry: { type: "Point", coordinates: [-113.49, 53.54] }, properties: {} }]
      };
    },
    async getProperties(input) {
      propertyCallCount += 1;
      if (input.west === 999) {
        throw new Error("unavailable");
      }
      return {
        render_mode: propertyCallCount === 1 ? "cluster" : "property",
        coverage_status: propertyCallCount === 1 ? "partial" : "complete",
        clusters:
          propertyCallCount === 1
            ? [{ cluster_id: "cluster-1", count: 5, center: { lat: 53.54, lng: -113.49 } }]
            : [],
        properties:
          propertyCallCount === 1
            ? []
            : [{ canonical_location_id: "loc-1", coordinates: { lat: 53.54, lng: -113.49 } }],
        page: { next_cursor: null },
        warnings: []
      };
    }
  };

  createLayerController({
    apiClient,
    store,
    controlsRoot,
    legendRoot,
    statusElement,
    mapAdapter
  });

  await wait(10);
  assert.match(statusElement.textContent, /Assessment Properties partial/);
  assert.equal(store.getState().propertyLayer.status, "partial");
  assert.equal(renderCalls.property.length > 0, true);

  const allToggles = controlsRoot.children.map((row) => row.children[1].children[1]);
  const propertyToggle = allToggles[0];
  const schoolsToggle = allToggles.find((toggle, index) => controlsRoot.children[index].children[0].textContent.includes("Schools"));
  const parksToggle = allToggles.find((toggle, index) => controlsRoot.children[index].children[0].textContent.includes("Parks"));

  schoolsToggle.checked = true;
  schoolsToggle.dispatchEvent({ type: "change", target: schoolsToggle });
  await wait(5);
  assert.equal(store.getState().activeLayers.schools.status, "partial");

  parksToggle.checked = true;
  parksToggle.dispatchEvent({ type: "change", target: parksToggle });
  await wait(5);
  assert.equal(store.getState().activeLayers.parks.status, "unavailable");

  assert.equal(legendRoot.children.length > 0, true);

  propertyToggle.checked = false;
  propertyToggle.dispatchEvent({ type: "change", target: propertyToggle });
  assert.equal(store.getState().propertyLayer.enabled, false);

  viewport.zoom = 17;
  propertyToggle.checked = true;
  propertyToggle.dispatchEvent({ type: "change", target: propertyToggle });
  await wait(5);
  assert.equal(store.getState().propertyLayer.status, "ready");

  mapAdapter.viewportHandler();
  await wait(350);
  assert.equal(store.getState().viewport.zoom, 17);

  const callsAfterViewport = propertyCallCount;
  mapAdapter.viewportHandler();
  await wait(250);
  assert.equal(propertyCallCount, callsAfterViewport);

  viewport.west = 999;
  mapAdapter.viewportHandler();
  await wait(250);
  assert.equal(store.getState().propertyLayer.status, "unavailable");
});
