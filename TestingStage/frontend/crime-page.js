import {
  apiFetch,
  escapeHtml,
  formatNumber,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const neighbourhoodInput = document.getElementById("crime-neighbourhood");
const propertyInput = document.getElementById("crime-property");
const radiusInput = document.getElementById("crime-radius");
const statusElement = document.getElementById("crime-status");
const resultElement = document.getElementById("crime-result");

function getResolvedNeighbourhood(payload) {
  if (payload.neighbourhood) {
    return payload.neighbourhood;
  }
  if (payload.property_match && payload.property_match.neighbourhood) {
    return payload.property_match.neighbourhood;
  }
  return "N/A";
}

async function loadNeighborhoods() {
  try {
    const payload = await apiFetch("/neighborhoods");
    neighbourhoodInput.innerHTML = payload.neighborhoods
      .map((name) => `<option value="${name}">${name}</option>`)
      .join("");
    setStatus(statusElement, `${payload.neighborhoods.length} neighborhoods loaded.`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
}

function renderCrimeResult(payload) {
  if (!payload.available) {
    resultElement.innerHTML = `
      <h4>Crime provider unavailable</h4>
      <p>${escapeHtml(payload.message || "No crime data is available.")}</p>
      <p><strong>TODO:</strong> ${escapeHtml(payload.todo || "Add a provider.")}</p>
      ${payload.property_match ? `<p><strong>Resolved property:</strong> ${escapeHtml(payload.property_match.address)}</p>` : ""}
    `;
    return;
  }

  resultElement.innerHTML = `
    <h4>Crime summary</h4>
    <p><strong>Scope:</strong> ${escapeHtml(payload.summary_scope)}</p>
    <p><strong>Neighbourhood:</strong> ${escapeHtml(getResolvedNeighbourhood(payload))}</p>
    <p><strong>Total incidents:</strong> ${formatNumber(payload.total_incidents)}</p>
    ${
      payload.property_match
        ? `<p><strong>Resolved property:</strong> ${escapeHtml(payload.property_match.address)} (${escapeHtml(payload.property_match.canonical_location_id)})</p>`
        : ""
    }
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Crime type</th>
            <th>Count</th>
          </tr>
        </thead>
        <tbody>
          ${(payload.crime_types || [])
            .map(
              (item) => `
                <tr>
                  <td>${escapeHtml(item.crime_type)}</td>
                  <td>${formatNumber(item.count)}</td>
                </tr>
              `,
            )
            .join("") || '<tr><td colspan="2">No crime rows returned.</td></tr>'}
        </tbody>
      </table>
    </div>
  `;
}

document.getElementById("crime-neighbourhood-button").addEventListener("click", async () => {
  setStatus(statusElement, "Loading neighbourhood crime summary...");

  try {
    const payload = await apiFetch("/crime-summary", {
      method: "POST",
      body: JSON.stringify({
        neighbourhood: neighbourhoodInput.value,
      }),
    });
    renderCrimeResult(payload);
    setStatus(statusElement, "Crime summary loaded.");
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

document.getElementById("crime-property-button").addEventListener("click", async () => {
  setStatus(statusElement, "Loading property crime summary...");

  try {
    const payload = await apiFetch("/crime-summary", {
      method: "POST",
      body: JSON.stringify({
        property_query: propertyInput.value,
        radius_m: Number(radiusInput.value),
      }),
    });
    renderCrimeResult(payload);
    setStatus(statusElement, "Crime summary loaded.");
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

loadNeighborhoods();
