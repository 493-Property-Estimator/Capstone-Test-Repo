import {
  apiFetch,
  escapeHtml,
  formatCurrency,
  formatNumber,
  setActiveNav,
  setStatus,
} from "./common.js";

setActiveNav();

const statusElement = document.getElementById("estimator-status");
const summaryElement = document.getElementById("estimator-summary");
const warningElement = document.getElementById("estimator-warnings");
const factorElement = document.getElementById("factor-results");
const amenityElement = document.getElementById("amenity-results");

function collectAttributes() {
  const entries = {
    year_built: document.getElementById("year-built-input").value,
    lot_size: document.getElementById("lot-size-input").value,
    total_gross_area: document.getElementById("gross-area-input").value,
    garage: document.getElementById("garage-input").value,
    tax_class: document.getElementById("tax-class-input").value,
    zoning: document.getElementById("zoning-input").value,
  };

  return Object.fromEntries(
    Object.entries(entries).filter(([, value]) => value !== ""),
  );
}

function renderWarningList(payload) {
  const warnings = payload.warnings?.length
    ? payload.warnings
    : [{ severity: "low", message: "No warnings were returned." }];
  const missingFactors = payload.missing_factors?.length
    ? `<p><strong>Missing factors:</strong> ${payload.missing_factors.map(escapeHtml).join(", ")}</p>`
    : "<p><strong>Missing factors:</strong> None</p>";
  warningElement.innerHTML = `
    <div class="result-card">
      <h4>Warnings</h4>
      ${warnings
        .map(
          (warning) => `
            <p><strong>${escapeHtml(warning.severity || "info")}:</strong> ${escapeHtml(warning.message || "")}</p>
          `,
        )
        .join("")}
      ${missingFactors}
      <p><strong>Fallback flags:</strong> ${(payload.fallback_flags || []).map(escapeHtml).join(", ") || "None"}</p>
    </div>
  `;
}

function renderSummary(payload) {
  const matched = payload.matched_property;
  summaryElement.innerHTML = `
    <div class="metric-grid">
      <div class="metric">
        <span class="small muted">Final estimate</span>
        <strong>${formatCurrency(payload.final_estimate)}</strong>
      </div>
      <div class="metric">
        <span class="small muted">Baseline</span>
        <strong>${formatCurrency(payload.baseline?.assessment_value)}</strong>
      </div>
      <div class="metric">
        <span class="small muted">Estimate range</span>
        <strong>${formatCurrency(payload.low_estimate)} to ${formatCurrency(payload.high_estimate)}</strong>
      </div>
      <div class="metric">
        <span class="small muted">Confidence</span>
        <strong>${formatNumber(payload.confidence_score)}% (${escapeHtml(payload.confidence_label)})</strong>
      </div>
      <div class="metric">
        <span class="small muted">Completeness</span>
        <strong>${formatNumber(payload.completeness_score)}%</strong>
      </div>
      <div class="metric">
        <span class="small muted">Request ID</span>
        <strong>${escapeHtml(payload.request_id)}</strong>
      </div>
    </div>
    <p><strong>Baseline type:</strong> ${escapeHtml(payload.baseline?.baseline_type || "N/A")}</p>
    <p><strong>Baseline property:</strong> ${escapeHtml(payload.baseline?.address || "N/A")}</p>
    <p><strong>Matched property:</strong> ${matched ? escapeHtml(matched.address) : "No exact property match at this point"}</p>
    ${
      matched
        ? `<p><strong>Estimated minus assessed delta:</strong> ${formatCurrency(matched.estimate_minus_assessed_delta)}</p>`
        : ""
    }
    <p><strong>Primary neighbourhood:</strong> ${escapeHtml(payload.neighbourhood_context?.primary_neighbourhood || "N/A")}</p>
  `;
}

function renderFactors(payload) {
  const positives = payload.top_positive_factors || [];
  const negatives = payload.top_negative_factors || [];
  factorElement.innerHTML = `
    <div class="result-card">
      <h4>Positive factors</h4>
      ${
        positives.length
          ? positives
              .map(
                (factor) => `<p><strong>${escapeHtml(factor.label)}:</strong> ${formatCurrency(factor.value)}</p>`,
              )
              .join("")
          : "<p>No positive factors were returned.</p>"
      }
      <h4>Negative factors</h4>
      ${
        negatives.length
          ? negatives
              .map(
                (factor) => `<p><strong>${escapeHtml(factor.label)}:</strong> ${formatCurrency(factor.value)}</p>`,
              )
              .join("")
          : "<p>No negative factors were returned.</p>"
      }
    </div>
  `;
}

function renderAmenityRow(title, items) {
  if (!items?.length) {
    return `<div class="result-card"><h4>${escapeHtml(title)}</h4><p>No results returned.</p></div>`;
  }

  return `
    <div class="result-card">
      <h4>${escapeHtml(title)}</h4>
      ${items
        .map(
          (item) => `
            <p>
              <strong>${escapeHtml(item.name)}</strong><br />
              Straight line: ${formatNumber(item.straight_line_m)} m<br />
              Road: ${formatNumber(item.road_distance_m)} m<br />
              Car time: ${item.car_travel_time_min == null ? "N/A" : `${formatNumber(item.car_travel_time_min)} min`}<br />
              Transit distance: ${item.transit_distance_m == null ? "N/A" : `${formatNumber(item.transit_distance_m)} m`}<br />
              Transit time: ${item.transit_travel_time_min == null ? "N/A" : `${formatNumber(item.transit_travel_time_min)} min`}<br />
              Distance method: ${escapeHtml(item.distance_method)}
            </p>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderAmenities(payload) {
  const amenities = payload.feature_breakdown?.amenities || {};
  const downtown = payload.feature_breakdown?.downtown_accessibility;
  amenityElement.innerHTML = `
    ${renderAmenityRow("Parks", amenities.parks)}
    ${renderAmenityRow("Playgrounds", amenities.playgrounds)}
    ${renderAmenityRow("Schools", amenities.schools)}
    ${renderAmenityRow("Libraries", amenities.libraries)}
    ${renderAmenityRow("Downtown Edmonton", downtown ? [downtown] : [])}
  `;
}

document.getElementById("run-estimate").addEventListener("click", async () => {
  const payload = {
    lat: Number(document.getElementById("lat-input").value),
    lon: Number(document.getElementById("lon-input").value),
    property_attributes: collectAttributes(),
  };

  setStatus(statusElement, "Running estimate...");
  try {
    const result = await apiFetch("/property-estimate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderSummary(result);
    renderWarningList(result);
    renderFactors(result);
    renderAmenities(result);
    setStatus(statusElement, `Estimate ready (${result.request_id}).`);
  } catch (error) {
    setStatus(statusElement, error.message);
  }
});
