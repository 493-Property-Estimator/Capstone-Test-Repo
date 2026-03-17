import { LAYER_DEFINITIONS } from "../../config.js";
import { clearElement, createElement, setText } from "../../utils/dom.js";

export function createLayerController({
  apiClient,
  store,
  controlsRoot,
  legendRoot,
  statusElement,
  mapAdapter
}) {
  function renderControls() {
    clearElement(controlsRoot);

    LAYER_DEFINITIONS.forEach((layer) => {
      const layerState = store.getState().activeLayers[layer.id];
      const row = createElement("label", "layer-item");
      const name = createElement("div", "layer-name");
      const title = createElement("strong", null, layer.label);
      const subtitle = createElement("span", null, layerState.status);
      name.appendChild(title);
      name.appendChild(subtitle);

      const toggle = document.createElement("input");
      toggle.type = "checkbox";
      toggle.checked = layerState.enabled;
      toggle.addEventListener("change", () => {
        if (toggle.checked) {
          loadLayer(layer.id);
        } else {
          store.updateLayer(layer.id, { enabled: false, status: "idle", data: null });
        }
      });

      row.appendChild(name);
      row.appendChild(toggle);
      controlsRoot.appendChild(row);
    });
  }

  function renderLegend() {
    clearElement(legendRoot);
    const layers = Object.values(store.getState().activeLayers).filter(
      (layer) => layer.enabled && layer.data?.legend?.items?.length
    );

    if (!layers.length) {
      legendRoot.appendChild(
        createElement("p", "legend-empty", "No active layer legends.")
      );
      return;
    }

    layers.forEach((layerState) => {
      layerState.data.legend.items.forEach((item) => {
        const row = createElement("div", "legend-item");
        const swatch = createElement("span", "legend-swatch");
        swatch.style.background = item.color || "#666";
        row.appendChild(swatch);
        row.appendChild(createElement("span", null, item.label));
        legendRoot.appendChild(row);
      });
    });
  }

  async function loadLayer(layerId) {
    const viewport = mapAdapter.getViewport();
    store.updateLayer(layerId, { enabled: true, status: "loading" });
    setText(statusElement, "Loading");

    try {
      const data = await apiClient.getLayerData({
        layerId,
        ...viewport
      });

      store.updateLayer(layerId, {
        enabled: true,
        status: data.coverage_status === "partial" ? "partial" : "ready",
        data
      });
      setText(statusElement, "Ready");
    } catch (error) {
      store.updateLayer(layerId, { enabled: false, status: "unavailable", data: null });
      setText(statusElement, "Unavailable");
    }
  }

  store.subscribe((state) => {
    renderControls();
    renderLegend();
    mapAdapter.renderLayers(state.activeLayers);
  });

  renderControls();
  renderLegend();
}
