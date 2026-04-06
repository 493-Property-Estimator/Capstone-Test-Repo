import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
const calls = [];
globalThis.fetch = async (url, options = {}) => {
  calls.push({ url: String(url), options });
  if (String(url).endsWith("/app.env")) {
    return createMockResponse(
      "PREFER_LIVE_API=1\nALLOW_MOCK_FALLBACK=0\nESTIMATE_API_TOKEN=token-123\n"
    );
  }
  if (String(url).includes("/estimates")) {
    return createMockResponse({ ok: true }, { status: 200 });
  }
  if (String(url).includes("/layers/schools")) {
    return {
      ok: true,
      status: 200,
      async json() {
        throw new Error("invalid json");
      }
    };
  }
  if (String(url).includes("/locations/resolve-click")) {
    return createMockResponse(
      { detail: { msg: "Map click invalid." } },
      { status: 400 }
    );
  }
  return createMockResponse(null, { status: 418 });
};

const { apiClient, __apiInternals } = await import("../src/services/api/apiClient.js");

test("api client respects disabled mock fallback and sends live estimate auth headers", async () => {
  const response = await apiClient.getEstimate({
    location: { coordinates: { lat: 53.54, lng: -113.49 } }
  });

  assert.deepEqual(response, { ok: true });

  const estimateCall = calls.find((call) => call.url.includes("/estimates"));
  assert.ok(estimateCall);
  assert.equal(estimateCall.options.headers.Authorization, "Bearer token-123");
  assert.equal(estimateCall.options.headers["Content-Type"], "application/json");

  const layerData = await apiClient.getLayerData({
    layerId: "schools",
    west: -113.6,
    south: 53.5,
    east: -113.4,
    north: 53.6,
    zoom: 12
  });
  assert.equal(layerData, null);

  await assert.rejects(
    () => apiClient.resolveMapClick({ coordinates: { lat: 53.5, lng: -113.4 } }),
    /Map click invalid/
  );

  await assert.rejects(
    () => apiClient.resolveAddress("bad request"),
    /Request failed/
  );

  await assert.rejects(
    () =>
      __apiInternals.request("/locations/resolve-click", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coordinates: { lat: 1, lng: 1 } })
      }),
    /Map click invalid/
  );

  assert.equal(__apiInternals.shouldFallbackToMock({ name: "AbortError" }), false);
});
