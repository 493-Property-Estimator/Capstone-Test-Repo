import {
  apiFetch,
  formatNumber,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const latInput = document.getElementById("lat-input");
const lonInput = document.getElementById("lon-input");
const limitInput = document.getElementById("limit-input");
const statusElement = document.getElementById("topx-status");
const resultsElement = document.getElementById("topx-results");

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

    resultsElement.innerHTML = result.results.length
      ? result.results
          .map(
            (item, index) => `
              <div class="result-card">
                <h4>${index + 1}. ${item.name}</h4>
                <p><strong>Category:</strong> ${item.raw_category}</p>
                <p><strong>Address:</strong> ${item.address || "N/A"}</p>
                <p><strong>Coordinates:</strong> ${item.lat}, ${item.lon}</p>
                <p><strong>Distance:</strong> ${formatNumber(item.distance_m)} m</p>
              </div>
            `,
          )
          .join("")
      : '<div class="result-card">No results were returned.</div>';

    setStatus(statusElement, `${result.results.length} ${category} loaded.`);
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

document.getElementById("tbd-button").addEventListener("click", () => {
  setStatus(statusElement, "TBD button is intentionally not wired yet.");
});
