import { API_BASE_URL, USE_MOCK_API } from "../../config.js";
import { mockApi } from "./mockData.js";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.error?.message || "Request failed";
    throw new Error(message);
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
      () => {
        window.clearTimeout(timeoutId);
        reject(createAbortError());
      },
      { once: true }
    );
  });
}

export const apiClient = {
  getAddressSuggestions(query, limit = 5) {
    if (USE_MOCK_API) {
      return withMockDelay(() => mockApi.getAddressSuggestions(query, limit));
    }
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    return request(`/search/suggestions?${params.toString()}`);
  },

  resolveAddress(query) {
    if (USE_MOCK_API) {
      return withMockDelay(() => mockApi.resolveAddress(query));
    }
    const params = new URLSearchParams({ q: query });
    return request(`/search/resolve?${params.toString()}`);
  },

  resolveMapClick(payload) {
    if (USE_MOCK_API) {
      return withMockDelay(() => mockApi.resolveMapClick(payload));
    }
    return request("/locations/resolve-click", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  getEstimate(payload) {
    if (USE_MOCK_API) {
      return withMockDelay(() => mockApi.getEstimate(payload));
    }
    return request("/estimates", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  getLayerData({ layerId, west, south, east, north, zoom }) {
    if (USE_MOCK_API) {
      return withMockDelay(() =>
        mockApi.getLayerData({ layerId, west, south, east, north, zoom })
      );
    }
    const params = new URLSearchParams({
      west: String(west),
      south: String(south),
      east: String(east),
      north: String(north),
      zoom: String(zoom)
    });
    return request(`/layers/${layerId}?${params.toString()}`);
  },

  getProperties({ west, south, east, north, zoom, limit = 5000, cursor = null, signal } = {}) {
    if (USE_MOCK_API) {
      return withMockDelay(() =>
        mockApi.getProperties({ west, south, east, north, zoom, limit, cursor, signal }),
      signal);
    }

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

    return request(`/properties?${params.toString()}`, { signal });
  }
};
