import {
  EDMONTON_BOUNDS,
  EDMONTON_CENTER,
  LAYER_LAB_DEFINITIONS,
  LAYERS_REFRESH_DEBOUNCE_MS,
  OSM_ATTRIBUTION,
  OSM_TILE_URL,
  PROPERTY_CACHE_TTL_MS
} from "./config.js";
import { apiClient } from "./services/api/apiClient.js";
import { debounce } from "./utils/debounce.js";
import { clearElement, createElement, setText } from "./utils/dom.js";

const LAB_LAYERS = LAYER_LAB_DEFINITIONS;
const POINT_ONLY_LAYERS = new Set([
  "schools",
  "parks",
  "playgrounds",
  "police_stations",
  "transit_stops",
  "businesses",
  "green_space"
]);
const HEAVY_GEOMETRY_LAYERS = new Set([
  "roads",
  "municipal_wards",
  "provincial_districts",
  "federal_districts",
  "census_subdivisions",
  "census_boundaries"
]);
const STATIC_LAYER_IDS = new Set([
  "municipal_wards",
  "provincial_districts",
  "federal_districts",
  "census_subdivisions",
  "census_boundaries"
]);

const layerState = Object.fromEntries(
  LAB_LAYERS.map((layer) => [
    layer.id,
    {
      enabled: false,
      mode: "individual",
      status: "idle",
      featureCount: 0,
      geometrySummary: ""
    }
  ])
);

const controlsRoot = document.getElementById("layer-lab-controls");
const statusElement = document.getElementById("lab-status");
const mapMessage = document.getElementById("lab-map-message");
const mapRoot = document.getElementById("layer-lab-map");

let map = null;
const renderedEntries = new Map();
const interactionRegistry = new Set();
const requestSeqByLayer = new Map();
const abortControllerByLayer = new Map();
const responseCacheByLayer = new Map();
let activePopup = null;

function createRasterStyle() {
  const tileUrls = ["a", "b", "c"].map((subdomain) => OSM_TILE_URL.replace("{s}", subdomain));
  return {
    version: 8,
    glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
    sources: {
      "osm-raster": {
        type: "raster",
        tiles: tileUrls,
        tileSize: 256,
        attribution: OSM_ATTRIBUTION
      }
    },
    layers: [{ id: "osm-raster-layer", type: "raster", source: "osm-raster" }]
  };
}

function getViewport() {
  const bounds = map.getBounds();
  return {
    west: bounds.getWest(),
    south: bounds.getSouth(),
    east: bounds.getEast(),
    north: bounds.getNorth(),
    zoom: map.getZoom()
  };
}

function setGlobalStatus() {
  const enabledRows = Object.values(layerState).filter((row) => row.enabled);
  const loading = enabledRows.some((row) => row.status === "loading");
  const unavailable = enabledRows.some((row) => row.status === "unavailable");
  if (loading) {
    setText(statusElement, "Loading...");
    return;
  }
  if (unavailable) {
    setText(statusElement, "Partial");
    return;
  }
  setText(statusElement, "Ready");
}

function formatStatusText(entry) {
  if (!entry.enabled) {
    return "Disabled";
  }
  if (entry.status === "loading") {
    return "Loading...";
  }
  if (entry.status === "unavailable") {
    return "Unavailable";
  }
  if (entry.featureCount > 0) {
    return entry.geometrySummary
      ? `${entry.featureCount} features · ${entry.geometrySummary}`
      : `${entry.featureCount} features`;
  }
  return "No features";
}

function supportsHeatMode(layerId) {
  return POINT_ONLY_LAYERS.has(layerId);
}

function renderControls() {
  clearElement(controlsRoot);

  LAB_LAYERS.forEach((layer) => {
    const state = layerState[layer.id];
    const card = createElement("div", "layer-lab-item");
    const topRow = createElement("div", "layer-lab-row");

    const enableLabel = createElement("label");
    const enableToggle = document.createElement("input");
    enableToggle.type = "checkbox";
    enableToggle.checked = state.enabled;
    enableToggle.addEventListener("change", () => {
      state.enabled = enableToggle.checked;
      if (!state.enabled) {
        state.status = "idle";
        state.featureCount = 0;
        state.geometrySummary = "";
        removeRenderedLayer(layer.id);
        setGlobalStatus();
        renderControls();
        updateMapMessage();
        return;
      }
      refreshLayer(layer.id);
      renderControls();
    });
    enableLabel.appendChild(enableToggle);
    enableLabel.appendChild(document.createTextNode(` ${layer.label}`));

    const statusCopy = createElement("span", "status-pill", formatStatusText(state));
    topRow.appendChild(enableLabel);
    topRow.appendChild(statusCopy);
    card.appendChild(topRow);

    const modeRow = createElement("div", "layer-lab-row");
    modeRow.appendChild(createElement("label", null, "Mode"));
    const modeSelect = document.createElement("select");
    const modeOptions = supportsHeatMode(layer.id)
      ? [
          { value: "individual", label: "Individual" },
          { value: "heat", label: "Heat Map" }
        ]
      : [
          { value: "individual", label: "Individual Geometry" }
        ];
    modeOptions.forEach((optionData) => {
      const option = document.createElement("option");
      option.value = optionData.value;
      option.textContent = optionData.label;
      option.selected = state.mode === optionData.value;
      modeSelect.appendChild(option);
    });
    modeSelect.addEventListener("change", () => {
      state.mode = modeSelect.value;
      refreshLayer(layer.id);
      renderControls();
    });
    modeRow.appendChild(modeSelect);
    card.appendChild(modeRow);

    controlsRoot.appendChild(card);
  });

  setGlobalStatus();
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

function buildCacheKey(layerId, viewport, mode) {
  return [layerId, mode, buildViewportKey(viewport)].join("|");
}

function getCachedResponse(layerId, cacheKey) {
  const layerCache = responseCacheByLayer.get(layerId);
  if (!layerCache) {
    return null;
  }
  const entry = layerCache.get(cacheKey);
  if (!entry) {
    return null;
  }
  if (Date.now() - entry.cachedAt > PROPERTY_CACHE_TTL_MS) {
    layerCache.delete(cacheKey);
    return null;
  }
  return entry.data;
}

function cacheResponse(layerId, cacheKey, data) {
  if (!responseCacheByLayer.has(layerId)) {
    responseCacheByLayer.set(layerId, new Map());
  }
  responseCacheByLayer.get(layerId).set(cacheKey, {
    cachedAt: Date.now(),
    data
  });
}

function geometryTypeSummary(features) {
  const types = new Set(features.map((feature) => feature?.geometry?.type).filter(Boolean));
  if (!types.size) {
    return "";
  }
  return [...types].join(", ");
}

function geometryCenter(geometry) {
  if (!geometry?.type || geometry.coordinates == null) {
    return null;
  }
  if (geometry.type === "Point" && Array.isArray(geometry.coordinates) && geometry.coordinates.length >= 2) {
    return { lng: Number(geometry.coordinates[0]), lat: Number(geometry.coordinates[1]) };
  }

  const points = [];
  const collect = (value) => {
    if (!Array.isArray(value)) {
      return;
    }
    if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
      points.push([Number(value[0]), Number(value[1])]);
      return;
    }
    value.forEach(collect);
  };
  collect(geometry.coordinates);
  if (!points.length) {
    return null;
  }
  const lng = points.reduce((sum, item) => sum + item[0], 0) / points.length;
  const lat = points.reduce((sum, item) => sum + item[1], 0) / points.length;
  return { lng, lat };
}

function closePopup() {
  if (activePopup) {
    activePopup.remove();
    activePopup = null;
  }
}

function removeRenderedLayer(layerId) {
  if (!map) {
    return;
  }
  closePopup();
  const entry = renderedEntries.get(layerId) || { sourceIds: [], layerIds: [] };
  [...entry.layerIds].reverse().forEach((id) => {
    if (map.getLayer(id)) {
      map.removeLayer(id);
    }
  });
  [...entry.sourceIds].reverse().forEach((id) => {
    if (map.getSource(id)) {
      map.removeSource(id);
    }
  });
  renderedEntries.delete(layerId);
}

function upsertSource(sourceId, features) {
  const sourceData = {
    type: "FeatureCollection",
    features
  };
  if (map.getSource(sourceId)) {
    map.getSource(sourceId).setData(sourceData);
    return sourceId;
  }
  map.addSource(sourceId, { type: "geojson", data: sourceData });
  return sourceId;
}

function formatPopupContent(feature, fallbackLabel) {
  const properties = feature?.properties || {};
  const title =
    properties.name ||
    properties.address ||
    properties.ward_name ||
    properties.district_name ||
    properties.csdname ||
    fallbackLabel;
  const secondary =
    properties.address ||
    properties.neighbourhood ||
    properties.category ||
    properties.zone_name ||
    properties.route_name ||
    "";
  return secondary && secondary !== title
    ? `<strong>${title}</strong><br>${secondary}`
    : `<strong>${title}</strong>`;
}

function registerPointer(layerId, mapLayerId) {
  const enterKey = `enter-${mapLayerId}`;
  const leaveKey = `leave-${mapLayerId}`;
  if (!interactionRegistry.has(enterKey)) {
    interactionRegistry.add(enterKey);
    map.on("mouseenter", mapLayerId, () => {
      map.getCanvas().style.cursor = "pointer";
    });
  }
  if (!interactionRegistry.has(leaveKey)) {
    interactionRegistry.add(leaveKey);
    map.on("mouseleave", mapLayerId, () => {
      map.getCanvas().style.cursor = "";
    });
  }
}

function registerPopupInteraction(layerId, mapLayerId, fallbackLabel) {
  registerPointer(layerId, mapLayerId);
  const clickKey = `click-${mapLayerId}`;
  if (interactionRegistry.has(clickKey)) {
    return;
  }
  interactionRegistry.add(clickKey);
  map.on("click", mapLayerId, (event) => {
    const feature = event.features?.[0];
    if (!feature) {
      return;
    }
    closePopup();
    activePopup = new window.maplibregl.Popup({ offset: 10 })
      .setLngLat(event.lngLat)
      .setHTML(formatPopupContent(feature, fallbackLabel))
      .addTo(map);
  });
}

function renderHeatLayer(layer, points) {
  removeRenderedLayer(layer.id);
  if (!points.length) {
    renderedEntries.set(layer.id, { sourceIds: [], layerIds: [] });
    return;
  }

  const sourceId = `lab-source-${layer.id}`;
  const heatFeatures = points.map((point) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [point.lng, point.lat] },
    properties: {
      name: point.name || layer.label,
      address: point.address || point.name || "",
      value: point.value ?? null
    }
  }));
  upsertSource(sourceId, heatFeatures);

  const heatLayerId = `lab-${layer.id}-heat`;
  const pointLayerId = `lab-${layer.id}-heat-points`;
  map.addLayer({
    id: heatLayerId,
    type: "heatmap",
    source: sourceId,
    paint: {
      "heatmap-weight": 1,
      "heatmap-intensity": [
        "interpolate",
        ["linear"],
        ["zoom"],
        9,
        0.6,
        16,
        1.6
      ],
      "heatmap-radius": [
        "interpolate",
        ["linear"],
        ["zoom"],
        9,
        12,
        16,
        28
      ],
      "heatmap-opacity": 0.9,
      "heatmap-color": [
        "interpolate",
        ["linear"],
        ["heatmap-density"],
        0,
        "rgba(33,102,172,0)",
        0.2,
        "#7cc8ff",
        0.45,
        "#7fd38a",
        0.7,
        "#f3c550",
        1,
        "#d94b3d"
      ]
    }
  });
  map.addLayer({
    id: pointLayerId,
    type: "circle",
    source: sourceId,
    minzoom: 14,
    paint: {
      "circle-color": layer.color,
      "circle-radius": 3.2,
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 0.8,
      "circle-opacity": 0.8
    }
  });
  registerPopupInteraction(layer.id, pointLayerId, layer.label);
  renderedEntries.set(layer.id, { sourceIds: [sourceId], layerIds: [heatLayerId, pointLayerId] });
}

function splitGeometryFeatures(features) {
  const points = [];
  const lines = [];
  const polygons = [];
  features.forEach((feature) => {
    const type = feature?.geometry?.type;
    if (type === "Point" || type === "MultiPoint") {
      points.push(feature);
      return;
    }
    if (type === "LineString" || type === "MultiLineString") {
      lines.push(feature);
      return;
    }
    if (type === "Polygon" || type === "MultiPolygon") {
      polygons.push(feature);
    }
  });
  return { points, lines, polygons };
}

function renderGeometryLayer(layer, features) {
  removeRenderedLayer(layer.id);
  if (!features.length) {
    renderedEntries.set(layer.id, { sourceIds: [], layerIds: [] });
    return;
  }

  const { points, lines, polygons } = splitGeometryFeatures(features);
  const sourceIds = [];
  const layerIds = [];

  if (polygons.length) {
    const fillSourceId = `lab-source-${layer.id}-fills`;
    upsertSource(fillSourceId, polygons);
    sourceIds.push(fillSourceId);

    const fillLayerId = `lab-${layer.id}-fills`;
    const fillOutlineLayerId = `lab-${layer.id}-fill-outlines`;
    map.addLayer({
      id: fillLayerId,
      type: "fill",
      source: fillSourceId,
      paint: {
        "fill-color": layer.color,
        "fill-opacity": 0.18
      }
    });
    map.addLayer({
      id: fillOutlineLayerId,
      type: "line",
      source: fillSourceId,
      paint: {
        "line-color": layer.color,
        "line-width": 1.8,
        "line-opacity": 0.95
      }
    });
    registerPopupInteraction(layer.id, fillLayerId, layer.label);
    layerIds.push(fillLayerId, fillOutlineLayerId);
  }

  if (lines.length) {
    const lineSourceId = `lab-source-${layer.id}-lines`;
    upsertSource(lineSourceId, lines);
    sourceIds.push(lineSourceId);

    const lineLayerId = `lab-${layer.id}-lines`;
    map.addLayer({
      id: lineLayerId,
      type: "line",
      source: lineSourceId,
      paint: {
        "line-color": layer.color,
        "line-width": 2.4,
        "line-opacity": 0.95
      }
    });
    registerPopupInteraction(layer.id, lineLayerId, layer.label);
    layerIds.push(lineLayerId);
  }

  if (points.length) {
    const pointSourceId = `lab-source-${layer.id}-points`;
    upsertSource(pointSourceId, points);
    sourceIds.push(pointSourceId);

    const pointLayerId = `lab-${layer.id}-points`;
    map.addLayer({
      id: pointLayerId,
      type: "circle",
      source: pointSourceId,
      paint: {
        "circle-color": layer.color,
        "circle-radius": 5.5,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.2
      }
    });
    registerPopupInteraction(layer.id, pointLayerId, layer.label);
    layerIds.push(pointLayerId);
  }

  renderedEntries.set(layer.id, { sourceIds, layerIds });
}

function normalizeGenericLayerFeatures(data) {
  return (data.features || [])
    .map((feature) => {
      const center = geometryCenter(feature?.geometry);
      return {
        type: "Feature",
        geometry: feature?.geometry,
        properties: {
          ...(feature?.properties || {}),
          name:
            feature?.properties?.name ||
            feature?.properties?.ward_name ||
            feature?.properties?.district_name ||
            feature?.properties?.csdname ||
            null,
          address: feature?.properties?.address || null,
          center_lng: center?.lng ?? null,
          center_lat: center?.lat ?? null
        }
      };
    })
    .filter(
      (feature) =>
        feature.geometry?.type &&
        feature.properties.center_lat != null &&
        feature.properties.center_lng != null
    );
}

function getLayerViewport(layerId) {
  if (STATIC_LAYER_IDS.has(layerId)) {
    return {
      west: EDMONTON_BOUNDS[0][1],
      south: EDMONTON_BOUNDS[0][0],
      east: EDMONTON_BOUNDS[1][1],
      north: EDMONTON_BOUNDS[1][0],
      zoom: 11
    };
  }
  return getViewport();
}

async function fetchLayerFeatures(layer, signal) {
  const viewport = getLayerViewport(layer.id);

  const response = await apiClient.getLayerData({
    layerId: layer.id,
    west: viewport.west,
    south: viewport.south,
    east: viewport.east,
    north: viewport.north,
    zoom: viewport.zoom,
    signal
  });
  return normalizeGenericLayerFeatures(response);
}

function updateMapMessage() {
  const enabled = LAB_LAYERS.filter((layer) => layerState[layer.id].enabled);
  if (!enabled.length) {
    setText(mapMessage, "No layers enabled.");
    return;
  }
  const summary = enabled
    .map((layer) => {
      const state = layerState[layer.id];
      return state.geometrySummary
        ? `${layer.label}: ${state.featureCount} (${state.geometrySummary})`
        : `${layer.label}: ${state.featureCount}`;
    })
    .join(" | ");
  setText(mapMessage, summary);
}

async function refreshLayer(layerId) {
  const layer = LAB_LAYERS.find((item) => item.id === layerId);
  const state = layerState[layerId];
  const viewport = getLayerViewport(layerId);
  const requestSeq = Number(requestSeqByLayer.get(layerId) || 0) + 1;
  requestSeqByLayer.set(layerId, requestSeq);
  const cacheKey = buildCacheKey(layerId, viewport, state.mode);

  if (!state.enabled) {
    const existingController = abortControllerByLayer.get(layerId);
    if (existingController) {
      existingController.abort();
      abortControllerByLayer.delete(layerId);
    }
    removeRenderedLayer(layerId);
    renderControls();
    return;
  }

  const cachedFeatures = getCachedResponse(layerId, cacheKey);
  if (cachedFeatures) {
    state.featureCount = cachedFeatures.length;
    state.geometrySummary = geometryTypeSummary(cachedFeatures);
    state.status = "ready";

    if (state.mode === "individual") {
      renderGeometryLayer(layer, cachedFeatures);
    } else {
      const centroidPoints = cachedFeatures.map((feature) => ({
        lng: Number(feature.properties.center_lng),
        lat: Number(feature.properties.center_lat),
        name: feature.properties.name,
        address: feature.properties.address,
        value: feature.properties.value ?? null
      }));
      renderHeatLayer(layer, centroidPoints);
    }
    renderControls();
    updateMapMessage();
    return;
  }

  const existingController = abortControllerByLayer.get(layerId);
  if (existingController) {
    existingController.abort();
  }
  const abortController = new AbortController();
  abortControllerByLayer.set(layerId, abortController);

  state.status = "loading";
  renderControls();

  try {
    const features = await fetchLayerFeatures(layer, abortController.signal);
    if (requestSeqByLayer.get(layerId) !== requestSeq) {
      return;
    }
    cacheResponse(layerId, cacheKey, features);
    state.featureCount = features.length;
    state.geometrySummary = geometryTypeSummary(features);
    state.status = "ready";

    if (state.mode === "individual") {
      renderGeometryLayer(layer, features);
    } else {
      const centroidPoints = features.map((feature) => ({
        lng: Number(feature.properties.center_lng),
        lat: Number(feature.properties.center_lat),
        name: feature.properties.name,
        address: feature.properties.address,
        value: feature.properties.value ?? null
      }));
      renderHeatLayer(layer, centroidPoints);
    }
  } catch (error) {
    if (requestSeqByLayer.get(layerId) !== requestSeq) {
      return;
    }
    if (error?.name === "AbortError") {
      return;
    }
    state.status = "unavailable";
    state.featureCount = 0;
    state.geometrySummary = "";
    removeRenderedLayer(layerId);
  } finally {
    if (abortControllerByLayer.get(layerId) === abortController) {
      abortControllerByLayer.delete(layerId);
    }
    renderControls();
    updateMapMessage();
  }
}

const refreshAllLayers = debounce(() => {
  LAB_LAYERS.filter((layer) => layerState[layer.id].enabled).forEach((layer) => {
    refreshLayer(layer.id);
  });
}, LAYERS_REFRESH_DEBOUNCE_MS);

function initializeMap() {
  map = new window.maplibregl.Map({
    container: mapRoot,
    style: createRasterStyle(),
    center: [EDMONTON_CENTER[1], EDMONTON_CENTER[0]],
    zoom: 11,
    maxBounds: [
      [EDMONTON_BOUNDS[0][1], EDMONTON_BOUNDS[0][0]],
      [EDMONTON_BOUNDS[1][1], EDMONTON_BOUNDS[1][0]]
    ]
  });

  map.addControl(new window.maplibregl.NavigationControl(), "top-right");

  map.on("load", () => {
    map.resize();
    setText(mapMessage, "Layer lab ready.");
    renderControls();
    refreshAllLayers();
  });

  window.addEventListener("resize", () => {
    if (map) {
      map.resize();
    }
  });

  map.on("moveend", refreshAllLayers);
  map.on("zoomend", refreshAllLayers);
}

initializeMap();
