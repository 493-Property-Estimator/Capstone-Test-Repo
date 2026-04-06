import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async () =>
  createMockResponse(
    "\n# comment\n=ignored\nAPI_BASE_URL=http://localhost:8100/api\nALLOW_MOCK_FALLBACK=0\nENABLED_LAYERS=schools\nBROKEN\n"
  );

const config = await import("../src/config.js");

test("config ignores blank env keys while parsing valid entries", () => {
  assert.equal(config.API_BASE_URL, "http://localhost:8100/api");
  assert.equal(config.ALLOW_MOCK_FALLBACK, false);
  assert.deepEqual(config.LAYER_DEFINITIONS.map((layer) => layer.id), ["schools"]);
  assert.equal(config.PROPERTY_LAYER_ENABLED, false);
  assert.deepEqual(config.__configInternals.parseList(undefined), []);
  assert.deepEqual(config.__configInternals.parseList(null), []);
  assert.deepEqual(config.__configInternals.parseList(" one, two ,,three "), ["one", "two", "three"]);
  assert.equal(config.__configInternals.normalizeSearchProvider("OSRM"), "osrm");
  assert.equal(config.__configInternals.normalizeSearchProvider("weird"), "db");
  assert.equal(config.__configInternals.normalizeSearchProvider(undefined), "db");
  assert.equal(config.__configInternals.parseBooleanFlag("0", true), false);
  assert.equal(config.__configInternals.parseWeight("180", 50), 100);
});
