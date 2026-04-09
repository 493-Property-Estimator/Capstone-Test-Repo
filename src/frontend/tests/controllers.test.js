import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse, wait } from "./helpers/fakeDom.js";

function location(overrides = {}) {
  return {
    canonical_location_id: "loc-1",
    canonical_address: "10234 98 Street NW, Edmonton, AB",
    coordinates: { lat: 53.5461, lng: -113.4938 },
    region: "Edmonton",
    neighbourhood: "Downtown",
    coverage_status: "supported",
    ...overrides
  };
}

async function buildStore() {
  globalThis.fetch = async () => createMockResponse("");
  const { createStore } = await import("../src/state/store.js");
  return createStore();
}

test("search controller covers suggestions, resolved, ambiguous, unsupported, and error flows", async () => {
  const { document } = installDomGlobals();
  const { createSearchController } = await import("../src/features/search/searchController.js");

  const input = document.createElement("input");
  const submitButton = document.createElement("button");
  const suggestionsRoot = document.createElement("div");
  const candidateResultsRoot = document.createElement("div");
  const helperText = document.createElement("div");
  const statusElement = document.createElement("div");
  const resolved = [];

  const apiClient = {
    async getAddressSuggestions(query) {
      if (query === "plain") {
        return {
          suggestions: [
            {
              display_text: "870 ABBOTTSFIELD ROAD NW, Edmonton, AB",
              secondary_text: "",
              confidence: ""
            }
          ]
        };
      }
      if (query === "boom") {
        throw new Error("down");
      }
      return {
        suggestions: [
          {
            display_text: "10234 98 Street NW, Edmonton, AB",
            secondary_text: "Edmonton",
            confidence: "high"
          }
        ]
      };
    },
    async resolveAddress(query) {
      if (query === "123 Main") {
        return {
          status: "ambiguous",
          candidates: [
            {
              candidate_id: "cand_loc-1",
              display_text: "123 Main St NW, Edmonton, AB",
              coordinates: { lat: 53.5, lng: -113.4 },
              coverage_status: "supported"
            },
            {
              candidate_id: "cand-2",
              canonical_location_id: "loc-2",
              display_text: "123 Main St SW, Calgary, AB",
              coordinates: { lat: 51.0, lng: -114.0 },
              coverage_status: "unsupported"
            }
          ]
        };
      }
      if (query === "Calgary") {
        return { status: "unsupported_region" };
      }
      if (query === "not found") {
        return { status: "not_found" };
      }
      if (query === "explode") {
        throw new Error("Search unavailable");
      }
      return {
        status: "resolved",
        location: location()
      };
    }
  };

  const controller = createSearchController({
    apiClient,
    input,
    submitButton,
    suggestionsRoot,
    candidateResultsRoot,
    helperText,
    statusElement,
    onLocationResolved(value) {
      resolved.push(value);
    }
  });

  await controller.resolveQuery("ab");
  assert.equal(helperText.textContent, "Enter more details.");
  assert.equal(statusElement.textContent, "Waiting");

  input.dispatchEvent({ type: "input", target: { value: "10234" } });
  await wait(320);
  assert.equal(suggestionsRoot.children.length, 1);
  assert.equal(helperText.textContent, "Suggestions");

  input.dispatchEvent({ type: "input", target: { value: "plain" } });
  await wait(320);
  assert.equal(suggestionsRoot.children[0].children[1].textContent, "");

  const firstSuggestion = suggestionsRoot.children[0];
  input.dispatchEvent({ type: "input", target: { value: "ab" } });
  await wait(320);
  assert.equal(suggestionsRoot.children.length, 0);

  input.dispatchEvent({ type: "input", target: { value: "10234" } });
  await wait(320);
  const clickableSuggestion = suggestionsRoot.children[0] || firstSuggestion;
  clickableSuggestion.click();
  await wait(0);
  assert.equal(statusElement.textContent, "Resolved");
  assert.equal(resolved.length, 1);

  await controller.resolveQuery("123 Main");
  assert.equal(statusElement.textContent, "Ambiguous");
  assert.equal(candidateResultsRoot.children.length, 2);
  assert.match(candidateResultsRoot.children[1].textContent, /Outside supported coverage/);
  candidateResultsRoot.children[0].click();
  assert.equal(resolved.length, 2);
  assert.equal(resolved[1].canonical_location_id, "loc-1");

  await controller.resolveQuery("Calgary");
  assert.equal(statusElement.textContent, "Unsupported");

  await controller.resolveQuery("not found");
  assert.equal(statusElement.textContent, "No match");

  await controller.resolveQuery("explode");
  assert.equal(statusElement.textContent, "Unavailable");

  input.dispatchEvent({ type: "input", target: { value: "boom" } });
  await wait(320);
  assert.equal(helperText.textContent, "Suggestion service unavailable.");

  input.value = "10234 98 Street NW";
  input.dispatchEvent({ type: "keydown", key: "Enter", target: input });
  await wait(0);
  assert.equal(resolved.length, 3);

  controller.setQuery("870 ABBOTTSFIELD ROAD NW");
  assert.equal(input.value, "870 ABBOTTSFIELD ROAD NW");

  controller.clear();
  assert.equal(input.value, "");
  assert.equal(statusElement.textContent, "Idle");
});

test("map selection controller handles resolved, unsupported, unresolved, and error outcomes", async () => {
  installDomGlobals();
  const store = await buildStore();
  const { createMapSelectionController } = await import(
    "../src/features/mapSelection/mapSelectionController.js"
  );

  const mapMessageElement = document.createElement("div");
  const setViewCalls = [];
  const mapAdapter = {
    setView(value, options) {
      setViewCalls.push({ value, options });
    }
  };

  const apiClient = {
    async resolveMapClick(payload) {
      if (payload.coordinates.lat === 0) {
        return { status: "outside_supported_area" };
      }
      if (payload.coordinates.lat === 1) {
        return { status: "unknown" };
      }
      if (payload.coordinates.lat === 2) {
        throw new Error("failure");
      }
      return {
        status: "resolved",
        location: location({ canonical_address: "Clicked location" })
      };
    }
  };

  const handler = createMapSelectionController({
    apiClient,
    store,
    mapAdapter,
    mapMessageElement
  });

  await handler({ lat: 53.5, lng: -113.4 });
  assert.equal(store.getState().selectedLocation.canonical_address, "Clicked location");
  assert.equal(setViewCalls.length, 1);
  assert.equal(setViewCalls[0].options.preserveZoom, true);

  await handler({ lat: 0, lng: 0 });
  assert.match(mapMessageElement.textContent, /outside the supported area/i);

  await handler({ lat: 1, lng: 1 });
  assert.match(mapMessageElement.textContent, /could not be determined/i);

  await handler({ lat: 2, lng: 2 });
  assert.equal(mapMessageElement.textContent, "Map click resolution unavailable.");
});

test("warning controller renders confidence, warnings, dismiss, and restore flows", async () => {
  const { document } = installDomGlobals();
  const store = await buildStore();
  const { createWarningController } = await import("../src/features/warnings/warningController.js");

  const warningPanel = document.createElement("div");
  const warningIndicator = document.createElement("button");

  createWarningController({
    store,
    warningPanel,
    warningIndicator
  });

  store.setState({ estimate: null });
  assert.equal(warningPanel.classList.contains("is-hidden"), true);
  assert.equal(warningIndicator.classList.contains("is-hidden"), true);

  store.setState({
    estimate: {
      confidence: { percentage: 78, label: "medium", completeness: "partial" },
      warnings: [
        {
          title: "Partial Data",
          message: "Crime statistics unavailable.",
          severity: "warning",
          affected_factors: ["crime"],
          dismissible: true
        }
      ]
    }
  });

  assert.equal(warningPanel.children.length, 1);
  assert.equal(warningIndicator.classList.contains("is-hidden"), true);
  assert.equal(warningPanel.classList.contains("is-hidden"), false);
  const warningDetails = warningPanel.children[0];
  assert.equal(warningDetails.tagName, "DETAILS");
  assert.equal(warningDetails.open, false);

  warningDetails.open = true;
  warningDetails.dispatchEvent({ type: "toggle" });
  assert.equal(store.getState().warningsCollapsed, false);

  const dismissButton = warningDetails.children[1].children[1].children[3].children[0];
  dismissButton.click();
  assert.equal(store.getState().warningsCollapsed, true);

  warningIndicator.click();
  assert.equal(store.getState().warningsCollapsed, false);

  store.setState({
    estimate: {
      confidence: { percentage: null, label: "", completeness: "" },
      warnings: [
        {
          title: "Informational",
          message: "No extra details.",
          severity: "info",
          affected_factors: [],
          dismissible: false
        }
      ]
    }
  });

  assert.equal(warningPanel.children.length, 1);
  assert.equal(warningPanel.children[0].children[1].children.length, 2);
});

test("warning controller handles empty payloads and no-op toggle/indicator branches", async () => {
  const { document } = installDomGlobals();
  const store = await buildStore();
  const { createWarningController } = await import("../src/features/warnings/warningController.js");

  const warningPanel = document.createElement("div");
  const warningIndicator = document.createElement("button");

  createWarningController({
    store,
    warningPanel,
    warningIndicator
  });

  store.setState({ estimate: { warnings: [] } });
  assert.equal(warningPanel.classList.contains("is-hidden"), true);

  store.setState({ estimate: { warnings: "not-an-array" } });
  assert.equal(warningPanel.classList.contains("is-hidden"), true);

  store.setState({
    warningsCollapsed: false,
    estimate: {
      confidence: {},
      warnings: [{ severity: "", affected_factors: "crime", dismissible: false }]
    }
  });

  assert.equal(warningPanel.children.length, 1);
  const warningDetails = warningPanel.children[0];
  assert.equal(warningDetails.open, true);

  warningDetails.dispatchEvent({ type: "toggle" });
  assert.equal(store.getState().warningsCollapsed, false);

  warningIndicator.click();
  assert.equal(store.getState().warningsCollapsed, false);

  const warningCard = warningDetails.children[1].children[1];
  assert.match(warningDetails.children[0].textContent, /unknown, --/);
  assert.equal(warningCard.children[0].textContent, "Warning");
  assert.equal(warningCard.children[1].textContent, "");
  assert.equal(warningCard.children[2].textContent, "");
  assert.equal(warningCard.children[3].children.length, 0);

  store.setState({
    warningsCollapsed: true,
    estimate: {
      warnings: [{ title: "No confidence payload", message: "", affected_factors: [], dismissible: false }]
    }
  });
  assert.match(warningPanel.textContent, /unknown, --/);
});

test("warning controller tolerates a missing warning indicator element", async () => {
  const { document } = installDomGlobals();
  const store = await buildStore();
  const { createWarningController } = await import("../src/features/warnings/warningController.js");

  const warningPanel = document.createElement("div");

  createWarningController({
    store,
    warningPanel,
    warningIndicator: null
  });

  store.setState({
    estimate: {
      confidence: { percentage: 44, label: "low" },
      warnings: [{ title: "Heads up", message: "Missing indicator", dismissible: false }]
    }
  });

  assert.equal(warningPanel.children.length, 1);
});

test("estimate controller validates inputs, renders estimates, and resets state", async () => {
  const { document } = installDomGlobals();
  const store = await buildStore();
  const { createEstimateController } = await import("../src/features/estimate/estimateController.js");

  const submitButton = document.createElement("button");
  const resetButton = document.createElement("button");
  const statusElement = document.createElement("div");
  const locationSummary = document.createElement("div");
  const selectionMeta = document.createElement("div");
  const estimatePanel = document.createElement("div");
  const validationMessage = document.createElement("div");
  validationMessage.classList.add("is-hidden");
  const formElements = {
    latitudeInput: document.createElement("input"),
    longitudeInput: document.createElement("input"),
    bedroomsInput: document.createElement("input"),
    bathroomsInput: document.createElement("input"),
    floorAreaInput: document.createElement("input"),
    includeBreakdownInput: document.createElement("input"),
    includeTopFactorsInput: document.createElement("input"),
    includeWarningsInput: document.createElement("input"),
    includeLayersContextInput: document.createElement("input"),
    factorCrimeInput: document.createElement("input"),
    factorSchoolsInput: document.createElement("input"),
    factorGreenSpaceInput: document.createElement("input"),
    factorCommuteInput: document.createElement("input"),
    weightCrimeInput: document.createElement("input"),
    weightSchoolsInput: document.createElement("input"),
    weightGreenSpaceInput: document.createElement("input"),
    weightCommuteInput: document.createElement("input"),
    weightCrimeOutput: document.createElement("strong"),
    weightSchoolsOutput: document.createElement("strong"),
    weightGreenSpaceOutput: document.createElement("strong"),
    weightCommuteOutput: document.createElement("strong")
  };
  [
    formElements.includeBreakdownInput,
    formElements.includeTopFactorsInput,
    formElements.includeWarningsInput,
    formElements.includeLayersContextInput,
    formElements.factorCrimeInput,
    formElements.factorSchoolsInput,
    formElements.factorGreenSpaceInput,
    formElements.factorCommuteInput
  ].forEach((input) => {
    input.type = "checkbox";
  });
  [
    formElements.weightCrimeInput,
    formElements.weightSchoolsInput,
    formElements.weightGreenSpaceInput,
    formElements.weightCommuteInput
  ].forEach((input) => {
    input.type = "range";
  });

  const estimateResponse = {
    status: "partial",
    final_estimate: 450000,
    baseline_value: 410000,
    range: { low: 432000, high: 470000 },
    factor_breakdown: [
      { label: "Schools", value: 5000, status: "available", summary: "Nearby schools." }
    ],
    warnings: [],
    confidence: { percentage: 80, completeness: "partial", label: "medium" }
  };

  const apiPayloads = [];
  const apiClient = {
    async getEstimate(payload) {
      apiPayloads.push(payload);
      if (payload.location.coordinates.lat === 0) {
        throw new Error("Coordinates must be within the supported Edmonton area.");
      }
      return estimateResponse;
    }
  };

  createEstimateController({
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
  });

  submitButton.click();
  assert.match(validationMessage.textContent, /provide an address/i);
  assert.equal(statusElement.textContent, "Error");

  store.setState({ selectedLocation: location() });
  assert.match(locationSummary.textContent, /10234 98 Street/);
  assert.match(selectionMeta.textContent, /resolved location/);
  assert.equal(formElements.latitudeInput.value, "53.5461");

  formElements.bedroomsInput.value = "3";
  formElements.bathroomsInput.value = "2";
  formElements.floorAreaInput.value = "1500";
  submitButton.click();
  await wait(0);

  assert.equal(statusElement.textContent, "Partial");
  assert.equal(apiPayloads.length, 1);
  assert.equal(apiPayloads[0].property_details.floor_area_sqft, 1500);
  assert.equal(apiPayloads[0].options.include_top_factors, true);
  assert.deepEqual(apiPayloads[0].options.desired_factor_outputs, [
    "crime_statistics",
    "school_access",
    "green_space",
    "commute_access"
  ]);
  assert.equal(apiPayloads[0].options.weights.school_access, 50);
  assert.match(estimatePanel.textContent, /Top Factors/);
  assert.match(estimatePanel.textContent, /Top Positive \/ Negative Factors/);
  const topFactorsSection = estimatePanel.children.find(
    (child) => child.tagName === "DETAILS" && /Top Factors/.test(child.textContent)
  );
  assert.ok(topFactorsSection);
  assert.equal(topFactorsSection.open, false);

  formElements.latitudeInput.value = "0";
  formElements.longitudeInput.value = "0";
  submitButton.click();
  await wait(0);
  assert.equal(statusElement.textContent, "Error");
  assert.match(validationMessage.textContent, /supported Edmonton area/i);

  store.setState({
    selectedLocation: {
      canonical_location_id: null,
      canonical_address: "Manual Coordinates",
      coordinates: { lat: 53.55, lng: -113.5 },
      neighbourhood: null
    }
  });
  assert.match(selectionMeta.textContent, /manual coordinates/);

  formElements.latitudeInput.value = "53.55";
  formElements.longitudeInput.value = "-113.5";
  formElements.bedroomsInput.value = "";
  formElements.bathroomsInput.value = "";
  formElements.floorAreaInput.value = "";
  apiClient.getEstimate = async (payload) => {
    apiPayloads.push(payload);
    return {
      status: "ready",
      final_estimate: 500000,
      baseline_value: 480000,
      range: { low: 470000, high: 520000 },
      factor_breakdown: [],
      warnings: [],
      confidence: null
    };
  };
  submitButton.click();
  await wait(0);
  assert.equal(statusElement.textContent, "Ready");
  assert.match(estimatePanel.textContent, /No factor breakdown returned/);

  store.setState({
    selectedLocation: {
      canonical_location_id: "loc-string-coords",
      canonical_address: "String Coordinates Property",
      coordinates: "{\"lat\":53.45193997726757,\"lng\":-113.59785527397807}",
      neighbourhood: "Haddow"
    }
  });
  assert.equal(formElements.latitudeInput.value, "53.45193997726757");
  assert.equal(formElements.longitudeInput.value, "-113.59785527397807");

  submitButton.click();
  await wait(0);
  assert.equal(apiPayloads.at(-1).location.coordinates.lat, 53.45193997726757);
  assert.equal(apiPayloads.at(-1).location.coordinates.lng, -113.59785527397807);

  resetButton.click();
  assert.equal(formElements.latitudeInput.value, "");
  assert.equal(formElements.factorCrimeInput.checked, true);
  assert.equal(formElements.weightCrimeOutput.textContent, "50");
  assert.equal(store.getState().estimate, null);
  assert.equal(statusElement.textContent, "Waiting");
});
