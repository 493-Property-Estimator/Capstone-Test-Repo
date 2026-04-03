import { LAYER_DEFINITIONS } from "../config.js";

export function createStore() {
  let state = {
    selectedLocation: null,
    latestClickId: null,
    activeLayers: LAYER_DEFINITIONS.reduce((accumulator, layer) => {
      accumulator[layer.id] = {
        enabled: Boolean(layer.alwaysOn && layer.id !== "assessment_properties"),
        status: layer.alwaysOn && layer.id !== "assessment_properties" ? "loading" : "idle",
        data: null
      };
      return accumulator;
    }, {}),
    propertyLayer: {
      enabled: true,
      status: "loading",
      requestSeq: 0,
      renderMode: "cluster",
      clusters: [],
      properties: [],
      nextCursor: null,
      warnings: [],
      legend: {
        title: "Assessment Properties",
        items: [{ label: "Property", color: "#a43434", shape: "circle" }]
      },
      viewportKey: null
    },
    viewport: null,
    estimate: null,
    warningsCollapsed: false
  };

  const listeners = new Set();

  function notify() {
    listeners.forEach((listener) => listener(state));
  }

  return {
    getState() {
      return state;
    },
    setState(patch) {
      state = {
        ...state,
        ...patch
      };
      notify();
    },
    updateLayer(layerId, patch) {
      state = {
        ...state,
        activeLayers: {
          ...state.activeLayers,
          [layerId]: {
            ...state.activeLayers[layerId],
            ...patch
          }
        }
      };
      notify();
    },
    updatePropertyLayer(patch) {
      state = {
        ...state,
        propertyLayer: {
          ...state.propertyLayer,
          ...patch
        }
      };
      notify();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    }
  };
}
