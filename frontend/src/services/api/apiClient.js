import { API_BASE_URL } from "../../config.js";

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

export const apiClient = {
  getAddressSuggestions(query, limit = 5) {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    return request(`/search/suggestions?${params.toString()}`);
  },

  resolveAddress(query) {
    const params = new URLSearchParams({ q: query });
    return request(`/search/resolve?${params.toString()}`);
  },

  resolveMapClick(payload) {
    return request("/locations/resolve-click", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  getEstimate(payload) {
    return request("/estimates", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  getLayerData({ layerId, west, south, east, north, zoom }) {
    const params = new URLSearchParams({
      west: String(west),
      south: String(south),
      east: String(east),
      north: String(north),
      zoom: String(zoom)
    });
    return request(`/layers/${layerId}?${params.toString()}`);
  }
};
