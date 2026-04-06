const DEFAULT_ENV = {
  API_BASE_URL: "http://localhost:8000/api/v1",
  PREFER_LIVE_API: "1",
  ALLOW_MOCK_FALLBACK: "1",
  SEARCH_PROVIDER: "db",
  ESTIMATE_API_TOKEN: "dev-local-token",
  ENABLED_LAYERS:
    "schools,parks,playgrounds,police_stations,municipal_wards,provincial_districts,federal_districts,census_subdivisions,census_boundaries,assessment_zones,assessment_properties"
};

async function loadEnvFile() {
  try {
    const response = await fetch("/app.env", { cache: "no-store" });
    if (!response.ok) {
      return {};
    }
    const text = await response.text();
    const values = {};
    text.split("\n").forEach((lineRaw) => {
      const line = lineRaw.trim();
      if (!line || line.startsWith("#") || !line.includes("=")) {
        return;
      }
      const idx = line.indexOf("=");
      const key = line.slice(0, idx).trim();
      const value = line.slice(idx + 1).trim();
      if (key) {
        values[key] = value;
      }
    });
    return values;
  } catch {
    return {};
  }
}

const RUNTIME_ENV = {
  ...DEFAULT_ENV,
  ...(await loadEnvFile())
};

function parseList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export const API_BASE_URL = RUNTIME_ENV.API_BASE_URL;
export const PREFER_LIVE_API = String(RUNTIME_ENV.PREFER_LIVE_API) !== "0";
export const ALLOW_MOCK_FALLBACK = String(RUNTIME_ENV.ALLOW_MOCK_FALLBACK) !== "0";
export const ESTIMATE_API_TOKEN = String(RUNTIME_ENV.ESTIMATE_API_TOKEN || "");
/* node:coverage ignore next */
export const SEARCH_PROVIDER = ["db", "osrm"].includes(String(RUNTIME_ENV.SEARCH_PROVIDER || "db").toLowerCase()) ? String(RUNTIME_ENV.SEARCH_PROVIDER).toLowerCase() : "db";

const ENABLED_LAYER_IDS = new Set(parseList(RUNTIME_ENV.ENABLED_LAYERS));

export const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export const EDMONTON_CENTER = [53.5461, -113.4938];
export const EDMONTON_BOUNDS = [
  [53.3385, -113.7134],
  [53.7152, -113.2784]
];

const ALL_LAYER_DEFINITIONS = [
  { id: "schools", label: "Schools", color: "#1f6feb" },
  { id: "parks", label: "Parks", color: "#2e8b57" },
  { id: "playgrounds", label: "Playgrounds", color: "#f0883e" },
  { id: "police_stations", label: "Police Stations", color: "#b91c1c" },
  { id: "municipal_wards", label: "Municipal Wards", color: "#b45309" },
  { id: "provincial_districts", label: "Provincial Districts", color: "#7c3aed" },
  { id: "federal_districts", label: "Federal Districts", color: "#0f766e" },
  { id: "census_subdivisions", label: "Census Subdivisions", color: "#475569" },
  { id: "census_boundaries", label: "Census Boundaries", color: "#a44dc5" },
  { id: "assessment_zones", label: "Assessment Zones", color: "#c46b15" },
  {
    id: "assessment_properties",
    label: "Assessment Properties",
    color: "#a43434",
    alwaysOn: true
  }
];

export const LAYER_DEFINITIONS = ALL_LAYER_DEFINITIONS.filter((layer) =>
  ENABLED_LAYER_IDS.has(layer.id)
);
export const PROPERTY_LAYER_ENABLED = ENABLED_LAYER_IDS.has("assessment_properties");

export const DEFAULT_LOCATION = {
  canonical_location_id: null,
  canonical_address: "Edmonton, AB",
  coordinates: { lat: 53.5461, lng: -113.4938 },
  region: "Edmonton",
  neighbourhood: null,
  coverage_status: "supported"
};
