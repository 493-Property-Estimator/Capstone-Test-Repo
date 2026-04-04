import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async () => {
  throw new Error("network down");
};

const config = await import("../src/config.js");

test("config falls back to defaults when app env fetch throws", () => {
  assert.equal(config.API_BASE_URL, "http://localhost:8000/api/v1");
  assert.equal(config.SEARCH_PROVIDER, "db");
});
