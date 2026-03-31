import {
  apiFetch,
  escapeHtml,
  formatNumber,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const latInput = document.getElementById("lat-input");
const lonInput = document.getElementById("lon-input");
const limitInput = document.getElementById("limit-input");
const sourceInput = document.getElementById("source-input");
const selectElement = document.getElementById("neighbourhood-input");
const categoryInput = document.getElementById("category-input");
const typeInput = document.getElementById("type-input");
const radiusInput = document.getElementById("radius-input");
const statusElement = document.getElementById("topx-status");
const resultsElement = document.getElementById("topx-results");

async function loadNeighborhoods() {
  try {
    const payload = await apiFetch("/neighborhoods");
    selectElement.innerHTML = payload.neighborhoods
      .map((name) => `<option value="${name}">${name}</option>`)
      .join("");
    selectElement.insertAdjacentHTML(
      "afterbegin",
      '<option value="">No neighbourhood filter</option>',
    );
    setStatus(statusElement, `${payload.neighborhoods.length} neighborhoods loaded.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
}

function renderResults(items) {
  resultsElement.innerHTML = items.length
    ? items
        .map(
          (item, index) => `
            <div class="result-card">
              <h4>${index + 1}. ${escapeHtml(item.name)}</h4>
              <p><strong>Category:</strong> ${escapeHtml(item.raw_category || "N/A")}</p>
              <p><strong>Type:</strong> ${escapeHtml(item.raw_subcategory || "N/A")}</p>
              <p><strong>Address:</strong> ${escapeHtml(item.address || "N/A")}</p>
              <p><strong>Neighbourhood:</strong> ${escapeHtml(item.neighbourhood || "N/A")}</p>
              <p><strong>Source:</strong> ${escapeHtml(item.source_dataset || "N/A")} (${escapeHtml(item.source_provider || "N/A")})</p>
              <p><strong>Coordinates:</strong> ${escapeHtml(item.lat)}, ${escapeHtml(item.lon)}</p>
              <p><strong>Distance:</strong> ${formatNumber(item.distance_m)}${item.distance_m == null ? "" : " m"}</p>
            </div>
          `,
        )
        .join("")
    : '<div class="result-card">No results were returned.</div>';
}

async function runLookup(category) {
  setStatus(statusElement, `Loading ${category}...`);

  try {
    const result = await apiFetch("/top-x", {
      method: "POST",
      body: JSON.stringify({
        lat: Number(latInput.value),
        lon: Number(lonInput.value),
        limit: Number(limitInput.value),
        category,
      }),
    });

    renderResults(result.results);
    setStatus(statusElement, `${result.results.length} ${category} loaded.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
}

async function runPoiQuery() {
  setStatus(statusElement, "Loading POIs...");

  try {
    const result = await apiFetch("/pois/query", {
      method: "POST",
      body: JSON.stringify({
        lat: Number(latInput.value),
        lon: Number(lonInput.value),
        limit: Number(limitInput.value),
        radius_m: Number(radiusInput.value),
        source: sourceInput.value,
        neighbourhood: selectElement.value,
        category: categoryInput.value,
        type: typeInput.value,
      }),
    });

    renderResults(result.results);
    setStatus(statusElement, `${result.results.length} POIs loaded.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
}

document.getElementById("schools-button").addEventListener("click", () => {
  runLookup("schools");
});

document.getElementById("parks-button").addEventListener("click", () => {
  runLookup("parks");
});

document.getElementById("poi-query-button").addEventListener("click", () => {
  runPoiQuery();
});

loadNeighborhoods();
