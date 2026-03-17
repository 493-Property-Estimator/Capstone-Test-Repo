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
  statusElement,
  locationSummary,
  estimatePanel
}) {
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

    const factorsHeading = createElement("h3", null, "Top Factors");
    estimatePanel.appendChild(factorsHeading);

    if (!estimate.factor_breakdown?.length) {
      estimatePanel.appendChild(
        createElement("p", "empty-state", "No factor breakdown returned.")
      );
      return;
    }

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
      estimatePanel.appendChild(item);
    });
  }

  async function requestEstimate() {
    const state = store.getState();
    setText(statusElement, "Loading");

    try {
      const response = await apiClient.getEstimate({
        location: {
          canonical_location_id: state.selectedLocation?.canonical_location_id,
          coordinates: state.selectedLocation?.coordinates,
          address: state.selectedLocation?.canonical_address
        },
        property_details: {},
        options: {
          include_breakdown: true,
          include_warnings: true,
          include_layers_context: false
        }
      });

      store.setState({ estimate: response, warningsCollapsed: false });
      setText(statusElement, response.status === "partial" ? "Partial" : "Ready");
    } catch (error) {
      setText(statusElement, "Error");
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

  store.subscribe((state) => {
    const location = state.selectedLocation;
    setText(
      locationSummary,
      location?.canonical_address
        ? `${location.canonical_address}${location.neighbourhood ? ` · ${location.neighbourhood}` : ""}`
        : "Select a property to request an estimate."
    );
    renderEstimate(state.estimate);
  });

  renderEstimate(null);
}
