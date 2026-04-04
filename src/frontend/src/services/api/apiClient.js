import { API_BASE_URL, PREFER_LIVE_API, SEARCH_PROVIDER } from "../../config.js";
import { mockApi } from "./mockData.js";

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body !== undefined && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers,
      ...options
    });
  } catch (error) {
    /* node:coverage ignore next */
    throw Object.assign(new Error("Unable to reach live API"), { cause: error, isNetworkError: true });
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.error?.message || "Request failed";
    const requestError = new Error(message);
    requestError.status = response.status;
    requestError.response = data;
    throw requestError;
  }

  return data;
}

function createAbortError() {
  return new DOMException("The operation was aborted.", "AbortError");
}

function withMockDelay(factory, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(createAbortError());
      return;
    }

    const timeoutId = window.setTimeout(() => {
      Promise.resolve()
        .then(factory)
        .then(resolve)
        .catch(reject);
    }, 180);

    signal?.addEventListener(
      "abort",
      /* node:coverage ignore next */
      () => { window.clearTimeout(timeoutId); reject(createAbortError()); },
      { once: true }
    );
  });
}

function shouldFallbackToMock(error) {
  /* node:coverage ignore next */
  if (error?.name === "AbortError") return false;

  /* node:coverage ignore next */
  if (!PREFER_LIVE_API) return true;

  return Boolean(
    error?.isNetworkError
      || (typeof error?.status === "number" && (
        error.status >= 500
        || error.status === 404
        || error.status === 424
      ))
  );
}

async function requestWithFallback(
  liveFactory,
  mockFactory,
  { signal, fallbackOnAnyError = false } = {}
) {
  if (!PREFER_LIVE_API) {
    return withMockDelay(mockFactory, signal);
  }

  try {
    return await liveFactory();
  } catch (error) {
    if (fallbackOnAnyError && error?.name !== "AbortError") {
      return withMockDelay(mockFactory, signal);
    }

    if (!shouldFallbackToMock(error)) {
      throw error;
    }

    return withMockDelay(mockFactory, signal);
  }
}

export const apiClient = {
  getAddressSuggestions(query, limit = 5) {
    const params = new URLSearchParams({
      q: query,
      limit: String(limit),
      provider: SEARCH_PROVIDER
    });
    return requestWithFallback(
      () => request(`/search/suggestions?${params.toString()}`),
      () => mockApi.getAddressSuggestions(query, limit)
    );
  },

  resolveAddress(query) {
    const params = new URLSearchParams({
      q: query,
      provider: SEARCH_PROVIDER
    });
    return requestWithFallback(
      () => request(`/search/resolve?${params.toString()}`),
      () => mockApi.resolveAddress(query)
    );
  },

  resolveMapClick(payload) {
    return requestWithFallback(
      () => request("/locations/resolve-click", {
        method: "POST",
        body: JSON.stringify(payload)
      }),
      () => mockApi.resolveMapClick(payload)
    );
  },

  getEstimate(payload) {
    return requestWithFallback(
      () => request("/estimates", {
        method: "POST",
        body: JSON.stringify(payload)
      }),
      () => mockApi.getEstimate(payload)
    );
  },

  getLayerData({ layerId, west, south, east, north, zoom }) {
    const params = new URLSearchParams({
      west: String(west),
      south: String(south),
      east: String(east),
      north: String(north),
      zoom: String(zoom)
    });
    return requestWithFallback(
      () => request(`/layers/${layerId}?${params.toString()}`),
      () => mockApi.getLayerData({ layerId, west, south, east, north, zoom }),
      { fallbackOnAnyError: true }
    );
  },

  getProperties({ west, south, east, north, zoom, limit = 5000, cursor = null, signal } = {}) {
    const params = new URLSearchParams({
      west: String(west),
      south: String(south),
      east: String(east),
      north: String(north),
      zoom: String(zoom),
      limit: String(limit)
    });

    if (cursor) {
      params.set("cursor", String(cursor));
    }

    return requestWithFallback(
      () => request(`/properties?${params.toString()}`, { signal }),
      () => mockApi.getProperties({ west, south, east, north, zoom, limit, cursor, signal }),
      { signal, fallbackOnAnyError: true }
    );
  }
};
