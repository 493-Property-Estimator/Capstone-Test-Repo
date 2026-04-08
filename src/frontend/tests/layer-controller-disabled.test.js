import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async () =>
  createMockResponse("ENABLED_LAYERS=schools\nPREFER_LIVE_API=0\n");

const { createStore } = await import("../src/state/store.js");
const { createLayerController } = await import("../src/features/layers/layerController.js");

test("layer controller supports a build with assessment properties disabled", () => {
  const store = createStore();
  const controlsRoot = document.createElement("div");
  const legendRoot = document.createElement("div");
  const statusElement = document.createElement("div");
  const propertyLayerCalls = [];
  const layerCalls = [];

  createLayerController({
    apiClient: {
      async getLayerData() {
        return {
          coverage_status: "complete",
          legend: { items: [] },
          features: []
        };
      }
    },
    store,
    controlsRoot,
    legendRoot,
    statusElement,
    mapAdapter: {
      getViewport() {
        return {
          west: -113.6,
          south: 53.5,
          east: -113.4,
          north: 53.6,
          zoom: 12
        };
      },
      setViewportChangeHandler() {},
      renderLayers(activeLayers) {
        layerCalls.push(activeLayers);
      },
      renderPropertyLayer(value) {
        propertyLayerCalls.push(value);
      }
    }
  });

  assert.equal(controlsRoot.children.length, 1);
  assert.equal(legendRoot.children[0].textContent, "No active layer legends.");
  assert.deepEqual(propertyLayerCalls[0], { enabled: false });
  const schoolsToggle = controlsRoot.children[0].children[1].children[1];
  schoolsToggle.checked = true;
  schoolsToggle.dispatchEvent({ type: "change", target: schoolsToggle });
  assert.equal(layerCalls.length >= 1, true);
});
