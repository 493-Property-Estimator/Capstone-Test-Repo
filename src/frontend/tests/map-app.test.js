import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse, wait } from "./helpers/fakeDom.js";
import { installMapLibre, latestMapInstance, FakePopup } from "./helpers/fakeMapLibre.js";

function baseIds() {
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

test("map adapter supports selection, generic layers, assessment layers, interactions, and reset flows", async () => {
  const { getById, window } = installDomGlobals({ ids: baseIds() });
  installMapLibre(window);
  globalThis.fetch = async () => createMockResponse("");

  const { createMapAdapter } = await import("../src/map/mapAdapter.js");
  const messages = getById("map-message");
  const propertyCard = getById("property-hover-card");
  let selectionCleared = 0;
  const clicked = [];
  const viewports = [];

  const adapter = createMapAdapter({
    root: getById("map-root"),
    onMapClick(coordinates) {
      clicked.push(coordinates);
    },
    onViewportChange(viewport) {
      viewports.push(viewport);
    },
    messageElement: messages,
    propertyCardElement: propertyCard,
    onSelectionCleared() {
      selectionCleared += 1;
    }
  });

  const map = latestMapInstance();
  assert.ok(map);
  assert.equal(viewports.length >= 1, true);

  adapter.setView({
    canonical_address: "870 ABBOTTSFIELD ROAD NW, Edmonton, AB",
    coordinates: { lat: 53.5763, lng: -113.3923 }
  });
  assert.match(messages.textContent, /Viewing 870 ABBOTTSFIELD/);
  assert.ok(map.lastFlyTo);

  adapter.setView(
    { canonical_address: "Pan only", coordinates: { lat: 53.57, lng: -113.39 } },
    { preserveZoom: true, panOnly: true }
  );
  assert.ok(map.lastEaseTo);

  adapter.renderLayers({
    schools: {
      enabled: true,
      status: "ready",
      data: {
        legend: { items: [{ color: "#1f6feb", label: "School" }] },
        features: [
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [-113.49, 53.54] },
            properties: { name: "School", address: "Edmonton", description: "Public school" }
          }
        ]
      }
    },
    parks: { enabled: false, status: "idle", data: null }
  });
  assert.ok(map.getLayer("schools-points"));

  map.emit(
    "click",
    {
      features: [
        {
          properties: { name: "School", address: "Edmonton", description: "Public school" }
        }
      ],
      lngLat: { lng: -113.49, lat: 53.54 }
    },
    "schools-points"
  );
  assert.equal(map.popups.some((popup) => popup instanceof FakePopup), true);
  map.emit("mousedown", { originalEvent: { clientX: 10, clientY: 10 } });
  map.emit("click", {
    originalEvent: { button: 0, clientX: 10, clientY: 10 },
    lngLat: { lat: 53.54, lng: -113.49 }
  });
  await wait(260);

  adapter.renderPropertyLayer({
    enabled: true,
    renderMode: "cluster",
    clusters: [{ cluster_id: "cluster-1", count: 8, center: { lat: 53.54, lng: -113.49 } }],
    properties: []
  });
  assert.ok(map.getLayer("assessment_properties-cluster-circle"));
  assert.match(messages.textContent, /Assessment properties visible: 8/);

  map.emit("mousedown", { originalEvent: { clientX: 20, clientY: 20 } });
  map.emit("click", {
    originalEvent: { button: 0, clientX: 20, clientY: 20 },
    lngLat: { lat: 53.55, lng: -113.48 }
  });
  await wait(260);
  assert.deepEqual(clicked[0], { lat: 53.55, lng: -113.48 });

  map.emit(
    "click",
    {
      features: [{ geometry: { coordinates: [-113.49, 53.54] } }],
      originalEvent: { button: 0 }
    },
    "assessment_properties-cluster-circle"
  );
  assert.ok(map.lastEaseTo);

  adapter.renderPropertyLayer({
    enabled: true,
    renderMode: "property",
    clusters: [],
    properties: [
      {
        canonical_location_id: "loc-1",
        canonical_address: "870 ABBOTTSFIELD ROAD NW, Edmonton, AB",
        coordinates: { lat: 53.5763, lng: -113.3923 },
        neighbourhood: "ABBOTTSFIELD",
        ward: "Métis",
        assessment_value: 165000,
        tax_class: "Residential"
      }
    ]
  });
  map.emit(
    "mousemove",
    {
      features: [
        {
          properties: {
            name: "870 ABBOTTSFIELD ROAD NW, Edmonton, AB",
            address: "870 ABBOTTSFIELD ROAD NW, Edmonton, AB",
            description: "Assessment: $165,000 | Neighbourhood: ABBOTTSFIELD | Ward: Métis | Tax class: Residential"
          }
        }
      ],
      originalEvent: { clientX: 50, clientY: 70 }
    },
    "assessment_properties-points"
  );
  await wait(5);
  assert.equal(propertyCard.classList.contains("is-visible"), true);
  assert.match(propertyCard.innerHTML, /ABBOTTSFIELD/);

  map.emit("mouseleave", {}, "assessment_properties-points");
  assert.equal(propertyCard.classList.contains("is-visible"), false);

  map.emit("mousedown", { originalEvent: { clientX: 20, clientY: 20 } });
  map.emit("dragstart");
  map.emit("click", {
    originalEvent: { button: 0, clientX: 50, clientY: 50 },
    lngLat: { lat: 53.56, lng: -113.47 }
  });
  await wait(260);
  assert.equal(clicked.length, 1);

  map.emit("mousedown", { originalEvent: { clientX: 20, clientY: 20 } });
  map.emit("click", {
    originalEvent: { button: 0, clientX: 20, clientY: 20 },
    lngLat: { lat: 53.57, lng: -113.46 }
  });
  map.emit("dblclick", { originalEvent: { button: 0 } });
  await wait(260);
  assert.equal(clicked.length, 1);

  adapter.focusEdmonton();
  assert.match(messages.textContent, /Viewing Edmonton/);
  adapter.resetView();
  assert.match(messages.textContent, /Map reset/);
  adapter.clearSelection();
  assert.equal(selectionCleared, 1);

  adapter.renderPropertyLayer({ enabled: false });
  assert.equal(map.getLayer("assessment_properties-points"), null);
});

test("map adapter handles missing MapLibre and default viewport fallback", async () => {
  installDomGlobals({
    ids: [
      { id: "map-root", rect: { left: 0, top: 0, width: 600, height: 400 } },
      { id: "map-message" },
      { id: "property-hover-card", rect: { left: 0, top: 0, width: 220, height: 120 } },
      { id: "property-detail-panel" }
    ]
  });
  globalThis.fetch = async () => createMockResponse("");
  delete window.maplibregl;

  const { createMapAdapter } = await import("../src/map/mapAdapter.js");
  const adapter = createMapAdapter({
    root: document.getElementById("map-root"),
    onMapClick() {},
    onViewportChange() {},
    messageElement: document.getElementById("map-message"),
    propertyCardElement: document.getElementById("property-hover-card"),
    propertyDetailPanelElement: document.getElementById("property-detail-panel"),
    onSelectionCleared() {}
  });

  assert.equal(document.getElementById("map-message").textContent, "MapLibre failed to load.");
  assert.equal(adapter.getViewport().zoom, 11);
});

test("app bootstrap wires the integrated frontend flows", async () => {
  const { getById, window } = installDomGlobals({ ids: baseIds() });
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
    return createMockResponse({}, { status: 404 });
  };

  const appModule = await import("../src/app.js");
  await wait(10);

  assert.match(getById("environment-badge").textContent, /Auto API|Mock API/);

  getById("address-input").value = "10234 98 Street NW, Edmonton";
  getById("search-submit").click();
  await wait(240);
  assert.match(getById("location-summary").textContent, /10234 98 Street/);

  appModule.__app.store.updatePropertyLayer({
    enabled: true,
    renderMode: "property",
    properties: [
      {
        canonical_location_id: "loc-1",
        canonical_address: "123 TEST AVENUE NW, Edmonton, AB",
        coordinates: { lat: 53.55, lng: -113.49 },
        details: {
          neighbourhood: "Downtown",
          assessment_value: 450000,
          ward: "O-day'min",
          tax_class: "Residential"
        }
      }
    ],
    clusters: []
  });
  await wait(10);

  const map = latestMapInstance();
  map.emit(
    "click",
    {
      features: [
        {
          geometry: { coordinates: [-113.49, 53.55] },
          properties: {
            canonical_location_id: "loc-1",
            canonical_address: "123 TEST AVENUE NW, Edmonton, AB",
            coordinates: { lat: 53.55, lng: -113.49 },
            details: {
              neighbourhood: "Downtown",
              assessment_value: 450000,
              ward: "O-day'min",
              tax_class: "Residential"
            }
          }
        }
      ],
      originalEvent: { button: 0 }
    },
    "assessment_properties-points"
  );
  assert.equal(appModule.__app.store.getState().selectedPropertyDetails.canonical_location_id, "loc-1");

  appModule.__app.store.setState({
    selectedLocation: {
      canonical_location_id: "loc-1",
      canonical_address: "123 TEST AVENUE NW, Edmonton, AB",
      coordinates: { lat: 53.55, lng: -113.49 }
    },
    selectedPropertyDetails: null,
    propertyDetailsDismissed: false
  });
  await wait(10);
  assert.equal(appModule.__app.store.getState().selectedPropertyDetails.canonical_location_id, "loc-1");

  appModule.__app.store.setState({
    selectedLocation: {
      canonical_location_id: "loc-1",
      canonical_address: "123 TEST AVENUE NW, Edmonton, AB",
      coordinates: { lat: 53.55, lng: -113.49 }
    },
    selectedPropertyDetails: null,
    propertyDetailsDismissed: true
  });
  await wait(10);
  assert.equal(appModule.__app.store.getState().selectedPropertyDetails, null);

  appModule.__app.store.updatePropertyLayer({
    enabled: true,
    renderMode: "property",
    properties: [
      {
        canonical_location_id: "loc-2",
        canonical_address: "No coord property",
        coordinates: { lat: 53.56, lng: -113.48 }
      }
    ],
    clusters: []
  });
  appModule.__app.store.setState({
    selectedLocation: {
      canonical_location_id: null,
      canonical_address: "Unmatched selection",
      coordinates: null
    },
    selectedPropertyDetails: null,
    propertyDetailsDismissed: false
  });
  await wait(10);
  assert.equal(appModule.__app.store.getState().selectedPropertyDetails, null);

  appModule.__app.store.updatePropertyLayer({
    enabled: true,
    renderMode: "property",
    properties: [
      {
        canonical_location_id: "loc-4",
        canonical_address: "Mismatch property",
        coordinates: { lat: 53.59, lng: -113.45 }
      }
    ],
    clusters: []
  });
  appModule.__app.store.setState({
    selectedLocation: {
      canonical_location_id: null,
      canonical_address: "Coordinate mismatch",
      coordinates: { lat: 53.55, lng: -113.49 }
    },
    selectedPropertyDetails: null,
    propertyDetailsDismissed: false
  });
  await wait(10);
  assert.equal(appModule.__app.store.getState().selectedPropertyDetails, null);

  appModule.__app.store.setState({
    selectedLocation: {
      canonical_location_id: "loc-1",
      canonical_address: "123 TEST AVENUE NW, Edmonton, AB",
      coordinates: { lat: 53.55, lng: -113.49 }
    },
    selectedPropertyDetails: appModule.__app.store.getState().propertyLayer.properties[0],
    propertyDetailsDismissed: false
  });
  await wait(10);

  map.emit(
    "click",
    {
      features: [
        {
          geometry: { coordinates: [-113.48, 53.56] },
          properties: {
            canonical_location_id: "loc-3",
            canonical_address: "456 OTHER ROAD NW, Edmonton, AB",
            coordinates: { lat: 53.56, lng: -113.48 },
            neighbourhood: "Oliver"
          }
        }
      ],
      originalEvent: { button: 0 }
    },
    "assessment_properties-points"
  );
  assert.equal(appModule.__app.store.getState().selectedLocation.neighbourhood, "Oliver");

  getById("estimate-submit").click();
  await wait(240);
  assert.match(getById("estimate-status").textContent, /Partial|Ready/);

  getById("reset-selection").click();
  assert.equal(getById("address-input").value, "");
  assert.match(getById("map-message").textContent, /Map reset/);

  appModule.__app.mapAdapter.clearSelection();
  assert.equal(appModule.__app.store.getState().selectedLocation, null);
});
