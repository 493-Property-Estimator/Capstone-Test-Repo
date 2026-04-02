export const API_BASE_URL = "http://localhost:8000/api/v1";
export const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export const EDMONTON_CENTER = [53.5461, -113.4938];
export const EDMONTON_BOUNDS = [
  [53.3958, -113.7136],
  [53.716, -113.2714]
];

export const LAYER_DEFINITIONS = [
  { id: "schools", label: "Schools", color: "#1f6feb" },
  { id: "parks", label: "Parks", color: "#2e8b57" },
  { id: "playgrounds", label: "Playgrounds", color: "#f0883e" },
  { id: "police_stations", label: "Police Stations", color: "#b91c1c" },
  { id: "municipal_wards", label: "Municipal Wards", color: "#b45309" },
  { id: "provincial_districts", label: "Provincial Districts", color: "#7c3aed" },
  { id: "federal_districts", label: "Federal Districts", color: "#0f766e" },
  { id: "census_subdivisions", label: "Census Subdivisions", color: "#475569" }
];

export const DEFAULT_LOCATION = {
  canonical_location_id: null,
  canonical_address: "Edmonton, AB",
  coordinates: { lat: 53.5461, lng: -113.4938 },
  region: "Edmonton",
  neighbourhood: null,
  coverage_status: "supported"
};
