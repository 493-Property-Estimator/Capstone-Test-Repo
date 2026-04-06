/* node:coverage disable */
import { clearElement, createElement, setText } from "../../utils/dom.js";

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

  function buildPayload() {
    const state = store.getState();
    const latitude = normalizeNumber(formElements.latitudeInput.value);
    const longitude = normalizeNumber(formElements.longitudeInput.value);
    const bedrooms = normalizeNumber(formElements.bedroomsInput.value);
    const bathrooms = normalizeNumber(formElements.bathroomsInput.value);
    const floorArea = normalizeNumber(formElements.floorAreaInput.value);

    const coordinates =
      latitude !== undefined && longitude !== undefined
        ? { lat: latitude, lng: longitude }
        : state.selectedLocation?.coordinates;

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
        include_breakdown: true,
        include_warnings: true,
        include_layers_context: true
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
  }
  /* node:coverage enable */

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
    store.setState({
      selectedLocation: null,
      estimate: null,
      warningsCollapsed: true
    });
    setText(statusElement, "Waiting");
  });

  store.subscribe((state) => {
    const location = state.selectedLocation;
    const lat = Number(location?.coordinates?.lat);
    const lng = Number(location?.coordinates?.lng);
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
}
