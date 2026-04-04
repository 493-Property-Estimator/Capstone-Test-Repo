import {
  apiFetch,
  createBaseMap,
  formatCurrency,
  formatNumber,
  makeMarker,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const map = createBaseMap("map-root");
const mapStatus = document.getElementById("map-status");
const selectionResult = document.getElementById("selection-result");
const estimatorResult = document.getElementById("estimator-result");

let clickMarker = null;
let propertyMarker = null;
const SINGLE_CLICK_DELAY_MS = 220;
let pendingClickTimeoutId = null;

async function handleMapClick(event) {
  const lat = Number(event.latlng.lat.toFixed(6));
  const lon = Number(event.latlng.lng.toFixed(6));

  setStatus(mapStatus, `Loading nearest property for ${lat}, ${lon}...`);

  try {
    const result = await apiFetch("/nearest-property", {
      method: "POST",
      body: JSON.stringify({ lat, lon }),
    });

    if (clickMarker) {
      map.removeLayer(clickMarker);
    }
    if (propertyMarker) {
      map.removeLayer(propertyMarker);
    }

    clickMarker = makeMarker(lat, lon, "#e85d04", "Clicked point").addTo(map);
    propertyMarker = makeMarker(
      result.selected_property.lat,
      result.selected_property.lon,
      "#0f766e",
      result.selected_property.address,
    ).addTo(map);

    selectionResult.innerHTML = `
      <h4>Nearest property</h4>
      <p><strong>Address:</strong> ${result.selected_property.address}</p>
      <p><strong>Assessment value:</strong> ${formatCurrency(result.selected_property.assessment_value)}</p>
      <p><strong>Neighborhood:</strong> ${result.selected_property.neighbourhood || "N/A"}</p>
      <p><strong>Ward:</strong> ${result.selected_property.ward || "N/A"}</p>
      <p><strong>Distance from click:</strong> ${formatNumber(result.selected_property.distance_m)} m</p>
      <p><strong>Location ID:</strong> ${result.selected_property.canonical_location_id}</p>
    `;

    estimatorResult.innerHTML = `
      <h4>Nearest 15 properties estimator</h4>
      <p><strong>Sample size:</strong> ${formatNumber(result.estimator_summary.sample_size)}</p>
      <p><strong>Mean:</strong> ${formatCurrency(result.estimator_summary.mean)}</p>
      <p><strong>Median:</strong> ${formatCurrency(result.estimator_summary.median)}</p>
      <p><strong>Mode:</strong> ${
        result.estimator_summary.mode.length
          ? result.estimator_summary.mode.map(formatCurrency).join(", ")
          : "N/A"
      }</p>
    `;

    map.flyTo([lat, lon], Math.max(map.getZoom(), 14), { duration: 0.7 });
    setStatus(mapStatus, "Nearest property loaded.");
  } catch (error) {
    setStatus(mapStatus, error.message);
  }
}

map.on("click", (event) => {
  if (event.originalEvent?.button !== 0) {
    return;
  }

  if (pendingClickTimeoutId) {
    window.clearTimeout(pendingClickTimeoutId);
  }

  pendingClickTimeoutId = window.setTimeout(() => {
    pendingClickTimeoutId = null;
    handleMapClick(event);
  }, SINGLE_CLICK_DELAY_MS);
});

map.on("dblclick", (event) => {
  if (event.originalEvent?.button !== 0) {
    return;
  }

  if (pendingClickTimeoutId) {
    window.clearTimeout(pendingClickTimeoutId);
    pendingClickTimeoutId = null;
  }
});
