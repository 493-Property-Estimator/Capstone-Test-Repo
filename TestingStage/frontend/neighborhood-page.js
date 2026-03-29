import {
  apiFetch,
  formatCurrency,
  formatNumber,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const selectElement = document.getElementById("neighborhood-select");
const detailLevelElement = document.getElementById("detail-level-select");
const statusElement = document.getElementById("neighborhood-status");
const resultsElement = document.getElementById("neighborhood-results");
const roadResultsElement = document.getElementById("neighborhood-road-results");

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
      `/neighborhood-summary?name=${encodeURIComponent(selectElement.value)}&detail_level=${encodeURIComponent(detailLevelElement.value)}`,
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
          <div class="metric">
            <span class="small muted">Average house age</span>
            <strong>${formatNumber(payload.average_house_age_years)} years</strong>
          </div>
          <div class="metric">
            <span class="small muted">Average house size</span>
            <strong>${formatNumber(payload.average_house_size)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Rows in average age</span>
            <strong>${formatNumber(payload.house_age_row_count)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Rows in average size</span>
            <strong>${formatNumber(payload.house_size_row_count)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Garage yes rows</span>
            <strong>${formatNumber(payload.garage_yes_row_count)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Garage known rows</span>
            <strong>${formatNumber(payload.garage_known_row_count)}</strong>
          </div>
          <div class="metric">
            <span class="small muted">Garage percentage</span>
            <strong>${formatNumber(payload.garage_percentage)}%</strong>
          </div>
          <div class="metric">
            <span class="small muted">Total rows considered</span>
            <strong>${formatNumber(payload.total_row_count_considered)}</strong>
          </div>
        </div>
        <p><strong>Area codes:</strong> ${payload.area_codes.join(", ") || "N/A"}</p>
        <p><strong>Method note:</strong> ${payload.bounding_box_method}</p>
      </div>
    `;

    roadResultsElement.innerHTML =
      payload.detail_level === "detailed"
        ? `
          <div class="result-card">
            <h4>Road distance by road type</h4>
            <p>These distances are grouped from road segment types within the selected neighbourhood bounding box.</p>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Road type</th>
                    <th>Total length (m)</th>
                    <th>Segment count</th>
                  </tr>
                </thead>
                <tbody>
                  ${
                    payload.road_type_breakdown.length
                      ? payload.road_type_breakdown
                          .map(
                            (item) => `
                              <tr>
                                <td>${item.road_type}</td>
                                <td>${formatNumber(item.road_length_m)}</td>
                                <td>${formatNumber(item.segment_count)}</td>
                              </tr>
                            `,
                          )
                          .join("")
                      : '<tr><td colspan="3">No road type results were returned.</td></tr>'
                  }
                </tbody>
              </table>
            </div>
          </div>
        `
        : '<div class="result-card">Detailed road results appear here when detailed mode is selected.</div>';

    setStatus(statusElement, `${payload.neighbourhood} loaded.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

loadNeighborhoods();
