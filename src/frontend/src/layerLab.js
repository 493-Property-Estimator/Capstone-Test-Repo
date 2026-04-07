import {
  EDMONTON_BOUNDS,
  EDMONTON_CENTER,
  OSM_ATTRIBUTION,
  OSM_TILE_URL
} from "./config.js";
import { apiClient } from "./services/api/apiClient.js";
import { debounce } from "./utils/debounce.js";
import { clearElement, createElement, setText } from "./utils/dom.js";

const LAB_LAYERS = [
  { id: "assessment_properties", label: "Assessment Properties", color: "#a43434" },
  { id: "schools", label: "Schools", color: "#1d4ed8" },
  { id: "parks", label: "Parks", color: "#15803d" },
  { id: "playgrounds", label: "Playgrounds", color: "#ea580c" },
  { id: "transit_stops", label: "Transit Stops", color: "#0891b2" }
];

const layerState = Object.fromEntries(
  LAB_LAYERS.map((layer) => [
    layer.id,
    {
      enabled: layer.id === "assessment_properties",
      mode: "collective",
      pointLimit: 1000,
      status: "idle",
      pointsInView: 0
    }
  ])
);

const controlsRoot = document.getElementById("layer-lab-controls");
const statusElement = document.getElementById("lab-status");
const mapMessage = document.getElementById("lab-map-message");
const mapRoot = document.getElementById("layer-lab-map");

let map = null;
const renderedLayerIds = new Map();
const interactionRegistry = new Set();
const requestSeqByLayer = new Map();

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
  if (entry.pointsInView > 0) {
    return `${entry.pointsInView} points`;
  }
  return "No points";
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
        state.pointsInView = 0;
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
    [
      { value: "individual", label: "Individual" },
      { value: "collective", label: "Collective" },
      { value: "heat", label: "Heat Map" }
    ].forEach((optionData) => {
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

    const limitRow = createElement("div", "layer-lab-row");
    limitRow.appendChild(createElement("label", null, "Point Limit (Individual)"));
    const limitInput = document.createElement("input");
    limitInput.type = "number";
    limitInput.min = "1";
    limitInput.max = "10000";
    limitInput.value = String(state.pointLimit);
    limitInput.disabled = state.mode !== "individual";
    limitInput.addEventListener("change", () => {
      const parsed = Number(limitInput.value);
      state.pointLimit = Number.isFinite(parsed) ? Math.max(1, Math.min(10000, Math.round(parsed))) : 1000;
      limitInput.value = String(state.pointLimit);
      if (state.mode === "individual") {
        refreshLayer(layer.id);
      }
    });
    limitRow.appendChild(limitInput);
    card.appendChild(limitRow);

    controlsRoot.appendChild(card);
  });

  setGlobalStatus();
}

function buildClusterPoints(points, zoom) {
  const bucketSize =
    zoom <= 11
      ? 0.03
      : zoom <= 12
      ? 0.024
      : zoom <= 13
      ? 0.018
      : zoom <= 14
      ? 0.012
      : zoom <= 15
      ? 0.008
      : zoom <= 16
      ? 0.005
      : 0.003;
  const buckets = new Map();
  points.forEach((point) => {
    const key = `${Math.floor(point.lng / bucketSize)}_${Math.floor(point.lat / bucketSize)}`;
    if (!buckets.has(key)) {
      buckets.set(key, []);
    }
    buckets.get(key).push(point);
  });

  return [...buckets.entries()].map(([bucketId, bucket]) => {
    const lng = bucket.reduce((sum, item) => sum + item.lng, 0) / bucket.length;
    const lat = bucket.reduce((sum, item) => sum + item.lat, 0) / bucket.length;
    return {
      type: "Feature",
      geometry: { type: "Point", coordinates: [lng, lat] },
      properties: {
        bucket_id: bucketId,
        point_count: bucket.length,
        point_count_abbreviated: String(bucket.length)
      }
    };
  });
}

function removeRenderedLayer(layerId) {
  if (!map) {
    return;
  }
  const layerIds = renderedLayerIds.get(layerId) || [];
  [...layerIds].reverse().forEach((id) => {
    if (map.getLayer(id)) {
      map.removeLayer(id);
    }
  });
  const sourceId = `lab-source-${layerId}`;
  if (map.getSource(sourceId)) {
    map.removeSource(sourceId);
  }
  renderedLayerIds.delete(layerId);
}

function upsertSource(layerId, features) {
  const sourceId = `lab-source-${layerId}`;
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

function registerLayerInteractions(layerId, mode) {
  const sourcePointLayerId =
    mode === "individual"
      ? `lab-${layerId}-individual`
      : mode === "collective"
      ? `lab-${layerId}-cluster-circle`
      : `lab-${layerId}-heat-points`;

  if (mode === "collective" && !interactionRegistry.has(sourcePointLayerId)) {
    interactionRegistry.add(sourcePointLayerId);
    map.on("click", sourcePointLayerId, (event) => {
      const feature = event.features?.[0];
      if (!feature) {
        return;
      }
      map.easeTo({
        center: feature.geometry.coordinates,
        zoom: Math.min(map.getZoom() + 2, 18)
      });
    });
  }

  if (mode !== "heat" && !interactionRegistry.has(`click-${sourcePointLayerId}`)) {
    interactionRegistry.add(`click-${sourcePointLayerId}`);
    map.on("mouseenter", sourcePointLayerId, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", sourcePointLayerId, () => {
      map.getCanvas().style.cursor = "";
    });
    map.on("click", sourcePointLayerId, (event) => {
      const feature = event.features?.[0];
      const name = feature?.properties?.name || feature?.properties?.address || null;
      if (!name || mode === "collective") {
        return;
      }
      new window.maplibregl.Popup({ offset: 10 })
        .setLngLat(event.lngLat)
        .setHTML(`<strong>${name}</strong>`)
        .addTo(map);
    });
  }
}

function renderLayer(layer, points, mode) {
  removeRenderedLayer(layer.id);
  if (!points.length) {
    renderedLayerIds.set(layer.id, []);
    return;
  }

  const sourceId =
    mode === "collective"
      ? upsertSource(layer.id, buildClusterPoints(points, map.getZoom()))
      : upsertSource(
          layer.id,
          points.map((point) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: [point.lng, point.lat] },
            properties: {
              name: point.name || layer.label,
              address: point.address || point.name || "",
              value: point.value ?? null
            }
          }))
        );

  if (mode === "individual") {
    const pointLayerId = `lab-${layer.id}-individual`;
    map.addLayer({
      id: pointLayerId,
      type: "circle",
      source: sourceId,
      paint: {
        "circle-color": layer.color,
        "circle-radius": 5.5,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.2
      }
    });
    renderedLayerIds.set(layer.id, [pointLayerId]);
    registerLayerInteractions(layer.id, mode);
    return;
  }

  if (mode === "collective") {
    const circleLayerId = `lab-${layer.id}-cluster-circle`;
    const countLayerId = `lab-${layer.id}-cluster-count`;
    map.addLayer({
      id: circleLayerId,
      type: "circle",
      source: sourceId,
      paint: {
        "circle-color": layer.color,
        "circle-radius": [
          "step",
          ["get", "point_count"],
          13,
          12,
          17,
          35,
          21
        ],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2
      }
    });
    map.addLayer({
      id: countLayerId,
      type: "symbol",
      source: sourceId,
      layout: {
        "text-field": ["get", "point_count_abbreviated"],
        "text-size": 12,
        "text-font": ["Noto Sans Regular"],
        "text-allow-overlap": true,
        "text-ignore-placement": true
      },
      paint: {
        "text-color": "#ffffff"
      }
    });
    renderedLayerIds.set(layer.id, [circleLayerId, countLayerId]);
    registerLayerInteractions(layer.id, mode);
    return;
  }

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
  renderedLayerIds.set(layer.id, [heatLayerId, pointLayerId]);
  registerLayerInteractions(layer.id, mode);
}

function normalizeGenericLayerPoints(data) {
  return (data.features || [])
    .filter((feature) => feature?.geometry?.type === "Point" && Array.isArray(feature.geometry.coordinates))
    .map((feature) => ({
      lng: Number(feature.geometry.coordinates[0]),
      lat: Number(feature.geometry.coordinates[1]),
      name: feature.properties?.name || null,
      address: feature.properties?.address || null
    }))
    .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lng));
}

function normalizeAssessmentPoints(data) {
  return (data.properties || [])
    .filter((row) => row?.coordinates?.lat != null && row?.coordinates?.lng != null)
    .map((row) => ({
      lng: Number(row.coordinates.lng),
      lat: Number(row.coordinates.lat),
      name: row.canonical_address || row.name || "Assessment Property",
      address: row.canonical_address || "",
      value: row.assessment_value ?? null
    }))
    .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lng));
}

async function fetchLayerPoints(layer) {
  const viewport = getViewport();
  const state = layerState[layer.id];

  if (layer.id === "assessment_properties") {
    const response = await apiClient.getProperties({
      west: viewport.west,
      south: viewport.south,
      east: viewport.east,
      north: viewport.north,
      zoom: Math.max(viewport.zoom, 18),
      limit: Math.max(200, state.pointLimit)
    });
    return normalizeAssessmentPoints(response);
  }

  const response = await apiClient.getLayerData({
    layerId: layer.id,
    west: viewport.west,
    south: viewport.south,
    east: viewport.east,
    north: viewport.north,
    zoom: viewport.zoom
  });
  return normalizeGenericLayerPoints(response);
}

function updateMapMessage() {
  const enabled = LAB_LAYERS.filter((layer) => layerState[layer.id].enabled);
  if (!enabled.length) {
    setText(mapMessage, "No layers enabled.");
    return;
  }
  const summary = enabled
    .map((layer) => `${layer.label}: ${layerState[layer.id].pointsInView}`)
    .join(" | ");
  setText(mapMessage, summary);
}

async function refreshLayer(layerId) {
  const layer = LAB_LAYERS.find((item) => item.id === layerId);
  const state = layerState[layerId];
  const requestSeq = Number(requestSeqByLayer.get(layerId) || 0) + 1;
  requestSeqByLayer.set(layerId, requestSeq);

  if (!state.enabled) {
    removeRenderedLayer(layerId);
    renderControls();
    return;
  }

  state.status = "loading";
  renderControls();

  try {
    const points = await fetchLayerPoints(layer);
    if (requestSeqByLayer.get(layerId) !== requestSeq) {
      return;
    }

    const filteredPoints =
      state.mode === "individual"
        ? points.slice(0, state.pointLimit)
        : points;

    renderLayer(layer, filteredPoints, state.mode);
    state.status = "ready";
    state.pointsInView = filteredPoints.length;
    renderControls();
    updateMapMessage();
  } catch {
    if (requestSeqByLayer.get(layerId) !== requestSeq) {
      return;
    }
    state.status = "unavailable";
    state.pointsInView = 0;
    removeRenderedLayer(layerId);
    renderControls();
    updateMapMessage();
  }
}

async function refreshEnabledLayers() {
  await Promise.all(
    LAB_LAYERS
      .filter((layer) => layerState[layer.id].enabled)
      .map((layer) => refreshLayer(layer.id))
  );
  setGlobalStatus();
}

function initMap() {
  map = new window.maplibregl.Map({
    container: mapRoot,
    style: createRasterStyle(),
    center: [EDMONTON_CENTER[1], EDMONTON_CENTER[0]],
    zoom: 11,
    minZoom: 10,
    maxZoom: 19,
    maxBounds: [
      [EDMONTON_BOUNDS[0][1], EDMONTON_BOUNDS[0][0]],
      [EDMONTON_BOUNDS[1][1], EDMONTON_BOUNDS[1][0]]
    ]
  });
  map.addControl(new window.maplibregl.NavigationControl(), "top-right");

  const onViewportChange = debounce(() => {
    refreshEnabledLayers();
  }, 220);

  map.on("load", () => {
    refreshEnabledLayers();
  });
  map.on("moveend", onViewportChange);
  map.on("zoomend", onViewportChange);
}

renderControls();
initMap();
