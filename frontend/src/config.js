export const API_BASE_URL = "http://localhost:8000/api/v1";

export const LAYER_DEFINITIONS = [
  { id: "schools", label: "Schools", color: "#1f6feb" },
  { id: "parks", label: "Parks", color: "#2e8b57" },
  { id: "census_boundaries", label: "Census Boundaries", color: "#a44dc5" },
  { id: "assessment_zones", label: "Assessment Zones", color: "#c46b15" }
];

export const DEFAULT_LOCATION = {
  canonical_location_id: null,
  canonical_address: "Edmonton, AB",
  coordinates: { lat: 53.5461, lng: -113.4938 },
  region: "Edmonton",
  neighbourhood: null,
  coverage_status: "supported"
};
