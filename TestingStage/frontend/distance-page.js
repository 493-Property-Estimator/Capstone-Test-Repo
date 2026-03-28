import {
  apiFetch,
  formatNumber,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const points = [];
const pointsList = document.getElementById("points-list");
const addPointForm = document.getElementById("add-point-form");
const newLatInput = document.getElementById("new-lat");
const newLonInput = document.getElementById("new-lon");
const statusElement = document.getElementById("distance-status");
const resultsElement = document.getElementById("distance-results");
const totalStraightLine = document.getElementById("total-straight-line");
const totalRoadDistance = document.getElementById("total-road-distance");

function renderPoints() {
  if (!points.length) {
    pointsList.innerHTML = '<div class="result-card">No points added yet.</div>';
    return;
  }

  pointsList.innerHTML = points
    .map((point, index) => {
      const buttonLabel = point.isEditing ? "Enter" : "Edit";
      return `
        <div class="list-item">
          <div class="entry-row">
            <label>
              Latitude
              <input data-role="lat" data-index="${index}" type="number" step="0.000001" value="${point.lat}" ${point.isEditing ? "" : "disabled"} />
            </label>
            <label>
              Longitude
              <input data-role="lon" data-index="${index}" type="number" step="0.000001" value="${point.lon}" ${point.isEditing ? "" : "disabled"} />
            </label>
            <button data-action="toggle-edit" data-index="${index}" type="button">${buttonLabel}</button>
            <button data-action="delete" data-index="${index}" class="secondary" type="button">Delete</button>
          </div>
        </div>
      `;
    })
    .join("");
}

addPointForm.addEventListener("submit", (event) => {
  event.preventDefault();
  points.push({
    lat: Number(newLatInput.value),
    lon: Number(newLonInput.value),
    isEditing: false,
  });
  newLatInput.value = "";
  newLonInput.value = "";
  renderPoints();
  setStatus(statusElement, `${points.length} point(s) in the list.`);
});

pointsList.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  const index = Number(target.dataset.index);
  if (Number.isNaN(index)) {
    return;
  }

  if (target.dataset.action === "delete") {
    points.splice(index, 1);
    renderPoints();
    setStatus(statusElement, `${points.length} point(s) in the list.`);
    return;
  }

  if (target.dataset.action === "toggle-edit") {
    if (points[index].isEditing) {
      const latInput = pointsList.querySelector(`input[data-role="lat"][data-index="${index}"]`);
      const lonInput = pointsList.querySelector(`input[data-role="lon"][data-index="${index}"]`);
      points[index].lat = Number(latInput.value);
      points[index].lon = Number(lonInput.value);
      points[index].isEditing = false;
      setStatus(statusElement, `Point ${index + 1} updated.`);
    } else {
      points[index].isEditing = true;
      setStatus(statusElement, `Editing point ${index + 1}.`);
    }

    renderPoints();
  }
});

document.getElementById("calculate-distances").addEventListener("click", async () => {
  setStatus(statusElement, "Computing distances...");

  try {
    const payload = await apiFetch("/point-distances", {
      method: "POST",
      body: JSON.stringify({
        points: points.map(({ lat, lon }) => ({ lat, lon })),
      }),
    });

    totalStraightLine.textContent = `${formatNumber(payload.total_straight_line_m)} m`;
    totalRoadDistance.textContent = `${formatNumber(payload.total_road_distance_m)} m`;

    resultsElement.innerHTML = payload.segments
      .map(
        (segment) => `
          <div class="result-card">
            <h4>Point ${segment.from_index + 1} to point ${segment.to_index + 1}</h4>
            <p><strong>Straight-line distance:</strong> ${formatNumber(segment.straight_line_m)} m</p>
            <p><strong>Road distance:</strong> ${formatNumber(segment.road_distance_m)} m</p>
            <p><strong>Routing mode:</strong> ${segment.routing_mode}</p>
          </div>
        `,
      )
      .join("");

    setStatus(statusElement, "Distance calculation complete.");
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});

renderPoints();
