import { clearElement, createElement, setText, toggleHidden } from "../../utils/dom.js";

function formatValue(value, fallback = "--") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function formatNumber(value, fallback = "--") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  return new Intl.NumberFormat("en-CA", {
    maximumFractionDigits: 2
  }).format(numeric);
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0
  }).format(numeric);
}

function formatCount(value, unitLabel) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  const formatted = new Intl.NumberFormat("en-CA", {
    maximumFractionDigits: numeric % 1 === 0 ? 0 : 1
  }).format(numeric);
  return `${formatted} ${unitLabel}`;
}

function formatArea(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return `${formatNumber(value)} sq ft`;
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  const normalized = numeric <= 1 ? numeric * 100 : numeric;
  return `${new Intl.NumberFormat("en-CA", {
    maximumFractionDigits: 1
  }).format(normalized)}%`;
}

export function createPropertyDetailController({
  store,
  panel,
  titleElement,
  subtitleElement,
  bodyElement,
  closeButton
}) {
  function metric(label, value) {
    const item = createElement("div", "detail-metric");
    item.appendChild(createElement("span", "detail-metric-label", label));
    item.appendChild(createElement("strong", "detail-metric-value", value));
    return item;
  }

  function section(title, items) {
    const wrapper = createElement("section", "detail-section");
    wrapper.appendChild(createElement("h4", null, title));
    const grid = createElement("div", "detail-grid");
    items.forEach((item) => grid.appendChild(item));
    wrapper.appendChild(grid);
    return wrapper;
  }

  function render(detailsState) {
    clearElement(bodyElement);

    if (!detailsState) {
      setText(titleElement, "No property selected");
      setText(subtitleElement, "Click an individual property point to inspect the full record.");
      bodyElement.appendChild(createElement("p", "empty-state", "Property details will appear here."));
      toggleHidden(panel, true);
      return;
    }

    const details = detailsState.details || {};

    setText(titleElement, detailsState.name || detailsState.canonical_address || "Selected property");
    setText(
      subtitleElement,
      `${detailsState.canonical_address || "Edmonton property"}${details.neighbourhood ? ` · ${details.neighbourhood}` : ""}`
    );

    bodyElement.appendChild(
      section("Overview", [
        metric("Assessment", formatCurrency(details.assessment_value)),
        metric("Neighbourhood", formatValue(details.neighbourhood)),
        metric("Ward", formatValue(details.ward)),
        metric("Tax Class", formatValue(details.tax_class))
      ])
    );

    bodyElement.appendChild(
      section("Property", [
        metric("Bedrooms", formatCount(details.bedrooms ?? details.bedrooms_estimated, "bedrooms")),
        metric("Bathrooms", formatCount(details.bathrooms ?? details.bathrooms_estimated, "bathrooms")),
        metric("Area", formatArea(details.total_gross_area)),
        metric("Year Built", formatNumber(details.year_built)),
        metric("Lot Size", formatNumber(details.lot_size)),
        metric("Zoning", formatValue(details.zoning)),
        metric("Suite", formatValue(details.suite)),
        metric("Garage", formatValue(details.garage))
      ])
    );

    bodyElement.appendChild(
      section("Assessment Metadata", [
        metric("Assessment Year", formatValue(details.assessment_year)),
        metric("Class 1", formatValue(details.assessment_class_1)),
        metric("Class 2", formatValue(details.assessment_class_2)),
        metric("Class 3", formatValue(details.assessment_class_3)),
        metric("Class 1 Share", formatPercent(details.assessment_class_pct_1)),
        metric("Class 2 Share", formatPercent(details.assessment_class_pct_2)),
        metric("Class 3 Share", formatPercent(details.assessment_class_pct_3)),
        metric("Legal Description", formatValue(details.legal_description))
      ])
    );

    bodyElement.appendChild(
      section("Data Provenance", [
        metric("Bedrooms/Baths Source", formatValue(details.attribute_source_type)),
        metric("Attribute Source Name", formatValue(details.attribute_source_name)),
        metric("Attribute Confidence", formatPercent(details.attribute_confidence)),
        metric("Location Confidence", formatPercent(details.location_confidence)),
        metric("Link Method", formatValue(details.link_method))
      ])
    );

    toggleHidden(panel, false);
  }

  closeButton.addEventListener("click", () => {
    store.setState({
      selectedPropertyDetails: null,
      propertyDetailsDismissed: true
    });
  });

  store.subscribe((state) => {
    render(state.selectedPropertyDetails);
  });

  render(null);
}
