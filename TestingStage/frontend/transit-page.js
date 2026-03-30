import {
  apiFetch,
  createBaseMap,
  escapeHtml,
  formatNumber,
  makeMarker,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const statusElement = document.getElementById("transit-status");
const routeSelect = document.getElementById("route-select");
const routeResult = document.getElementById("route-result");
const journeyResult = document.getElementById("journey-result");

const map = createBaseMap("transit-map-root");
const stopLayer = window.L.layerGroup().addTo(map);
const routeLayer = window.L.layerGroup().addTo(map);
const journeyLayer = window.L.layerGroup().addTo(map);

function clearLayers() {
  stopLayer.clearLayers();
  routeLayer.clearLayers();
  journeyLayer.clearLayers();
}

function parseLocationInput(value) {
  const trimmed = value.trim();
  const pieces = trimmed.split(",");
  if (pieces.length === 2) {
    const lat = Number(pieces[0].trim());
    const lon = Number(pieces[1].trim());
    if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
      return { lat, lon, label: trimmed };
    }
  }
  return { text: trimmed };
}

function fitMapToLayers(layers) {
  const group = window.L.featureGroup(layers.filter(Boolean));
  if (group.getLayers().length > 0) {
    map.fitBounds(group.getBounds().pad(0.15));
  }
}

function drawStops(stops, { clearExisting = false } = {}) {
  if (clearExisting) {
    stopLayer.clearLayers();
  }
  const markers = stops.map((stop) =>
    makeMarker(stop.lat, stop.lon, "#c84b31", `${escapeHtml(stop.name)} (${escapeHtml(stop.stop_id)})`).addTo(stopLayer),
  );
  return markers;
}

function drawRouteShapes(shapes, color = "#284b63") {
  routeLayer.clearLayers();
  const lines = shapes
    .filter((shape) => Array.isArray(shape.points) && shape.points.length > 1)
    .map((shape) =>
      window.L.polyline(
        shape.points.map((point) => [point[1], point[0]]),
        { color, weight: 4, opacity: 0.85 },
      )
        .bindPopup(
          `${escapeHtml(shape.trip_headsign || shape.shape_id || "Route shape")}<br />Trip: ${escapeHtml(shape.trip_id)}`,
        )
        .addTo(routeLayer),
    );
  return lines;
}

function renderRouteSummary(payload) {
  routeResult.innerHTML = `
    <h4>Route ${escapeHtml(payload.route_id)}</h4>
    <p><strong>Trips:</strong> ${formatNumber(payload.trip_count)}</p>
    <p><strong>Shapes:</strong> ${formatNumber(payload.shape_count)}</p>
    <p><strong>Matched stops:</strong> ${formatNumber(payload.stop_count)}</p>
    <p><strong>Headsigns:</strong> ${escapeHtml((payload.headsigns || []).join(", ") || "N/A")}</p>
    <p><strong>Directions:</strong> ${escapeHtml((payload.direction_ids || []).join(", ") || "N/A")}</p>
  `;
}

function renderJourney(payload) {
  const legsHtml = payload.legs
    .map((leg, index) => {
      if (leg.mode === "walk") {
        return `
          <div class="list-item">
            <h4>Leg ${index + 1}: Walk</h4>
            <p><strong>From:</strong> ${escapeHtml(leg.from.label)}</p>
            <p><strong>To:</strong> ${escapeHtml(leg.to.label)}</p>
            <p><strong>Distance:</strong> ${formatNumber(leg.distance_m)} m</p>
          </div>
        `;
      }
      return `
        <div class="list-item">
          <h4>Leg ${index + 1}: Route ${escapeHtml(leg.route_id)}</h4>
          <p><strong>From stop:</strong> ${escapeHtml(leg.from_stop_name)}</p>
          <p><strong>To stop:</strong> ${escapeHtml(leg.to_stop_name)}</p>
          <p><strong>Headsign:</strong> ${escapeHtml(leg.headsign || "N/A")}</p>
          <p><strong>Distance:</strong> ${formatNumber(leg.distance_m)} m</p>
          <p><strong>Segments merged:</strong> ${formatNumber(leg.segment_count)}</p>
        </div>
      `;
    })
    .join("");

  journeyResult.innerHTML = `
    <h4>Journey summary</h4>
    <p><strong>Origin:</strong> ${escapeHtml(payload.origin.label)}</p>
    <p><strong>Destination:</strong> ${escapeHtml(payload.destination.label)}</p>
    <p><strong>Routes used:</strong> ${escapeHtml(payload.summary.routes_used.join(", ") || "N/A")}</p>
    <p><strong>Transfers:</strong> ${formatNumber(payload.summary.transfer_count)}</p>
    <p><strong>Total distance:</strong> ${formatNumber(payload.summary.total_distance_m)} m</p>
    <p><strong>Walking distance:</strong> ${formatNumber(payload.summary.walking_distance_m)} m</p>
    <p><strong>Transit distance:</strong> ${formatNumber(payload.summary.transit_distance_m)} m</p>
    <div class="list">${legsHtml}</div>
  `;
}

function drawJourney(payload) {
  journeyLayer.clearLayers();
  const layers = [];

  const originMarker = makeMarker(payload.origin.lat, payload.origin.lon, "#0f766e", `Origin: ${escapeHtml(payload.origin.label)}`).addTo(journeyLayer);
  const destinationMarker = makeMarker(payload.destination.lat, payload.destination.lon, "#c1121f", `Destination: ${escapeHtml(payload.destination.label)}`).addTo(journeyLayer);
  layers.push(originMarker, destinationMarker);

  for (const leg of payload.legs) {
    if (leg.mode === "walk") {
      const line = window.L.polyline(
        [
          [leg.from.lat, leg.from.lon],
          [leg.to.lat, leg.to.lon],
        ],
        { color: "#6b7280", weight: 3, dashArray: "6 6" },
      ).addTo(journeyLayer);
      layers.push(line);
      continue;
    }

    if (leg.from_lat != null && leg.from_lon != null && leg.to_lat != null && leg.to_lon != null) {
      const line = window.L.polyline(
        [
          [leg.from_lat, leg.from_lon],
          [leg.to_lat, leg.to_lon],
        ],
        { color: "#1d4ed8", weight: 5, opacity: 0.85 },
      ).bindPopup(`Route ${escapeHtml(leg.route_id)}`).addTo(journeyLayer);
      layers.push(line);
    }
  }

  fitMapToLayers(layers);
}

async function loadRoutes() {
  setStatus(statusElement, "Loading transit routes...");
  const payload = await apiFetch("/transit/routes");
  routeSelect.innerHTML = "";
  if (!payload.routes.length) {
    routeSelect.innerHTML = `<option value="">No routes loaded in transit_prod</option>`;
    setStatus(statusElement, "Transit routes are not available in the database yet.");
    return;
  }
  routeSelect.innerHTML = payload.routes
    .map(
      (route) =>
        `<option value="${escapeHtml(route.route_id)}">${escapeHtml(route.route_id)}${route.headsigns?.length ? ` - ${escapeHtml(route.headsigns[0])}` : ""}</option>`,
    )
    .join("");
  setStatus(statusElement, `Loaded ${payload.route_count} routes.`);
}

document.getElementById("load-stops-button").addEventListener("click", async () => {
  setStatus(statusElement, "Loading all transit stops...");
  try {
    const payload = await apiFetch("/transit/stops");
    const markers = drawStops(payload.stops, { clearExisting: true });
    if (markers.length) {
      fitMapToLayers(markers);
    }
    routeResult.innerHTML = `
      <h4>All transit stops</h4>
      <p><strong>Stops loaded:</strong> ${formatNumber(payload.stop_count)}</p>
    `;
    setStatus(statusElement, `Loaded ${payload.stop_count} transit stops.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

document.getElementById("show-route-button").addEventListener("click", async () => {
  const routeId = routeSelect.value;
  if (!routeId) {
    setStatus(statusElement, "Choose a route first.");
    return;
  }
  setStatus(statusElement, `Loading route ${routeId}...`);
  try {
    const payload = await apiFetch(`/transit/route?route_id=${encodeURIComponent(routeId)}`);
    renderRouteSummary(payload);
    const markers = drawStops(payload.stops.slice(0, 250), { clearExisting: true });
    const lines = drawRouteShapes(payload.shapes);
    fitMapToLayers([...markers, ...lines]);
    setStatus(statusElement, `Displayed route ${routeId}.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

document.getElementById("show-route-stops-button").addEventListener("click", async () => {
  const routeId = routeSelect.value;
  if (!routeId) {
    setStatus(statusElement, "Choose a route first.");
    return;
  }
  setStatus(statusElement, `Loading stops for route ${routeId}...`);
  try {
    const payload = await apiFetch(`/transit/stops?route_id=${encodeURIComponent(routeId)}`);
    const markers = drawStops(payload.stops, { clearExisting: true });
    if (markers.length) {
      fitMapToLayers(markers);
    }
    routeResult.innerHTML = `
      <h4>Route ${escapeHtml(routeId)} stops</h4>
      <p><strong>Stops shown:</strong> ${formatNumber(payload.stop_count)}</p>
    `;
    setStatus(statusElement, `Loaded ${payload.stop_count} stops for route ${routeId}.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

document.getElementById("plan-journey-button").addEventListener("click", async () => {
  const origin = document.getElementById("journey-origin").value.trim();
  const destination = document.getElementById("journey-destination").value.trim();
  if (!origin || !destination) {
    setStatus(statusElement, "Enter both origin and destination.");
    return;
  }
  setStatus(statusElement, "Planning transit journey...");
  try {
    const payload = await apiFetch("/transit/journey", {
      method: "POST",
      body: JSON.stringify({
        origin: parseLocationInput(origin),
        destination: parseLocationInput(destination),
      }),
    });
    renderJourney(payload);
    drawJourney(payload);
    setStatus(statusElement, "Transit journey loaded.");
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

document.getElementById("clear-map-button").addEventListener("click", () => {
  clearLayers();
  setStatus(statusElement, "Transit map layers cleared.");
});

loadRoutes().catch((error) => {
  setStatus(statusElement, error.message);
});
