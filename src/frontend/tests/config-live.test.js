import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async () =>
  createMockResponse(
    "API_BASE_URL=http://localhost:9000/api/v2\nPREFER_LIVE_API=0\nSEARCH_PROVIDER=OSRM\nESTIMATE_REQUESTED_FACTORS=crime_statistics,school_access\nESTIMATE_WEIGHT_CRIME=80\nENABLED_LAYERS=schools,assessment_properties\n"
  );

const config = await import("../src/config.js");

test("config loads runtime env values and normalizes providers", () => {
  assert.equal(config.API_BASE_URL, "http://localhost:9000/api/v2");
  assert.equal(config.PREFER_LIVE_API, false);
  assert.equal(config.SEARCH_PROVIDER, "osrm");
  assert.deepEqual(config.ESTIMATE_REQUESTED_FACTORS, ["crime_statistics", "school_access"]);
  assert.equal(config.ESTIMATE_WEIGHT_DEFAULTS.crime, 80);
  assert.equal(config.PROPERTY_LAYER_ENABLED, true);
  assert.deepEqual(
    config.LAYER_DEFINITIONS.map((layer) => layer.id),
    ["schools", "assessment_properties"]
  );
});
