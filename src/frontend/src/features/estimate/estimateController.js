/* node:coverage disable */
import { clearElement, createElement, setText } from "../../utils/dom.js";
import {
  ESTIMATE_OPTIONS_DEFAULTS,
  ESTIMATE_REQUESTED_FACTORS,
  ESTIMATE_WEIGHT_DEFAULTS
} from "../../config.js";

function formatCurrency(value) {
  if (typeof value !== "number") {
    return "--";
  }

  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0
  }).format(value);
}

export function createEstimateController({
  apiClient,
  store,
  submitButton,
  resetButton,
  statusElement,
  locationSummary,
  selectionMeta,
  estimatePanel,
  validationMessage,
  formElements
}) {
  function showValidation(message) {
    validationMessage.textContent = message;
    validationMessage.classList.remove("is-hidden");
  }

  function clearValidation() {
    validationMessage.textContent = "";
    validationMessage.classList.add("is-hidden");
  }

  function normalizeNumber(value) {
    if (value === "" || value === null || value === undefined) {
      return undefined;
    }

    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  function normalizeCoordinates(value) {
    if (!value) {
      return null;
    }

    if (typeof value === "string") {
      try {
        return normalizeCoordinates(JSON.parse(value));
      } catch {
        return null;
      }
    }

    if (typeof value !== "object") {
      return null;
    }

    const lat = normalizeNumber(value.lat);
    const lng = normalizeNumber(value.lng);

    if (lat === undefined || lng === undefined) {
      return null;
    }

    return { lat, lng };
  }

  function buildPayload() {
    const state = store.getState();
    const latitude = normalizeNumber(formElements.latitudeInput.value);
    const longitude = normalizeNumber(formElements.longitudeInput.value);
    const bedrooms = normalizeNumber(formElements.bedroomsInput.value);
    const bathrooms = normalizeNumber(formElements.bathroomsInput.value);
    const floorArea = normalizeNumber(formElements.floorAreaInput.value);
    const desiredFactorOutputs = [
      formElements.factorCrimeInput.checked ? "crime_statistics" : null,
      formElements.factorSchoolsInput.checked ? "school_access" : null,
      formElements.factorGreenSpaceInput.checked ? "green_space" : null,
      formElements.factorCommuteInput.checked ? "commute_access" : null
    ].filter(Boolean);

    const coordinates =
      latitude !== undefined && longitude !== undefined
        ? { lat: latitude, lng: longitude }
        : normalizeCoordinates(state.selectedLocation?.coordinates);

    if (!coordinates) {
      throw new Error(
        "Provide an address, click the map, or enter latitude and longitude."
      );
    }

    if (
      coordinates.lat < 53.3958 ||
      coordinates.lat > 53.716 ||
      coordinates.lng < -113.7136 ||
      coordinates.lng > -113.2714
    ) {
      throw new Error("Coordinates must be within the supported Edmonton area.");
    }

    return {
      location: {
        canonical_location_id: state.selectedLocation?.canonical_location_id,
        coordinates,
        ...(latitude === undefined || longitude === undefined
          ? { address: state.selectedLocation?.canonical_address }
          : {})
      },
      property_details: {
        ...(bedrooms !== undefined ? { bedrooms } : {}),
        ...(bathrooms !== undefined ? { bathrooms } : {}),
        ...(floorArea !== undefined ? { floor_area_sqft: floorArea } : {})
      },
      options: {
        include_breakdown: formElements.includeBreakdownInput.checked,
        include_top_factors: formElements.includeTopFactorsInput.checked,
        include_warnings: formElements.includeWarningsInput.checked,
        include_layers_context: formElements.includeLayersContextInput.checked,
        desired_factor_outputs: desiredFactorOutputs,
        weights: {
          crime_statistics: normalizeNumber(formElements.weightCrimeInput.value) ?? ESTIMATE_WEIGHT_DEFAULTS.crime,
          school_access: normalizeNumber(formElements.weightSchoolsInput.value) ?? ESTIMATE_WEIGHT_DEFAULTS.schools,
          green_space: normalizeNumber(formElements.weightGreenSpaceInput.value) ?? ESTIMATE_WEIGHT_DEFAULTS.greenSpace,
          commute_access: normalizeNumber(formElements.weightCommuteInput.value) ?? ESTIMATE_WEIGHT_DEFAULTS.commute
        }
      }
    };
  }

  /* node:coverage disable */
  function renderEstimate(estimate) {
    clearElement(estimatePanel);

    if (!estimate) {
      estimatePanel.appendChild(createElement("p", "empty-state", "No estimate loaded."));
      return;
    }

    const metrics = createElement("div", "estimate-grid");
    [
      ["Estimate", formatCurrency(estimate.final_estimate)],
      ["Baseline", formatCurrency(estimate.baseline_value)],
      ["Low", formatCurrency(estimate.range?.low)],
      ["High", formatCurrency(estimate.range?.high)]
    ].forEach(([label, value]) => {
      const metric = createElement("article", "estimate-metric");
      metric.appendChild(createElement("span", "estimate-label", label));
      metric.appendChild(createElement("div", "estimate-value", value));
      metrics.appendChild(metric);
    });
    estimatePanel.appendChild(metrics);

    const summaryGrid = createElement("div", "estimate-grid");
    [
      ["Estimated At", estimate.estimated_at ? new Date(estimate.estimated_at).toLocaleString("en-CA") : "--"],
      ["Confidence", estimate.confidence?.percentage != null ? `${estimate.confidence.percentage}%` : "--"]
    ].forEach(([label, value]) => {
      const metric = createElement("article", "estimate-metric");
      metric.appendChild(createElement("span", "estimate-label", label));
      metric.appendChild(createElement("div", "estimate-value", value));
      summaryGrid.appendChild(metric);
    });
    estimatePanel.appendChild(summaryGrid);

    const factorsSection = createElement("details", "collapsible-section");
    factorsSection.open = false;

    const factorsSummary = createElement("summary", "collapsible-summary");
    factorsSummary.appendChild(createElement("h3", null, "Top Factors"));
    factorsSection.appendChild(factorsSummary);

    const factorsBody = createElement("div", "collapsible-body");
    if (!estimate.factor_breakdown?.length) {
      factorsBody.appendChild(
        createElement("p", "empty-state", "No factor breakdown returned.")
      );
    } else {
      estimate.factor_breakdown.forEach((factor) => {
        const item = createElement("article", "factor-item");
        item.appendChild(
          createElement(
            "div",
            "suggestion-title",
            `${factor.label} · ${formatCurrency(factor.value)}`
          )
        );
        item.appendChild(
          createElement("div", "factor-meta", `Status: ${factor.status}`)
        );
        item.appendChild(
          createElement("p", "factor-summary", factor.summary || "No summary provided.")
        );
        factorsBody.appendChild(item);
      });
    }

    factorsSection.appendChild(factorsBody);
    estimatePanel.appendChild(factorsSection);

    const topFactorsSection = createElement("details", "collapsible-section");
    topFactorsSection.open = false;
    const topFactorsSummary = createElement("summary", "collapsible-summary");
    topFactorsSummary.appendChild(createElement("h3", null, "Top Positive / Negative Factors"));
    topFactorsSection.appendChild(topFactorsSummary);
    const topFactorsBody = createElement("div", "collapsible-body");
    [
      ["Top Positive Factors", estimate.top_positive_factors || []],
      ["Top Negative Factors", estimate.top_negative_factors || []]
    ].forEach(([heading, factors]) => {
      topFactorsBody.appendChild(createElement("h4", null, heading));
      if (!factors.length) {
        topFactorsBody.appendChild(createElement("p", "empty-state", "No factors returned."));
      } else {
        factors.forEach((factor) => {
          const item = createElement("article", "factor-item");
          item.appendChild(createElement("div", "suggestion-title", `${factor.label} · ${formatCurrency(factor.value)}`));
          item.appendChild(createElement("div", "factor-meta", `Status: ${factor.status}`));
          item.appendChild(createElement("p", "factor-summary", factor.summary || "No summary provided."));
          topFactorsBody.appendChild(item);
        });
      }
    });
    topFactorsSection.appendChild(topFactorsBody);
    estimatePanel.appendChild(topFactorsSection);

  }
  /* node:coverage enable */

  function syncSliderOutputs() {
    formElements.weightCrimeOutput.textContent = formElements.weightCrimeInput.value;
    formElements.weightSchoolsOutput.textContent = formElements.weightSchoolsInput.value;
    formElements.weightGreenSpaceOutput.textContent = formElements.weightGreenSpaceInput.value;
    formElements.weightCommuteOutput.textContent = formElements.weightCommuteInput.value;
  }

  function applyEstimateDefaults() {
    formElements.includeBreakdownInput.checked = ESTIMATE_OPTIONS_DEFAULTS.includeBreakdown;
    formElements.includeTopFactorsInput.checked = ESTIMATE_OPTIONS_DEFAULTS.includeTopFactors;
    formElements.includeWarningsInput.checked = ESTIMATE_OPTIONS_DEFAULTS.includeWarnings;
    formElements.includeLayersContextInput.checked = ESTIMATE_OPTIONS_DEFAULTS.includeLayersContext;
    formElements.factorCrimeInput.checked = ESTIMATE_REQUESTED_FACTORS.includes("crime_statistics");
    formElements.factorSchoolsInput.checked = ESTIMATE_REQUESTED_FACTORS.includes("school_access");
    formElements.factorGreenSpaceInput.checked = ESTIMATE_REQUESTED_FACTORS.includes("green_space");
    formElements.factorCommuteInput.checked = ESTIMATE_REQUESTED_FACTORS.includes("commute_access");
    formElements.weightCrimeInput.value = String(ESTIMATE_WEIGHT_DEFAULTS.crime);
    formElements.weightSchoolsInput.value = String(ESTIMATE_WEIGHT_DEFAULTS.schools);
    formElements.weightGreenSpaceInput.value = String(ESTIMATE_WEIGHT_DEFAULTS.greenSpace);
    formElements.weightCommuteInput.value = String(ESTIMATE_WEIGHT_DEFAULTS.commute);
    syncSliderOutputs();
  }

  async function requestEstimate() {
    clearValidation();
    setText(statusElement, "Loading");

    try {
      const payload = buildPayload();
      const response = await apiClient.getEstimate(payload);

      store.setState({ estimate: response, warningsCollapsed: true });
      setText(statusElement, response.status === "partial" ? "Partial" : "Ready");
    } catch (error) {
      setText(statusElement, "Error");
      showValidation(error.message);
      store.setState({
        estimate: {
          warnings: [
            {
              code: "ESTIMATE_UNAVAILABLE",
              severity: "critical",
              title: "Estimate unavailable",
              message: error.message,
              affected_factors: [],
              dismissible: false
            }
          ],
          confidence: null,
          factor_breakdown: []
        }
      });
    }
  }

  submitButton.addEventListener("click", requestEstimate);
  resetButton.addEventListener("click", () => {
    clearValidation();
    formElements.latitudeInput.value = "";
    formElements.longitudeInput.value = "";
    formElements.bedroomsInput.value = "";
    formElements.bathroomsInput.value = "";
    formElements.floorAreaInput.value = "";
    applyEstimateDefaults();
    store.setState({
      selectedLocation: null,
      estimate: null,
      warningsCollapsed: true
    });
    setText(statusElement, "Waiting");
  });

  store.subscribe((state) => {
    const location = state.selectedLocation;
    const coordinates = normalizeCoordinates(location?.coordinates);
    const lat = Number(coordinates?.lat);
    const lng = Number(coordinates?.lng);
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      formElements.latitudeInput.value = String(lat);
      formElements.longitudeInput.value = String(lng);
    } else {
      formElements.latitudeInput.value = "";
      formElements.longitudeInput.value = "";
    }
    /* node:coverage ignore next */
    setText(
      locationSummary,
      location?.canonical_address
        ? `${location.canonical_address}${location.neighbourhood ? ` · ${location.neighbourhood}` : ""}`
        : "Select a property to request an estimate."
    );
    /* node:coverage ignore next */
    setText(
      selectionMeta,
      location?.canonical_address
        ? `Current selection source: ${location.canonical_location_id ? "resolved location" : "manual coordinates"}`
        : "Choose a location by search, map click, or manual coordinates."
    );
    renderEstimate(state.estimate);
  });

  renderEstimate(null);
  applyEstimateDefaults();
  [
    formElements.weightCrimeInput,
    formElements.weightSchoolsInput,
    formElements.weightGreenSpaceInput,
    formElements.weightCommuteInput
  ].forEach((input) => input.addEventListener("input", syncSliderOutputs));
}
