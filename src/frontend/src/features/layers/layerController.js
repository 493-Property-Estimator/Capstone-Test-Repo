import { LAYER_DEFINITIONS } from "../../config.js";
import { debounce } from "../../utils/debounce.js";
import { clearElement, createElement, setText } from "../../utils/dom.js";

export function createLayerController({
  apiClient,
  store,
  controlsRoot,
  legendRoot,
  statusElement,
  mapAdapter
}) {
  let lastRenderedActiveLayers = null;
  let lastRenderedPropertyLayer = null;
  let propertyAbortController = null;
  const propertyResponseCache = new Map();

  function buildViewportKey(viewport = {}) {
    return [
      Number(viewport.west || 0).toFixed(3),
      Number(viewport.south || 0).toFixed(3),
      Number(viewport.east || 0).toFixed(3),
      Number(viewport.north || 0).toFixed(3),
      Number(viewport.zoom || 0).toFixed(2)
    ].join("|");
  }

  function renderControls() {
    clearElement(controlsRoot);

    LAYER_DEFINITIONS.filter((layer) => !layer.alwaysOn).forEach((layer) => {
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
          mapAdapter.focusEdmonton();
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
    const propertyLayer = store.getState().propertyLayer;

    if (propertyLayer.enabled && propertyLayer.legend?.items?.length) {
      layers.unshift({
        data: {
          legend: propertyLayer.legend
        }
      });
    }

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
      setText(statusElement, data.coverage_status === "partial" ? "Partial" : "Ready");
    } catch (error) {
      store.updateLayer(layerId, { enabled: false, status: "unavailable", data: null });
      setText(statusElement, "Unavailable");
    }
  }

  async function loadPropertyLayer(viewport) {
    const viewportKey = buildViewportKey(viewport);
    const nextRequestSeq = store.getState().propertyLayer.requestSeq + 1;

    if (propertyResponseCache.has(viewportKey)) {
      const cached = propertyResponseCache.get(viewportKey);
      store.updatePropertyLayer({
        ...cached,
        status: cached.coverage_status === "partial" ? "partial" : "ready",
        requestSeq: nextRequestSeq,
        viewportKey
      });
      return;
    }

    if (propertyAbortController) {
      propertyAbortController.abort();
    }

    propertyAbortController = new AbortController();

    store.updatePropertyLayer({
      status: "loading",
      requestSeq: nextRequestSeq,
      viewportKey
    });
    setText(statusElement, "Loading");

    try {
      const response = await apiClient.getProperties({
        ...viewport,
        limit: viewport.zoom >= 17 ? 4000 : 5000,
        signal: propertyAbortController.signal
      });

      if (store.getState().propertyLayer.requestSeq !== nextRequestSeq) {
        return;
      }

      const patch = {
        renderMode: response.render_mode,
        clusters: response.clusters || [],
        properties: response.properties || [],
        nextCursor: response.page?.next_cursor || null,
        warnings: response.warnings || [],
        legend: response.legend || store.getState().propertyLayer.legend,
        coverage_status: response.coverage_status || "complete",
        viewportKey
      };

      propertyResponseCache.set(viewportKey, patch);
      store.updatePropertyLayer({
        ...patch,
        status: response.coverage_status === "partial" || response.status === "partial"
          ? "partial"
          : "ready"
      });
      setText(statusElement, "Ready");
    } catch (error) {
      if (error?.name === "AbortError") {
        return;
      }

      store.updatePropertyLayer({
        status: "unavailable",
        warnings: [
          {
            code: "PROPERTY_LAYER_UNAVAILABLE",
            severity: "warning",
            title: "Property layer unavailable",
            message: "The assessment property viewport could not be loaded.",
            affected_factors: [],
            dismissible: true
          }
        ]
      });
      setText(statusElement, "Unavailable");
    }
  }

  const refreshVisibleLayers = debounce(() => {
    const state = store.getState();
    LAYER_DEFINITIONS
      .filter((layer) => layer.id !== "assessment_properties")
      .filter((layer) => state.activeLayers[layer.id]?.enabled)
      .forEach(
      (layer) => loadLayer(layer.id)
    );
  }, 300);

  const refreshPropertyLayer = debounce((viewport) => {
    loadPropertyLayer(viewport);
  }, 180);

  mapAdapter.setViewportChangeHandler(() => {
    const viewport = mapAdapter.getViewport();
    store.setState({ viewport });
    refreshPropertyLayer(viewport);
    refreshVisibleLayers();
  });

  store.subscribe((state) => {
    renderControls();
    renderLegend();

    if (state.activeLayers !== lastRenderedActiveLayers) {
      lastRenderedActiveLayers = state.activeLayers;
      mapAdapter.renderLayers(state.activeLayers);
    }

    if (state.propertyLayer !== lastRenderedPropertyLayer) {
      lastRenderedPropertyLayer = state.propertyLayer;
      mapAdapter.renderPropertyLayer(state.propertyLayer);
    }
  });

  renderControls();
  renderLegend();

  LAYER_DEFINITIONS
    .filter((layer) => layer.alwaysOn && layer.id !== "assessment_properties")
    .forEach((layer) => {
    loadLayer(layer.id);
  });

  loadPropertyLayer(mapAdapter.getViewport());
}
