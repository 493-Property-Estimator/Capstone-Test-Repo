import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async () =>
  createMockResponse(
    "# comment\nSEARCH_PROVIDER=invalid\nENABLED_LAYERS=\nMALFORMED\n"
  );

const config = await import("../src/config.js");

test("config normalizes invalid provider values back to db", () => {
  assert.equal(config.SEARCH_PROVIDER, "db");
  assert.equal(config.PROPERTY_LAYER_ENABLED, false);
  assert.deepEqual(config.LAYER_DEFINITIONS, []);
});
