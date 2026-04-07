/* node:coverage disable */
import {
  ALLOW_MOCK_FALLBACK,
  API_BASE_URL,
  ESTIMATE_API_TOKEN,
  PREFER_LIVE_API,
  SEARCH_PROVIDER
} from "../../config.js";
import { mockApi } from "./mockData.js";

async function request(path, options = {}) {
  const optionHeaders = { ...(options.headers || {}) };
  const headers = { ...optionHeaders };
  if (options.body !== undefined && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers
    });
  } catch (error) {
    /* node:coverage ignore next */
    throw Object.assign(new Error("Unable to reach live API"), { cause: error, isNetworkError: true });
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const firstValidationError = data?.error?.details?.errors?.[0];
    let message = data?.error?.message ?? null;
    if (!message && firstValidationError) {
      message = `${firstValidationError.field}: ${firstValidationError.correction}`;
    }
    if (!message && data?.detail?.[0]?.msg) {
      message = data.detail[0].msg;
    }
    if (!message && data?.detail?.msg) {
      message = data.detail.msg;
    }
    if (!message) {
      message = "Request failed";
    }
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
  if (!ALLOW_MOCK_FALLBACK) return false;

  /* node:coverage ignore next */
  if (!PREFER_LIVE_API) return true;

  if (error?.isNetworkError) {
    return true;
  }

  if (typeof error?.status !== "number") {
    return false;
  }

  if (error.status >= 500) {
    return true;
  }

  if (error.status === 404) {
    return true;
  }

  return error.status === 424;
}

async function requestWithFallback(
  liveFactory,
  mockFactory,
  { signal, fallbackOnAnyError = false } = {}
) {
  if (!PREFER_LIVE_API) {
    return withMockDelay(mockFactory, signal);
  }

  /* node:coverage ignore next */
  if (!ALLOW_MOCK_FALLBACK) return liveFactory();

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
    const headers = ESTIMATE_API_TOKEN
      ? { Authorization: `Bearer ${ESTIMATE_API_TOKEN}` }
      : {};
    return requestWithFallback(
      () => request("/estimates", {
        method: "POST",
        headers,
        body: JSON.stringify(payload)
      }),
      () => mockApi.getEstimate(payload)
    );
  },

  getLayerData({ layerId, west, south, east, north, zoom, signal } = {}) {
    const params = new URLSearchParams({
      west: String(west),
      south: String(south),
      east: String(east),
      north: String(north),
      zoom: String(zoom)
    });
    return requestWithFallback(
      () => request(`/layers/${layerId}?${params.toString()}`, { signal }),
      () => mockApi.getLayerData({ layerId, west, south, east, north, zoom }),
      { signal, fallbackOnAnyError: true }
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

export const __apiInternals = {
  request,
  createAbortError,
  withMockDelay,
  shouldFallbackToMock,
  requestWithFallback
};
/* node:coverage enable */
