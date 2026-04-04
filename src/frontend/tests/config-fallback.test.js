import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async () => createMockResponse("", { status: 404 });

const config = await import("../src/config.js");

test("config falls back to defaults when app env is unavailable", () => {
  assert.equal(config.API_BASE_URL, "http://localhost:8000/api/v1");
  assert.equal(config.PREFER_LIVE_API, true);
  assert.equal(config.SEARCH_PROVIDER, "db");
  assert.ok(config.LAYER_DEFINITIONS.some((layer) => layer.id === "assessment_properties"));
});
