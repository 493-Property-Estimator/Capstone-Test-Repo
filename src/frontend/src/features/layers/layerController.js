import {
  LAYER_DEFINITIONS,
  LAYERS_REFRESH_DEBOUNCE_MS,
  PROPERTY_CACHE_TTL_MS,
  PROPERTY_HIGH_ZOOM_THRESHOLD,
  PROPERTY_LAYER_ENABLED,
  PROPERTY_LIMIT_DEFAULT,
  PROPERTY_LIMIT_HIGH_ZOOM,
  PROPERTY_PREFETCH_VIEWPORTS,
  PROPERTY_REFRESH_DEBOUNCE_MS
} from "../../config.js";
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
  const layerRequestSeqById = new Map();

  /* node:coverage disable */
  function formatStatus(status) {
    const normalized = String(status || "idle").toLowerCase();
    if (normalized === "loading") {
      return "Loading...";
    }
    if (normalized === "ready") {
      return "Ready";
    }
    if (normalized === "partial") {
      return "Partial";
    }
    if (normalized === "unavailable") {
      return "Unavailable";
    }
    return "Idle";
  }

  function layerLabel(layerId) {
    /* node:coverage ignore next */
    if (layerId === "assessment_properties") return "Assessment Properties";
    return LAYER_DEFINITIONS.find((layer) => layer.id === layerId)?.label || layerId;
  }

  function setLayerStatusMessage(text) {
    setText(statusElement, text);
  }

  function buildViewportKey(viewport = {}) {
    return [
      Number(viewport.west || 0).toFixed(3),
      Number(viewport.south || 0).toFixed(3),
      Number(viewport.east || 0).toFixed(3),
      Number(viewport.north || 0).toFixed(3),
      Number(viewport.zoom || 0).toFixed(2)
    ].join("|");
  }

  function normalizeViewport(viewport = {}) {
    return {
      west: Number(viewport.west),
      south: Number(viewport.south),
      east: Number(viewport.east),
      north: Number(viewport.north),
      zoom: Number(viewport.zoom)
    };
  }

  function getCachedPropertyResponse(viewportKey) {
    const entry = propertyResponseCache.get(viewportKey);

    if (!entry) {
      return null;
    }

    /* node:coverage ignore next */
    if (Date.now() - entry.cachedAt > PROPERTY_CACHE_TTL_MS) {
      propertyResponseCache.delete(viewportKey);
      return null;
    }

    return entry.data;
  }

  function cachePropertyResponse(viewportKey, data) {
    propertyResponseCache.set(viewportKey, {
      cachedAt: Date.now(),
      data
    });
  }

  function createDisplayModeSelect(currentMode, onChange) {
    const select = document.createElement("select");
    select.className = "layer-display-select";
    const modes = [
      { value: "clusters", label: "Clusters" },
      { value: "points", label: "Points" },
      { value: "heatmap", label: "Heat Map" }
    ];
    modes.forEach((mode) => {
      const option = document.createElement("option");
      option.value = mode.value;
      option.textContent = mode.label;
      option.selected = mode.value === currentMode;
      select.appendChild(option);
    });
    select.addEventListener("change", () => onChange(select.value));
    return select;
  }

  function renderControls() {
    clearElement(controlsRoot);

    if (PROPERTY_LAYER_ENABLED) {
      const propertyLayerState = store.getState().propertyLayer;
      const row = createElement("div", "layer-item");
      const name = createElement("div", "layer-name");
      const title = createElement("strong", null, "Assessment Properties");
      const subtitle = createElement("span", null, formatStatus(propertyLayerState.status));
      name.appendChild(title);
      name.appendChild(subtitle);

      const controls = createElement("div", "layer-controls-row");

      const displaySelect = createDisplayModeSelect(
        propertyLayerState.displayMode || "clusters",
        (mode) => {
          store.updatePropertyLayer({ displayMode: mode });
        }
      );
      controls.appendChild(displaySelect);

      const toggle = document.createElement("input");
      toggle.type = "checkbox";
      toggle.checked = Boolean(propertyLayerState.enabled);
      toggle.addEventListener("change", (event) => {
        if (event.target.checked) {
          store.updatePropertyLayer({ enabled: true, status: "loading" });
          setLayerStatusMessage("Loading Assessment Properties...");
          loadPropertyLayer(mapAdapter.getViewport());
        } else {
          if (propertyAbortController) {
            propertyAbortController.abort();
          }
          store.updatePropertyLayer({
            enabled: false,
            status: "idle",
            clusters: [],
            properties: [],
            warnings: []
          });
          setLayerStatusMessage("Assessment Properties idle.");
        }
      });
      controls.appendChild(toggle);

      row.appendChild(name);
      row.appendChild(controls);
      controlsRoot.appendChild(row);
    }

    LAYER_DEFINITIONS
      .filter((layer) => !layer.alwaysOn)
      .forEach((layer) => {
      const layerState = store.getState().activeLayers[layer.id];
      const row = createElement("div", "layer-item");
      const name = createElement("div", "layer-name");
      const title = createElement("strong", null, layer.label);
      const subtitle = createElement("span", null, formatStatus(layerState.status));
      name.appendChild(title);
      name.appendChild(subtitle);

      const controls = createElement("div", "layer-controls-row");

      const displaySelect = createDisplayModeSelect(
        layerState.displayMode || "clusters",
        (mode) => {
          store.updateLayer(layer.id, { displayMode: mode });
        }
      );
      controls.appendChild(displaySelect);

      const toggle = document.createElement("input");
      toggle.type = "checkbox";
      toggle.checked = layerState.enabled;
      toggle.addEventListener("change", (event) => {
        if (event.target.checked) {
          setLayerStatusMessage(`Loading ${layer.label}...`);
          loadLayer(layer.id);
        } else {
          const currentSeq = Number(layerRequestSeqById.get(layer.id) || 0) + 1;
          layerRequestSeqById.set(layer.id, currentSeq);
          store.updateLayer(layer.id, { enabled: false, status: "idle", data: null });
          setLayerStatusMessage(`${layer.label} idle.`);
        }
      });
      controls.appendChild(toggle);

      row.appendChild(name);
      row.appendChild(controls);
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
  /* node:coverage enable */

  async function loadLayer(layerId) {
    const viewport = mapAdapter.getViewport();
    const nextSeq = Number(layerRequestSeqById.get(layerId) || 0) + 1;
    layerRequestSeqById.set(layerId, nextSeq);

    const layerName = layerLabel(layerId);
    store.updateLayer(layerId, { enabled: true, status: "loading" });
    setLayerStatusMessage(`Loading ${layerName}...`);

    try {
      const data = await apiClient.getLayerData({
        layerId,
        ...viewport
      });

      if (layerRequestSeqById.get(layerId) !== nextSeq) {
        return;
      }

      /* node:coverage ignore next */
      if (!store.getState().activeLayers[layerId]?.enabled) return;

      const nextStatus = data.coverage_status === "partial" ? "partial" : "ready";
      store.updateLayer(layerId, {
        enabled: true,
        status: nextStatus,
        data
      });
      setLayerStatusMessage(
        nextStatus === "partial" ? `${layerName} partial.` : `${layerName} ready.`
      );
    } catch (error) {
      if (layerRequestSeqById.get(layerId) !== nextSeq) {
        return;
      }

      if (!store.getState().activeLayers[layerId]?.enabled) {
        return;
      }

      store.updateLayer(layerId, { enabled: true, status: "unavailable", data: null });
      setLayerStatusMessage(`${layerName} unavailable.`);
    }
  }

  async function loadPropertyLayer(viewport) {
    /* node:coverage ignore next */
    if (!store.getState().propertyLayer.enabled) return;

    const normalizedViewport = normalizeViewport(viewport);
    const viewportKey = buildViewportKey(normalizedViewport);
    const nextRequestSeq = store.getState().propertyLayer.requestSeq + 1;

    const cached = getCachedPropertyResponse(viewportKey);
    if (cached) {
      store.updatePropertyLayer({
        ...cached,
        status: cached.coverage_status === "partial" ? "partial" : "ready",
        requestSeq: nextRequestSeq,
        viewportKey
      });
      setLayerStatusMessage(
        cached.coverage_status === "partial"
          ? "Assessment Properties partial."
          : "Assessment Properties ready."
      );
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
    setLayerStatusMessage("Loading Assessment Properties...");

    try {
      const response = await apiClient.getProperties({
        ...viewport,
        limit: viewport.zoom >= PROPERTY_HIGH_ZOOM_THRESHOLD ? PROPERTY_LIMIT_HIGH_ZOOM : PROPERTY_LIMIT_DEFAULT,
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

      cachePropertyResponse(viewportKey, patch);
      store.updatePropertyLayer({
        ...patch,
        status: response.coverage_status === "partial" || response.status === "partial"
          ? "partial"
          : "ready"
      });
      setLayerStatusMessage(
        response.coverage_status === "partial" || response.status === "partial"
          ? "Assessment Properties partial."
          : "Assessment Properties ready."
      );
      buildAdjacentViewports(normalizedViewport)
        .slice(0, PROPERTY_PREFETCH_VIEWPORTS)
        .forEach((adjacentViewport) => {
          prefetchPropertyViewport(adjacentViewport);
        });
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
      setLayerStatusMessage("Assessment Properties unavailable.");
    }
  }

  async function prefetchPropertyViewport(viewport) {
    const normalizedViewport = normalizeViewport(viewport);
    const viewportKey = buildViewportKey(normalizedViewport);

    /* node:coverage ignore next */
    if (getCachedPropertyResponse(viewportKey)) return;

    try {
      const response = await apiClient.getProperties({
        ...normalizedViewport,
        limit:
          normalizedViewport.zoom >= PROPERTY_HIGH_ZOOM_THRESHOLD
            ? PROPERTY_LIMIT_HIGH_ZOOM
            : PROPERTY_LIMIT_DEFAULT
      });

      cachePropertyResponse(viewportKey, {
        renderMode: response.render_mode,
        clusters: response.clusters || [],
        properties: response.properties || [],
        nextCursor: response.page?.next_cursor || null,
        warnings: response.warnings || [],
        legend: response.legend || store.getState().propertyLayer.legend,
        coverage_status: response.coverage_status || "complete",
        viewportKey
      });
    } catch {
      // Ignore prefetch failures.
    }
  }

  function buildAdjacentViewports(viewport) {
    const width = viewport.east - viewport.west;
    const height = viewport.north - viewport.south;

    return [
      {
        ...viewport,
        west: viewport.west + width,
        east: viewport.east + width
      },
      {
        ...viewport,
        west: viewport.west - width,
        east: viewport.east - width
      },
      {
        ...viewport,
        south: viewport.south + height,
        north: viewport.north + height
      },
      {
        ...viewport,
        south: viewport.south - height,
        north: viewport.north - height
      }
    ];
  }

  const refreshVisibleLayers = debounce(() => {
    const state = store.getState();
    LAYER_DEFINITIONS
      .filter((layer) => layer.id !== "assessment_properties")
      .filter((layer) => state.activeLayers[layer.id]?.enabled)
      .forEach(
      (layer) => loadLayer(layer.id)
    );
  }, LAYERS_REFRESH_DEBOUNCE_MS);

  const refreshPropertyLayer = debounce((viewport) => {
    loadPropertyLayer(viewport);
  }, PROPERTY_REFRESH_DEBOUNCE_MS);

  mapAdapter.setViewportChangeHandler(() => {
    const viewport = mapAdapter.getViewport();
    store.setState({ viewport });
    if (PROPERTY_LAYER_ENABLED && store.getState().propertyLayer.enabled) {
      refreshPropertyLayer(viewport);
    }
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
    /* node:coverage ignore next */
    .forEach((layer) => loadLayer(layer.id));

  if (PROPERTY_LAYER_ENABLED) {
    loadPropertyLayer(mapAdapter.getViewport());
  } else {
    mapAdapter.renderPropertyLayer({ enabled: false });
  }
}
