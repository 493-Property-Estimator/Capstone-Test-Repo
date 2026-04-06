import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse, wait } from "./helpers/fakeDom.js";
import { installMapLibre, latestMapInstance, FakeMap } from "./helpers/fakeMapLibre.js";

test("map adapter covers deferred load, missing cards, ignored clicks, and generic interaction fallbacks", async () => {
  const { window } = installDomGlobals({
    ids: [
      { id: "map-root", rect: { left: 0, top: 0, width: 600, height: 400 } },
      { id: "map-message" }
    ]
  });
  installMapLibre(window);
  FakeMap.autoLoad = false;
  globalThis.fetch = async () => createMockResponse("");

  const { createMapAdapter } = await import("../src/map/mapAdapter.js");
  const clicked = [];
  const viewports = [];
  const adapter = createMapAdapter({
    root: document.getElementById("map-root"),
    onMapClick(value) {
      clicked.push(value);
    },
    onViewportChange(value) {
      viewports.push(value);
    },
    messageElement: document.getElementById("map-message"),
    propertyCardElement: null,
    onSelectionCleared() {}
  });

  const map = latestMapInstance();
  adapter.renderLayers({
    schools: {
      enabled: true,
      status: "ready",
      data: {
        legend: { items: [{ color: "#000", label: "School" }] },
        features: [
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [-113.49, 53.54] },
            properties: { name: "School", address: "Edmonton", description: "" }
          }
        ]
      }
    }
  });
  adapter.renderPropertyLayer({
    enabled: true,
    renderMode: "cluster",
    clusters: [{ cluster_id: "c", count: 1, center: { lat: 53.54, lng: -113.49 } }],
    properties: []
  });

  assert.equal(map.getLayer("schools-points"), null);
  assert.equal(map.getLayer("assessment_properties-cluster-circle"), null);

  map.emit("load");
  assert.ok(map.getLayer("schools-points"));
  assert.ok(map.getLayer("assessment_properties-cluster-circle"));
  assert.equal(viewports.length >= 1, true);

  adapter.setViewportChangeHandler(null);
  map.emit("moveend");
  await wait(150);

  map.emit("click", { originalEvent: { button: 1 } });
  await wait(250);
  assert.equal(clicked.length, 0);

  map.emit("dblclick", { originalEvent: { button: 1 } });

  adapter.renderPropertyLayer({
    enabled: true,
    renderMode: "cluster",
    clusters: [{ cluster_id: "post-load", count: 2, center: { lat: 53.54, lng: -113.49 } }],
    properties: []
  });
  assert.ok(map.getLayer("assessment_properties-cluster-circle"));

  adapter.renderPropertyLayer({
    enabled: true,
    renderMode: "property",
    clusters: [],
    properties: []
  });
  assert.ok(map.getLayer("assessment_properties-points"));

  adapter.renderLayers({
    schools: {
      enabled: true,
      status: "ready",
      data: {
        legend: { items: [{ color: "#000", label: "School" }] },
        features: [
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [-113.49, 53.54] },
            properties: { name: "", address: "", description: "" }
          }
        ]
      }
    }
  });
  map.emit("mouseenter", {}, "schools-points");
  assert.equal(map.getCanvas().style.cursor, "pointer");
  map.emit("mouseleave", {}, "schools-points");
  assert.equal(map.getCanvas().style.cursor, "");
  map.emit("click", { features: [] }, "schools-points");

  adapter.setSelectionClearedHandler(() => {
    clicked.push("cleared");
  });
  adapter.clearSelection();
  assert.equal(clicked.includes("cleared"), true);

  FakeMap.autoLoad = true;
});
