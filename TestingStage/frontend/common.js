export const EDMONTON_CENTER = [53.5461, -113.4938];
export const API_BASE = "/api";

export function setActiveNav() {
  const currentPath = window.location.pathname.replace(/\/$/, "") || "/";
  document.querySelectorAll("[data-nav]").forEach((link) => {
    const linkPath = link.getAttribute("href").replace(/\/$/, "") || "/";
    link.classList.toggle("active", linkPath === currentPath);
  });
}

export async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload;
}

export function formatCurrency(value) {
  if (value == null) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value) {
  if (value == null) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-CA", {
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatDurationSeconds(value) {
  if (value == null) {
    return "N/A";
  }

  const totalSeconds = Math.round(Number(value));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return replacements[character] || character;
  });
}

export function setStatus(element, message) {
  element.textContent = message;
}

export function createBaseMap(elementId) {
  const map = window.L.map(elementId, {
    center: EDMONTON_CENTER,
    zoom: 11,
    minZoom: 10,
    maxZoom: 18,
    zoomControl: true,
  });

  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  return map;
}

export function makeMarker(lat, lon, color, label) {
  return window.L.circleMarker([lat, lon], {
    radius: 8,
    color,
    fillColor: color,
    fillOpacity: 0.9,
    weight: 2,
  }).bindPopup(label);
}
