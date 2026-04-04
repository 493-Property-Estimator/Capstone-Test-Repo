import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse } from "./helpers/fakeDom.js";

installDomGlobals();
globalThis.fetch = async (url) => {
  if (String(url).endsWith("/app.env")) {
    return createMockResponse("PREFER_LIVE_API=0\n");
  }
  if (String(url).includes("./mock-data/assessment-properties-tiles/index.json")) {
    return createMockResponse({ tiles: [] });
  }
  if (String(url).includes("./mock-data/assessment-properties.geojson")) {
    return createMockResponse({ type: "FeatureCollection", features: [] });
  }
  return createMockResponse({});
};

const { apiClient } = await import("../src/services/api/apiClient.js");

test("api client supports mock-mode aborts and optional cursor parameters", async () => {
  const abortedSignal = {
    aborted: true,
    addEventListener() {}
  };

  await assert.rejects(
    () => apiClient.getProperties({ west: -113.6, south: 53.5, east: -113.4, north: 53.6, zoom: 12, signal: abortedSignal }),
    /aborted/i
  );

  const response = await apiClient.getProperties({
    west: -113.6,
    south: 53.5,
    east: -113.4,
    north: 53.6,
    zoom: 18,
    cursor: "offset:10"
  });

  assert.ok(["cluster", "property"].includes(response.render_mode));
});
