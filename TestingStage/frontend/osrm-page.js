import {
  apiFetch,
  escapeHtml,
  formatCurrency,
  formatDurationSeconds,
  formatNumber,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const statusElement = document.getElementById("osrm-status");

function readPoint(latId, lonId) {
  return {
    lat: Number(document.getElementById(latId).value),
    lon: Number(document.getElementById(lonId).value),
  };
}

function parseMatrixPoints() {
  return document.getElementById("matrix-points").value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [lat, lon] = line.split(",").map((value) => Number(value.trim()));
      return { lat, lon };
    });
}

function renderMatrixTable(title, matrix, formatter) {
  if (!matrix) {
    return `<p><strong>${escapeHtml(title)}:</strong> N/A</p>`;
  }

  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>${escapeHtml(title)}</th>
            ${matrix[0].map((_, index) => `<th>P${index + 1}</th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${matrix
            .map(
              (row, rowIndex) => `
                <tr>
                  <th>P${rowIndex + 1}</th>
                  ${row.map((value) => `<td>${escapeHtml(formatter(value))}</td>`).join("")}
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

document.getElementById("nearest-road-button").addEventListener("click", async () => {
  setStatus(statusElement, "Loading nearest road...");

  try {
    const point = readPoint("nearest-lat", "nearest-lon");
    const payload = await apiFetch("/osrm/nearest", {
      method: "POST",
      body: JSON.stringify({
        ...point,
        profile: document.getElementById("nearest-profile").value,
      }),
    });

    document.getElementById("nearest-road-result").innerHTML = `
      <h4>Nearest road result</h4>
      <p><strong>Requested profile:</strong> ${escapeHtml(payload.profile)}</p>
      <p><strong>Resolved OSRM profile:</strong> ${escapeHtml(payload.resolved_profile)}</p>
      <p><strong>Snapped point:</strong> ${escapeHtml(payload.waypoint.lat)}, ${escapeHtml(payload.waypoint.lon)}</p>
      <p><strong>Access distance:</strong> ${formatNumber(payload.waypoint.distance_m)} m</p>
      <p><strong>Name:</strong> ${escapeHtml(payload.waypoint.name || "Unnamed road")}</p>
    `;
    setStatus(statusElement, "Nearest road loaded.");
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

document.getElementById("nearest-property-button").addEventListener("click", async () => {
  setStatus(statusElement, "Loading nearest property...");

  try {
    const point = readPoint("property-lat", "property-lon");
    const payload = await apiFetch("/nearest-property", {
      method: "POST",
      body: JSON.stringify(point),
    });

    document.getElementById("nearest-property-result").innerHTML = `
      <h4>Nearest property</h4>
      <p><strong>Address:</strong> ${escapeHtml(payload.selected_property.address)}</p>
      <p><strong>Location ID:</strong> ${escapeHtml(payload.selected_property.canonical_location_id)}</p>
      <p><strong>Neighbourhood:</strong> ${escapeHtml(payload.selected_property.neighbourhood || "N/A")}</p>
      <p><strong>Distance:</strong> ${formatNumber(payload.selected_property.distance_m)} m</p>
      <p><strong>Assessment value:</strong> ${formatCurrency(payload.selected_property.assessment_value)}</p>
    `;
    setStatus(statusElement, "Nearest property loaded.");
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

document.getElementById("route-button").addEventListener("click", async () => {
  setStatus(statusElement, "Loading OSRM route...");

  try {
    const payload = await apiFetch("/osrm/route", {
      method: "POST",
      body: JSON.stringify({
        start: readPoint("route-start-lat", "route-start-lon"),
        end: readPoint("route-end-lat", "route-end-lon"),
        profile: document.getElementById("route-profile").value,
      }),
    });

    document.getElementById("route-result").innerHTML = `
      <h4>Route result</h4>
      <p><strong>Requested profile:</strong> ${escapeHtml(payload.profile)}</p>
      <p><strong>Resolved OSRM profile:</strong> ${escapeHtml(payload.resolved_profile)}</p>
      <p><strong>Route distance:</strong> ${formatNumber(payload.distance_m)} m</p>
      <p><strong>Route duration:</strong> ${escapeHtml(formatDurationSeconds(payload.duration_s))}</p>
      <p><strong>Start snap:</strong> ${payload.start_waypoint ? `${escapeHtml(payload.start_waypoint.lat)}, ${escapeHtml(payload.start_waypoint.lon)}` : "N/A"}</p>
      <p><strong>End snap:</strong> ${payload.end_waypoint ? `${escapeHtml(payload.end_waypoint.lat)}, ${escapeHtml(payload.end_waypoint.lon)}` : "N/A"}</p>
      <p><strong>Geometry points:</strong> ${payload.geometry?.coordinates?.length || 0}</p>
    `;
    setStatus(statusElement, "Route loaded.");
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

document.getElementById("matrix-button").addEventListener("click", async () => {
  setStatus(statusElement, "Loading OSRM matrix...");

  try {
    const payload = await apiFetch("/osrm/matrix", {
      method: "POST",
      body: JSON.stringify({
        points: parseMatrixPoints(),
        profile: document.getElementById("matrix-profile").value,
      }),
    });

    document.getElementById("matrix-result").innerHTML = `
      <h4>Matrix result</h4>
      <p><strong>Requested profile:</strong> ${escapeHtml(payload.profile)}</p>
      <p><strong>Resolved OSRM profile:</strong> ${escapeHtml(payload.resolved_profile)}</p>
      ${renderMatrixTable("Durations (s)", payload.durations_s, formatNumber)}
      ${renderMatrixTable("Distances (m)", payload.distances_m, formatNumber)}
    `;
    setStatus(statusElement, "Matrix loaded.");
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});
