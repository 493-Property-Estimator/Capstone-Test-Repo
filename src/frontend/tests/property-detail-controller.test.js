import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

test("property detail controller renders empty and populated states and supports closing", async () => {
  installDomGlobals({
    ids: [
      { id: "property-detail-panel" },
      { id: "property-detail-title" },
      { id: "property-detail-subtitle" },
      { id: "property-detail-body" },
      { id: "property-detail-close", tagName: "button" }
    ]
  });
  globalThis.fetch = async () => createMockResponse("");

  const { createStore } = await import("../src/state/store.js");
  const { createPropertyDetailController } = await import(
    "../src/features/propertyDetails/propertyDetailController.js"
  );

  const store = createStore();
  const panel = document.getElementById("property-detail-panel");
  const title = document.getElementById("property-detail-title");
  const subtitle = document.getElementById("property-detail-subtitle");
  const body = document.getElementById("property-detail-body");
  const close = document.getElementById("property-detail-close");

  createPropertyDetailController({
    store,
    panel,
    titleElement: title,
    subtitleElement: subtitle,
    bodyElement: body,
    closeButton: close
  });

  assert.equal(panel.classList.contains("is-hidden"), true);
  assert.match(title.textContent, /No property selected/);
  assert.match(body.textContent, /Property details will appear here/);

  store.setState({
    selectedPropertyDetails: {
      name: "123 TEST AVENUE NW",
      canonical_address: "123 TEST AVENUE NW, Edmonton, AB",
      details: {
        assessment_value: 450000,
        neighbourhood: "Downtown",
        ward: "O-day'min",
        tax_class: "Residential",
        bedrooms: 3,
        bathrooms_estimated: 2.5,
        total_gross_area: 1450,
        year_built: 1998,
        lot_size: 3900,
        zoning: "RF3",
        suite: "",
        garage: "Detached",
        assessment_year: 2025,
        assessment_class_1: "Residential",
        assessment_class_2: "",
        assessment_class_3: null,
        assessment_class_pct_1: 1,
        assessment_class_pct_2: 75,
        assessment_class_pct_3: 0.125,
        legal_description: "Lot 1 Block 2 Plan 3",
        attribute_source_type: "observed",
        attribute_source_name: "listing",
        attribute_confidence: 0.96,
        location_confidence: 0.5,
        link_method: "direct"
      }
    }
  });

  assert.equal(panel.classList.contains("is-hidden"), false);
  assert.match(title.textContent, /123 TEST AVENUE/);
  assert.match(subtitle.textContent, /Downtown/);
  assert.match(body.textContent, /\$450,000/);
  assert.match(body.textContent, /3 bedrooms/);
  assert.match(body.textContent, /2.5 bathrooms/);
  assert.match(body.textContent, /1,450 sq ft/);
  assert.match(body.textContent, /100%/);
  assert.match(body.textContent, /75%/);
  assert.match(body.textContent, /12.5%/);
  assert.match(body.textContent, /96%/);
  assert.match(body.textContent, /50%/);

  store.setState({
    selectedPropertyDetails: {
      canonical_address: "Fallback property",
      details: {
        assessment_value: null,
        neighbourhood: "",
        ward: null,
        tax_class: undefined,
        bedrooms_estimated: "Studio",
        bathrooms_estimated: "",
        total_gross_area: "unknown",
        year_built: "ancient",
        lot_size: "small",
        zoning: "",
        suite: "",
        garage: "",
        assessment_year: "",
        assessment_class_1: "",
        assessment_class_2: "",
        assessment_class_3: "",
        assessment_class_pct_1: "N/A",
        assessment_class_pct_2: null,
        assessment_class_pct_3: "",
        legal_description: "",
        attribute_source_type: "",
        attribute_source_name: "",
        attribute_confidence: "high",
        location_confidence: null,
        link_method: ""
      }
    }
  });

  assert.match(body.textContent, /--/);

  store.setState({
    selectedPropertyDetails: {
      canonical_address: "String fallback property",
      details: {
        assessment_value: "TBD",
        bedrooms_estimated: "Studio",
        bathrooms_estimated: "",
        total_gross_area: "unknown",
        year_built: "ancient",
        lot_size: "small",
        assessment_class_pct_1: "N/A",
        attribute_confidence: "high"
      }
    }
  });

  assert.match(body.textContent, /TBD/);
  assert.match(body.textContent, /Studio/);
  assert.match(body.textContent, /unknown sq ft/);
  assert.match(body.textContent, /ancient/);
  assert.match(body.textContent, /small/);
  assert.match(body.textContent, /N\/A/);
  assert.match(body.textContent, /high/);
  assert.match(body.textContent, /--/);

  store.setState({
    selectedPropertyDetails: {
      details: null
    }
  });

  assert.match(title.textContent, /Selected property/);
  assert.match(subtitle.textContent, /Edmonton property/);

  close.click();
  assert.equal(store.getState().propertyDetailsDismissed, true);
  assert.equal(store.getState().selectedPropertyDetails, null);
});
