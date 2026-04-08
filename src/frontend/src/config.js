/* node:coverage disable */
const DEFAULT_ENV = {
  API_BASE_URL: "http://localhost:8000/api/v1",
  PREFER_LIVE_API: "1",
  ALLOW_MOCK_FALLBACK: "1",
  SEARCH_PROVIDER: "db",
  ESTIMATE_API_TOKEN: "dev-local-token",
  SEARCH_QUERY_MIN_CHARS: "3",
  SEARCH_SUGGESTIONS_DEFAULT_LIMIT: "5",
  PROPERTY_CACHE_TTL_MS: "30000",
  PROPERTY_LIMIT_DEFAULT: "5000",
  PROPERTY_LIMIT_HIGH_ZOOM: "4000",
  PROPERTY_HIGH_ZOOM_THRESHOLD: "17",
  PROPERTY_PREFETCH_VIEWPORTS: "2",
  LAYERS_REFRESH_DEBOUNCE_MS: "300",
  PROPERTY_REFRESH_DEBOUNCE_MS: "180",
  SEARCH_INPUT_DEBOUNCE_MS: "300",
  ESTIMATE_REQUESTED_FACTORS: "crime_statistics,school_access,green_space,commute_access",
  ESTIMATE_INCLUDE_BREAKDOWN: "1",
  ESTIMATE_INCLUDE_TOP_FACTORS: "1",
  ESTIMATE_INCLUDE_WARNINGS: "1",
  ESTIMATE_INCLUDE_LAYERS_CONTEXT: "1",
  ESTIMATE_WEIGHT_CRIME: "50",
  ESTIMATE_WEIGHT_SCHOOLS: "50",
  ESTIMATE_WEIGHT_GREEN_SPACE: "50",
  ESTIMATE_WEIGHT_COMMUTE: "50",
  LAYER_LAB_LAYER_IDS:
    "schools,parks,playgrounds,police_stations,transit_stops,businesses,green_space,roads,municipal_wards,provincial_districts,federal_districts,census_subdivisions,census_boundaries",
  ENABLED_LAYERS:
    "schools,parks,playgrounds,police_stations,transit_stops,businesses,green_space,roads,municipal_wards,provincial_districts,federal_districts,census_subdivisions,census_boundaries,assessment_properties"
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
      if (!line) {
        return;
      }
      if (line.startsWith("#")) {
        return;
      }
      const idx = line.indexOf("=");
      if (idx < 0) {
        return;
      }
      const key = line.slice(0, idx).trim();
      const value = line.slice(idx + 1).trim();
      if (!key) {
        return;
      }
      values[key] = value;
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
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeSearchProvider(value) {
  const normalized = String(value ?? "db").toLowerCase();
  if (normalized === "db") {
    return "db";
  }
  if (normalized === "osrm") {
    return "osrm";
  }
  return "db";
}

function parseBooleanFlag(value, fallback = true) {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }
  return String(value) !== "0";
}

function parseWeight(value, fallback = 50) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(0, Math.min(100, parsed));
}

function parseNumber(value, fallback, { min = null, max = null } = {}) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  if (min !== null && parsed < min) {
    return min;
  }
  if (max !== null && parsed > max) {
    return max;
  }
  return parsed;
}

export const API_BASE_URL = RUNTIME_ENV.API_BASE_URL;
export const PREFER_LIVE_API = String(RUNTIME_ENV.PREFER_LIVE_API) !== "0";
export const ALLOW_MOCK_FALLBACK = String(RUNTIME_ENV.ALLOW_MOCK_FALLBACK) !== "0";
export const ESTIMATE_API_TOKEN = String(RUNTIME_ENV.ESTIMATE_API_TOKEN ?? "");
export const SEARCH_PROVIDER = normalizeSearchProvider(RUNTIME_ENV.SEARCH_PROVIDER);
export const SEARCH_QUERY_MIN_CHARS = parseNumber(RUNTIME_ENV.SEARCH_QUERY_MIN_CHARS, 3, { min: 1 });
export const SEARCH_SUGGESTIONS_DEFAULT_LIMIT = parseNumber(RUNTIME_ENV.SEARCH_SUGGESTIONS_DEFAULT_LIMIT, 5, { min: 1 });
export const PROPERTY_CACHE_TTL_MS = parseNumber(RUNTIME_ENV.PROPERTY_CACHE_TTL_MS, 30000, { min: 1 });
export const PROPERTY_LIMIT_DEFAULT = parseNumber(RUNTIME_ENV.PROPERTY_LIMIT_DEFAULT, 5000, { min: 1 });
export const PROPERTY_LIMIT_HIGH_ZOOM = parseNumber(RUNTIME_ENV.PROPERTY_LIMIT_HIGH_ZOOM, 4000, { min: 1 });
export const PROPERTY_HIGH_ZOOM_THRESHOLD = parseNumber(RUNTIME_ENV.PROPERTY_HIGH_ZOOM_THRESHOLD, 17, { min: 0 });
export const PROPERTY_PREFETCH_VIEWPORTS = parseNumber(RUNTIME_ENV.PROPERTY_PREFETCH_VIEWPORTS, 2, { min: 0 });
export const LAYERS_REFRESH_DEBOUNCE_MS = parseNumber(RUNTIME_ENV.LAYERS_REFRESH_DEBOUNCE_MS, 300, { min: 1 });
export const PROPERTY_REFRESH_DEBOUNCE_MS = parseNumber(RUNTIME_ENV.PROPERTY_REFRESH_DEBOUNCE_MS, 180, { min: 1 });
export const SEARCH_INPUT_DEBOUNCE_MS = parseNumber(RUNTIME_ENV.SEARCH_INPUT_DEBOUNCE_MS, 300, { min: 1 });
export const ESTIMATE_REQUESTED_FACTORS = parseList(RUNTIME_ENV.ESTIMATE_REQUESTED_FACTORS);
export const ESTIMATE_OPTIONS_DEFAULTS = {
  includeBreakdown: parseBooleanFlag(RUNTIME_ENV.ESTIMATE_INCLUDE_BREAKDOWN, true),
  includeTopFactors: parseBooleanFlag(RUNTIME_ENV.ESTIMATE_INCLUDE_TOP_FACTORS, true),
  includeWarnings: parseBooleanFlag(RUNTIME_ENV.ESTIMATE_INCLUDE_WARNINGS, true),
  includeLayersContext: parseBooleanFlag(RUNTIME_ENV.ESTIMATE_INCLUDE_LAYERS_CONTEXT, true)
};
export const ESTIMATE_WEIGHT_DEFAULTS = {
  crime: parseWeight(RUNTIME_ENV.ESTIMATE_WEIGHT_CRIME, 50),
  schools: parseWeight(RUNTIME_ENV.ESTIMATE_WEIGHT_SCHOOLS, 50),
  greenSpace: parseWeight(RUNTIME_ENV.ESTIMATE_WEIGHT_GREEN_SPACE, 50),
  commute: parseWeight(RUNTIME_ENV.ESTIMATE_WEIGHT_COMMUTE, 50)
};

const ENABLED_LAYER_IDS = new Set(parseList(RUNTIME_ENV.ENABLED_LAYERS));
const LAYER_LAB_LAYER_ID_SET = new Set(parseList(RUNTIME_ENV.LAYER_LAB_LAYER_IDS));

export const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export const EDMONTON_CENTER = [53.5461, -113.4938];
export const EDMONTON_BOUNDS = [
  [53.3385, -113.7134],
  [53.7152, -113.2784]
];

const ALL_LAYER_DEFINITIONS = [
  { id: "schools", label: "Schools", color: "#1d4ed8" },
  { id: "parks", label: "Parks", color: "#15803d" },
  { id: "playgrounds", label: "Playgrounds", color: "#ea580c" },
  { id: "police_stations", label: "Police Stations", color: "#b91c1c" },
  { id: "transit_stops", label: "Transit Stops", color: "#0891b2" },
  { id: "businesses", label: "Businesses", color: "#7c3aed" },
  { id: "green_space", label: "Green Space", color: "#0f766e" },
  { id: "roads", label: "Roads", color: "#4b5563" },
  { id: "municipal_wards", label: "Municipal Wards", color: "#d97706" },
  { id: "provincial_districts", label: "Provincial Districts", color: "#7c3aed" },
  { id: "federal_districts", label: "Federal Districts", color: "#be123c" },
  { id: "census_subdivisions", label: "Census Subdivisions", color: "#334155" },
  { id: "census_boundaries", label: "Census Boundaries", color: "#475569" },
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
export const LAYER_LAB_DEFINITIONS = ALL_LAYER_DEFINITIONS.filter((layer) =>
  LAYER_LAB_LAYER_ID_SET.has(layer.id)
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

export const __configInternals = {
  loadEnvFile,
  parseList,
  normalizeSearchProvider,
  parseBooleanFlag,
  parseNumber,
  parseWeight
};
/* node:coverage enable */
