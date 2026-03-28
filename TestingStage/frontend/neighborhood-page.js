import {
  apiFetch,
  formatCurrency,
  formatNumber,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const selectElement = document.getElementById("neighborhood-select");
const statusElement = document.getElementById("neighborhood-status");
const resultsElement = document.getElementById("neighborhood-results");

async function loadNeighborhoods() {
  try {
    const payload = await apiFetch("/neighborhoods");
    selectElement.innerHTML = payload.neighborhoods
      .map((name) => `<option value="${name}">${name}</option>`)
      .join("");
    setStatus(statusElement, `${payload.neighborhoods.length} neighborhoods loaded.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
}

document.getElementById("load-neighborhood").addEventListener("click", async () => {
  setStatus(statusElement, `Loading ${selectElement.value}...`);

  try {
    const payload = await apiFetch(
      `/neighborhood-summary?name=${encodeURIComponent(selectElement.value)}`,
    );

    resultsElement.innerHTML = `
      <div class="result-card">
        <h4>${payload.neighbourhood}</h4>
        <div class="metric-grid">
          <div class="metric">
            <span class="small muted">Number of properties</span>
            <strong>${formatNumber(payload.number_of_properties)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Average assessment</span>
            <strong>${formatCurrency(payload.average_assessment)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Schools</span>
            <strong>${formatNumber(payload.number_of_schools)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Parks</span>
            <strong>${formatNumber(payload.number_of_parks)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Playgrounds</span>
            <strong>${formatNumber(payload.number_of_playgrounds)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Road length</span>
            <strong>${formatNumber(payload.road_length_m)} m</strong>
          </div>
        </div>
        <p><strong>Area codes:</strong> ${payload.area_codes.join(", ") || "N/A"}</p>
        <p><strong>Method note:</strong> ${payload.bounding_box_method}</p>
      </div>
    `;

    setStatus(statusElement, `${payload.neighbourhood} loaded.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

loadNeighborhoods();
