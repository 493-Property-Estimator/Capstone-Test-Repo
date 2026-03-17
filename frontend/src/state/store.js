import { DEFAULT_LOCATION, LAYER_DEFINITIONS } from "../config.js";

export function createStore() {
  let state = {
    selectedLocation: DEFAULT_LOCATION,
    latestClickId: null,
    activeLayers: LAYER_DEFINITIONS.reduce((accumulator, layer) => {
      accumulator[layer.id] = { enabled: false, status: "idle", data: null };
      return accumulator;
    }, {}),
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
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    }
  };
}
