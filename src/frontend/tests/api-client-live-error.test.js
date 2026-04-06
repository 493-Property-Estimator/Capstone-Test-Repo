import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async (url) => {
  if (String(url).endsWith("/app.env")) {
    return createMockResponse("PREFER_LIVE_API=1\n");
  }
  throw new Error("offline");
};

const { apiClient } = await import("../src/services/api/apiClient.js");

test("api client falls back from live network failures", async () => {
  const resolved = await apiClient.resolveAddress("10234 98 Street NW");
  assert.ok(resolved.status);
});
