import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async (url) => {
  if (String(url).endsWith("/app.env")) {
    return createMockResponse("PREFER_LIVE_API=1\nALLOW_MOCK_FALLBACK=1\n");
  }
  return createMockResponse({});
};

const { __apiInternals } = await import("../src/services/api/apiClient.js");

test("api fallback helper covers non-status and retryable status branches", () => {
  assert.equal(__apiInternals.shouldFallbackToMock({}), false);
  assert.equal(__apiInternals.shouldFallbackToMock({ status: 404 }), true);
  assert.equal(__apiInternals.shouldFallbackToMock({ status: 424 }), true);
  assert.equal(__apiInternals.shouldFallbackToMock({ status: 400 }), false);
});
