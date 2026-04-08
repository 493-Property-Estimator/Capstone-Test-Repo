function createRequestId(prefix) {
  return `${prefix}-${Date.now()}`;
}

const propertyTileCache = new Map();
let propertyTileIndexPromise = null;
const propertyViewportCache = new Map();

function isWithinEdmonton(lat, lng) {
  return lat >= 53.3385 && lat <= 53.7152 && lng >= -113.7134 && lng <= -113.2784;
}

function fetchJson(path) {
  return fetch(path).then((response) => {
    if (!response.ok) {
      throw new Error(`Failed to load ${path}`);
    }
    return response.json();
  });
}

function intersectsBounds(tile, bounds) {
  return !(
    tile.east < bounds.west ||
    tile.west > bounds.east ||
    tile.north < bounds.south ||
    tile.south > bounds.north
  );
}

function getPropertyTileIndex() {
  if (!propertyTileIndexPromise) {
    propertyTileIndexPromise = fetchJson(
      "./mock-data/assessment-properties-tiles/index.json"
    );
  }

  return propertyTileIndexPromise;
}

async function getPropertyTile(file) {
  if (!propertyTileCache.has(file)) {
    propertyTileCache.set(
      file,
      fetchJson(`./mock-data/assessment-properties-tiles/${file}`)
    );
  }

  return propertyTileCache.get(file);
}

async function getAssessmentPropertyFeatures(bounds) {
  const index = await getPropertyTileIndex();
  const selectedTiles = index.tiles.filter((tile) => intersectsBounds(tile, bounds));

  if (!selectedTiles.length) {
    return {
      tileCount: 0,
      featureCount: 0,
      features: []
    };
  }

  const collections = await Promise.all(
    selectedTiles.map((tile) => getPropertyTile(tile.file))
  );

  return {
    tileCount: selectedTiles.length,
    featureCount: selectedTiles.reduce((sum, tile) => sum + tile.count, 0),
    features: collections.flatMap((collection) => collection.features || [])
  };
}

function buildViewportCacheKey(bounds = {}, cursor = null) {
  return [
    Number(bounds.west || 0).toFixed(3),
    Number(bounds.south || 0).toFixed(3),
    Number(bounds.east || 0).toFixed(3),
    Number(bounds.north || 0).toFixed(3),
    Number(bounds.zoom || 0).toFixed(2),
    cursor || ""
  ].join("|");
}

function clusterAssessmentFeatures(features, zoom) {
  const bucketSize =
    zoom <= 11
      ? 0.03
      : zoom <= 12
        ? 0.024
        : zoom <= 13
          ? 0.018
          : zoom <= 14
            ? 0.012
            : zoom <= 15
              ? 0.008
              : zoom <= 16
                ? 0.005
                : 0.003;

  const buckets = new Map();

  features.forEach((feature) => {
    const [lng, lat] = feature.geometry.coordinates;
    const x = Math.floor(lng / bucketSize);
    const y = Math.floor(lat / bucketSize);
    const key = `${x}:${y}`;

    if (!buckets.has(key)) {
      buckets.set(key, []);
    }

    buckets.get(key).push(feature);
  });

  return Array.from(buckets.values()).map((bucket, index) => {
    const count = bucket.length;
    const lngs = bucket.map((feature) => feature.geometry.coordinates[0]);
    const lats = bucket.map((feature) => feature.geometry.coordinates[1]);
    return {
      cluster_id: `cluster-${zoom}-${index}`,
      center: {
        lat: lats.reduce((sum, value) => sum + value, 0) / count,
        lng: lngs.reduce((sum, value) => sum + value, 0) / count
      },
      count,
      bounds: {
        west: Math.min(...lngs),
        south: Math.min(...lats),
        east: Math.max(...lngs),
        north: Math.max(...lats)
      },
      sample_properties: bucket.slice(0, 3).map((feature) => ({
        canonical_location_id: feature.properties?.id || null,
        canonical_address: feature.properties?.address || feature.properties?.name || "Edmonton property",
        assessment_value: Number(
          String(feature.properties?.description || "")
            .match(/Assessment: \$([0-9,]+)/)?.[1]
            ?.replace(/,/g, "") || 0
        )
      }))
    };
  });
}

async function buildPropertyViewportResponse(bounds, { limit = 5000, cursor = null } = {}) {
  const cacheKey = buildViewportCacheKey(bounds, cursor);

  if (propertyViewportCache.has(cacheKey)) {
    return propertyViewportCache.get(cacheKey);
  }

  const result = await getAssessmentPropertyFeatures(bounds);
  const zoom = Number(bounds.zoom || 11);
  let response;

  if (zoom < 17) {
    response = {
      request_id: createRequestId("properties"),
      status: "ok",
      coverage_status: "complete",
      viewport: {
        west: bounds.west,
        south: bounds.south,
        east: bounds.east,
        north: bounds.north,
        zoom
      },
      render_mode: "cluster",
      legend: {
        title: "Assessment Properties",
        items: [{ label: "Cluster", color: "#a43434", shape: "circle" }]
      },
      clusters: clusterAssessmentFeatures(result.features, zoom),
      properties: [],
      page: {
        has_more: false,
        next_cursor: null
      },
      warnings: [
        {
          code: "PROPERTY_TILE_LOAD",
          severity: "info",
          title: "Clustered property view active",
          message: `Loaded ${result.featureCount.toLocaleString()} source properties from ${result.tileCount} intersecting tiles.`,
          affected_factors: [],
          dismissible: true
        }
      ]
    };
  } else {
    const sliced = result.features.slice(0, limit);
    response = {
      request_id: createRequestId("properties"),
      status: sliced.length < result.features.length ? "partial" : "ok",
      coverage_status: sliced.length < result.features.length ? "partial" : "complete",
      viewport: {
        west: bounds.west,
        south: bounds.south,
        east: bounds.east,
        north: bounds.north,
        zoom
      },
      render_mode: "property",
      legend: {
        title: "Assessment Properties",
        items: [{ label: "Property", color: "#a43434", shape: "circle" }]
      },
      clusters: [],
      properties: sliced.map((feature) => ({
        canonical_location_id: feature.properties?.id || null,
        canonical_address: feature.properties?.address || feature.properties?.name || "Edmonton property",
        coordinates: {
          lat: feature.geometry.coordinates[1],
          lng: feature.geometry.coordinates[0]
        },
        neighbourhood:
          String(feature.properties?.description || "").match(/Neighbourhood: ([^|]+)/)?.[1]?.trim() || null,
        ward:
          String(feature.properties?.description || "").match(/Ward: ([^|]+)/)?.[1]?.trim() || null,
        assessment_value: Number(
          String(feature.properties?.description || "")
            .match(/Assessment: \$([0-9,]+)/)?.[1]
            ?.replace(/,/g, "") || 0
        ),
        tax_class:
          String(feature.properties?.description || "").match(/Tax class: (.+)$/)?.[1]?.trim() || null,
        name: feature.properties?.name || null,
        description: feature.properties?.description || null
      })),
      page: {
        has_more: sliced.length < result.features.length,
        next_cursor: sliced.length < result.features.length ? `offset:${sliced.length}` : null
      },
      warnings: [
        {
          code: "PROPERTY_TILE_LOAD",
          severity: "info",
          title: "Property tiles loaded",
          message: `Loaded ${Math.min(result.featureCount, limit).toLocaleString()} visible properties from ${result.tileCount} intersecting tiles.`,
          affected_factors: [],
          dismissible: true
        }
      ]
    };
  }

  propertyViewportCache.set(cacheKey, response);
  return response;
}

async function getAssessmentPropertyFallbackFeatures() {
  const geojson = await fetchJson("./mock-data/assessment-properties.geojson");
  return {
    tileCount: 1,
    featureCount: (geojson.features || []).length,
    features: geojson.features || []
  };
}

const knownLocations = [
  {
    canonical_location_id: "loc_10234_98_st_nw",
    canonical_address: "10234 98 Street NW, Edmonton, AB T5H 2P9",
    coordinates: { lat: 53.5461, lng: -113.4938 },
    region: "Edmonton",
    neighbourhood: "Downtown",
    coverage_status: "supported"
  },
  {
    canonical_location_id: "loc_10950_97_st_nw",
    canonical_address: "10950 97 St NW, Edmonton, AB",
    coordinates: { lat: 53.5554, lng: -113.4959 },
    region: "Edmonton",
    neighbourhood: "Central McDougall",
    coverage_status: "supported"
  },
  {
    canonical_location_id: "loc_5432_111_ave_nw",
    canonical_address: "5432 111 Avenue NW, Edmonton, AB",
    coordinates: { lat: 53.5631, lng: -113.4294 },
    region: "Edmonton",
    neighbourhood: "Highlands",
    coverage_status: "supported"
  }
];

function buildEstimateResponse(payload) {
  const coordinates = payload.location?.coordinates || knownLocations[0].coordinates;
  const bedrooms = payload.property_details?.bedrooms || 0;
  const bathrooms = payload.property_details?.bathrooms || 0;
  const floorArea = payload.property_details?.floor_area_sqft || 0;
  const inCoverage = isWithinEdmonton(coordinates.lat, coordinates.lng);

  if (!inCoverage) {
    throw new Error("Coordinates must be within the supported Edmonton area.");
  }

  const base = 410000;
  const bedAdj = bedrooms * 8500;
  const bathAdj = bathrooms * 6000;
  const areaAdj = Math.min(Math.round(floorArea * 24), 65000);
  const finalEstimate = base + bedAdj + bathAdj + areaAdj;
  const hasStandardInputs = bedrooms > 0 || bathrooms > 0 || floorArea > 0;
  const status = hasStandardInputs ? "ok" : "partial";

  return {
    request_id: createRequestId("estimate"),
    estimate_id: `est_${Math.floor(Math.random() * 100000)}`,
    status,
    location: {
      canonical_location_id: payload.location?.canonical_location_id || "loc_mock",
      canonical_address:
        payload.location?.address || "Selected Edmonton property",
      coordinates,
      region: "Edmonton",
      neighbourhood: "Mock District",
      coverage_status: "supported"
    },
    baseline_value: base,
    final_estimate: finalEstimate,
    range: {
      low: finalEstimate - 18000,
      high: finalEstimate + 22000
    },
    factor_breakdown: [
      {
        factor_id: "assessment_baseline",
        label: "Assessment baseline",
        value: base,
        status: "available",
        summary: "Baseline assessment anchored from the assessment dataset."
      },
      {
        factor_id: "school_distance",
        label: "Distance to schools",
        value: 5400,
        status: "available",
        summary: "Nearby schools improve the location score."
      },
      {
        factor_id: "green_space",
        label: "Green space access",
        value: 3200,
        status: "available",
        summary: "Parks and green-space coverage support the estimate."
      },
      ...(hasStandardInputs
        ? [
            {
              factor_id: "property_details",
              label: "Property details",
              value: bedAdj + bathAdj + areaAdj,
              status: "available",
              summary: "Bedrooms, bathrooms, and floor area increased estimate confidence."
            }
          ]
        : [
            {
              factor_id: "property_details",
              label: "Property details",
              value: 0,
              status: "missing",
              summary: "Estimate used location-only inputs because standard property details were not supplied."
            },
            {
              factor_id: "commute_accessibility",
              label: "Commute accessibility",
              value: -1200,
              status: "approximated",
              summary: "Straight-line distance used because routing was unavailable."
            }
          ])
    ],
    confidence: hasStandardInputs
      ? { score: 0.9, percentage: 90, label: "high", completeness: "complete" }
      : { score: 0.67, percentage: 67, label: "medium", completeness: "partial" },
    warnings: hasStandardInputs
      ? []
      : [
          {
            code: "MISSING_DATA",
            severity: "warning",
            title: "Some data is missing",
            message: "Property details were not provided, so the estimate uses location-only inputs.",
            affected_factors: ["property_details"],
            dismissible: true
          },
          {
            code: "ROUTING_FALLBACK_USED",
            severity: "warning",
            title: "Approximate distances used",
            message: "Routing was unavailable, so straight-line distance was used.",
            affected_factors: ["commute_accessibility"],
            dismissible: true
          }
        ],
    missing_factors: hasStandardInputs ? [] : ["property_details"],
    approximations: hasStandardInputs ? [] : ["commute_accessibility"]
  };
}

function buildLayerFeatures(layerId, bounds = null) {
  const common = {
    request_id: createRequestId(`layer-${layerId}`),
    layer_id: layerId,
    status: "ok",
    coverage_status: "complete",
    warnings: []
  };

  if (layerId === "schools") {
    return {
      ...common,
      legend: {
        title: "Schools",
        items: [{ label: "School", color: "#1f6feb", shape: "circle" }]
      },
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [-113.4938, 53.5461] },
          properties: {
            id: "school_001",
            name: "Downtown School",
            category: "public",
            address: "10234 98 Street NW, Edmonton, AB",
            description: "Mock public school near the downtown core"
          }
        },
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [-113.4815, 53.5532] },
          properties: {
            id: "school_002",
            name: "River Valley School",
            category: "public",
            address: "9805 Jasper Ave NW, Edmonton, AB",
            description: "Mock school fixture for layer rendering"
          }
        }
      ]
    };
  }

  if (layerId === "parks") {
    return {
      ...common,
      legend: {
        title: "Parks",
        items: [{ label: "Park", color: "#2e8b57", shape: "polygon" }]
      },
      features: [
        {
          type: "Feature",
          geometry: {
            type: "Polygon",
            coordinates: [[
              [-113.501, 53.548],
              [-113.497, 53.548],
              [-113.497, 53.551],
              [-113.501, 53.551],
              [-113.501, 53.548]
            ]]
          },
          properties: {
            id: "park_001",
            name: "Mock Riverfront Park",
            category: "park",
            address: "Central Edmonton",
            description: "Mock polygon park for green-space display"
          }
        }
      ]
    };
  }

  if (layerId === "census_boundaries") {
    return {
      ...common,
      legend: {
        title: "Census Boundaries",
        items: [{ label: "Boundary", color: "#a44dc5", shape: "line" }]
      },
      features: [
        {
          type: "Feature",
          geometry: {
            type: "Polygon",
            coordinates: [[
              [-113.51, 53.54],
              [-113.48, 53.54],
              [-113.48, 53.56],
              [-113.51, 53.56],
              [-113.51, 53.54]
            ]]
          },
          properties: {
            id: "census_001",
            name: "Downtown Census Area",
            category: "boundary",
            address: "Downtown Edmonton",
            description: "Mock census boundary layer"
          }
        }
      ]
    };
  }

  if (layerId === "assessment_properties") {
    const legend = {
      title: "Assessment Properties",
      items: [{ label: "Property", color: "#a43434", shape: "circle" }]
    };

    return getAssessmentPropertyFeatures(bounds)
      .then((result) => {
        if (!result.features.length) {
          return getAssessmentPropertyFallbackFeatures().then((fallback) => ({
            ...common,
            status: "partial",
            coverage_status: "partial",
            legend,
            features: fallback.features,
            warnings: [
              {
                code: "FALLBACK_PROPERTY_SAMPLE",
                severity: "info",
                title: "Sample property view active",
                message:
                  "No intersecting property tiles were returned, so the exported sample property layer was used instead.",
                affected_factors: [],
                dismissible: true
              }
            ]
          }));
        }

        return {
          ...common,
          legend,
          features: result.features,
          warnings: [
            {
              code: "PROPERTY_TILE_LOAD",
              severity: "info",
              title: "Property tiles loaded",
              message: `Loaded ${result.featureCount.toLocaleString()} properties from ${result.tileCount} intersecting tiles.`,
              affected_factors: [],
              dismissible: true
            }
          ]
        };
      })
      .catch(() =>
        getAssessmentPropertyFallbackFeatures().then((fallback) => ({
          ...common,
          status: "partial",
          coverage_status: "partial",
          legend,
          features: fallback.features,
          warnings: [
            {
              code: "FALLBACK_PROPERTY_SAMPLE",
              severity: "warning",
              title: "Property tile load failed",
              message:
                "The full tiled property layer could not be loaded, so the exported sample property layer is being displayed.",
              affected_factors: [],
              dismissible: true
            }
          ]
        }))
      );
  }

  return {
    request_id: createRequestId(`layer-${layerId}`),
    layer_id: layerId,
    status: "partial",
    coverage_status: "partial",
    legend: {
      title: "Assessment Zones",
      items: [{ label: "Assessment Zone", color: "#c46b15", shape: "polygon" }]
    },
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [[
            [-113.505, 53.543],
            [-113.489, 53.543],
            [-113.489, 53.552],
            [-113.505, 53.552],
            [-113.505, 53.543]
          ]]
        },
        properties: {
          id: "zone_001",
          name: "Assessment Zone A",
          category: "assessment_zone",
          address: "Central Edmonton",
          description: "Mock assessment zone coverage"
        }
      }
    ],
    warnings: [
      {
        code: "PARTIAL_COVERAGE",
        severity: "warning",
        title: "Incomplete layer coverage",
        message: "Assessment zone coverage is partial in this view.",
        affected_factors: [],
        dismissible: true
      }
    ]
  };
}

function buildResolvedLocationFromCoordinates(payload) {
  const coordinates = payload.coordinates;

  if (!isWithinEdmonton(coordinates.lat, coordinates.lng)) {
    return {
      request_id: createRequestId("click"),
      status: "outside_supported_area",
      click_id: payload.click_id,
      location: null,
      error: {
        code: "OUTSIDE_SUPPORTED_AREA",
        message: "Location is outside the supported area.",
        details: {},
        retryable: false
      }
    };
  }

  return {
    request_id: createRequestId("click"),
    status: "resolved",
    click_id: payload.click_id,
    location: {
      canonical_location_id: `loc_click_${payload.click_id}`,
      canonical_address: `Selected location (${coordinates.lat}, ${coordinates.lng})`,
      coordinates,
      region: "Edmonton",
      neighbourhood: "Map Selection",
      coverage_status: "supported"
    }
  };
}

export const mockApi = {
  async getAddressSuggestions(query, limit = 5) {
    const q = query.toLowerCase();
    const suggestions = knownLocations
      .filter((location) => location.canonical_address.toLowerCase().includes(q))
      .slice(0, limit)
      .map((location, index) => ({
        id: `suggestion_${index + 1}`,
        display_text: location.canonical_address,
        secondary_text: location.neighbourhood,
        rank: index + 1,
        confidence: "high"
      }));

    return {
      request_id: createRequestId("suggestions"),
      query,
      suggestions
    };
  },

  async resolveAddress(query) {
    const q = query.toLowerCase().trim();

    if (q.includes("123 main")) {
      return {
        request_id: createRequestId("resolve"),
        status: "ambiguous",
        location: null,
        candidates: [
          {
            candidate_id: "cand_main_nw",
            display_text: "123 Main Street NW, Edmonton, AB T5J 1A1",
            coordinates: { lat: 53.5449, lng: -113.4905 },
            coverage_status: "supported"
          },
          {
            candidate_id: "cand_main_sw",
            display_text: "123 Main Street SW, Edmonton, AB T6X 0P9",
            coordinates: { lat: 53.4152, lng: -113.514 },
            coverage_status: "supported"
          }
        ]
      };
    }

    if (q.includes("calgary")) {
      return {
        request_id: createRequestId("resolve"),
        status: "unsupported_region",
        location: {
          canonical_location_id: null,
          canonical_address: "123 Main Street SW, Calgary, AB T2P 1M7",
          coordinates: { lat: 51.0447, lng: -114.0719 },
          region: "Outside Coverage",
          neighbourhood: null,
          coverage_status: "unsupported"
        },
        candidates: []
      };
    }

    const known = knownLocations.find((location) =>
      location.canonical_address.toLowerCase().includes(q)
    );

    if (known) {
      return {
        request_id: createRequestId("resolve"),
        status: "resolved",
        location: known,
        candidates: []
      };
    }

    return {
      request_id: createRequestId("resolve"),
      status: "not_found",
      location: null,
      candidates: []
    };
  },

  async resolveMapClick(payload) {
    return buildResolvedLocationFromCoordinates(payload);
  },

  async getEstimate(payload) {
    return buildEstimateResponse(payload);
  },

  async getLayerData(params) {
    return buildLayerFeatures(params.layerId, params);
  },

  async getProperties(params) {
    return buildPropertyViewportResponse(params, params);
  }
};
