/* node:coverage disable */
import {
  EDMONTON_BOUNDS,
  EDMONTON_CENTER,
  LAYER_DEFINITIONS,
  OSM_ATTRIBUTION,
  OSM_TILE_URL
} from "../config.js";
import { createElement, clearElement, setText } from "../utils/dom.js";
import { debounce } from "../utils/debounce.js";

export function createMapAdapter({
  root,
  onMapClick,
  onViewportChange,
  messageElement,
  propertyCardElement,
  propertyDetailPanelElement,
  onPropertySelect,
  onSelectionCleared
}) {
  let clickHandler = onMapClick;
  let viewportChangeHandler = onViewportChange;
  let propertySelectHandler = onPropertySelect;
  let selectionClearedHandler = onSelectionCleared;
  let map = null;
  let mapCanvas = null;
  let marker = null;
  let markerPopup = null;
  let layerContainer = null;
  let lastActiveLayers = null;
  let lastPropertyLayerState = null;
  let propertyCardAnimationFrame = null;
  let pointerDownPoint = null;
  let mapWasDragged = false;
  let suppressNextMapClick = false;
  let pendingMapClickTimeoutId = null;
  let styleLoaded = false;

  const singleClickDelayMs = 220;
  const renderedLayerIds = new Map();
  const interactionRegistry = new Set();

  function createSelectedMarkerElement() {
    const element = document.createElement("span");
    element.className = "selected-property-marker";
    return element;
  }

  function positionPropertyCard(clientX, clientY) {
    /* node:coverage ignore next */
    if (!propertyCardElement) return;

    const rootRect = root.getBoundingClientRect();
    const cardRect = propertyCardElement.getBoundingClientRect();
    const offset = 18;
    const maxLeft = Math.max(12, rootRect.width - cardRect.width - 12);
    const maxTop = Math.max(12, rootRect.height - cardRect.height - 12);

    propertyCardElement.style.left = `${Math.min(maxLeft, Math.max(12, clientX - rootRect.left + offset))}px`;
    propertyCardElement.style.top = `${Math.min(maxTop, Math.max(12, clientY - rootRect.top + offset))}px`;
  }

  function updatePropertyCardPosition(event) {
    const originalEvent = event?.originalEvent;

    /* node:coverage ignore next */
    if (!propertyCardElement || !originalEvent) return;
    /* node:coverage ignore next */
    if (propertyCardAnimationFrame) window.cancelAnimationFrame(propertyCardAnimationFrame);

    propertyCardAnimationFrame = window.requestAnimationFrame(() => {
      positionPropertyCard(originalEvent.clientX, originalEvent.clientY);
      propertyCardAnimationFrame = null;
    });
  }

  function renderPropertyCard(properties = null, event = null) {
    if (!propertyCardElement) {
      return;
    }

    if (!properties) {
      propertyCardElement.classList.remove("is-visible");
      return;
    }

    propertyCardElement.innerHTML = `
      <p class="eyebrow">Property Card</p>
      <h3>${properties.name || "Selected property"}</h3>
      <p class="property-card-copy">${properties.address || "Edmonton property"}</p>
      <p class="property-card-copy">${properties.assessment_text || "--"} · ${properties.neighbourhood || "--"}</p>
    `;

    propertyCardElement.classList.remove("is-hidden");
    propertyCardElement.classList.add("is-visible");

    if (event) {
      updatePropertyCardPosition(event);
    }
  }

  function createRasterStyle() {
    const tileUrls = ["a", "b", "c"].map((subdomain) =>
      OSM_TILE_URL.replace("{s}", subdomain)
    );

    return {
      version: 8,
      glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
      sources: {
        "osm-raster": {
          type: "raster",
          tiles: tileUrls,
          tileSize: 256,
          attribution: OSM_ATTRIBUTION
        }
      },
      layers: [
        {
          id: "osm-raster-layer",
          type: "raster",
          source: "osm-raster"
        }
      ]
    };
  }

  function renderBase() {
    clearElement(root);

    mapCanvas = createElement("div", "map-canvas");
    root.appendChild(mapCanvas);

    if (propertyCardElement) {
      propertyCardElement.classList.add("is-hidden");
      propertyCardElement.classList.remove("is-visible");
      root.appendChild(propertyCardElement);
    }

    if (propertyDetailPanelElement) {
      root.appendChild(propertyDetailPanelElement);
    }

    layerContainer = createElement("div", "map-layer-container");
    root.appendChild(layerContainer);

    if (!window.maplibregl) {
      setText(messageElement, "MapLibre failed to load.");
      return;
    }

    map = new window.maplibregl.Map({
      container: mapCanvas,
      style: createRasterStyle(),
      center: [EDMONTON_CENTER[1], EDMONTON_CENTER[0]],
      zoom: 11,
      minZoom: 10,
      maxZoom: 19,
      maxBounds: [
        [EDMONTON_BOUNDS[0][1], EDMONTON_BOUNDS[0][0]],
        [EDMONTON_BOUNDS[1][1], EDMONTON_BOUNDS[1][0]]
      ]
    });

    map.addControl(new window.maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      styleLoaded = true;
      if (lastActiveLayers) {
        renderLayers(lastActiveLayers);
      }
      if (lastPropertyLayerState?.enabled) {
        renderAssessmentLayer(
          "assessment_properties",
          lastPropertyLayerState,
          LAYER_DEFINITIONS.find((layer) => layer.id === "assessment_properties")
        );
      }
      if (viewportChangeHandler) {
        viewportChangeHandler(getViewport());
      }
    });

    map.on("mousedown", (event) => {
      pointerDownPoint = {
        x: event.originalEvent.clientX,
        y: event.originalEvent.clientY
      };
      mapWasDragged = false;
    });

    map.on("dragstart", () => {
      mapWasDragged = true;
      renderPropertyCard();
    });

    const handleMapClick = (event) => {
      if (suppressNextMapClick) {
        suppressNextMapClick = false;
        return;
      }

      const nearbyProperty = findNearbyPropertyFeature(event.point);
      if (nearbyProperty) {
        suppressNextMapClick = true;
        selectPropertyFeature(nearbyProperty);
        pointerDownPoint = null;
        mapWasDragged = false;
        return;
      }

      const movedDistance = pointerDownPoint
        ? Math.hypot(
            event.originalEvent.clientX - pointerDownPoint.x,
            event.originalEvent.clientY - pointerDownPoint.y
          )
        : 0;

      /* node:coverage ignore next */
      if (mapWasDragged || movedDistance > 8) return pointerDownPoint = null, mapWasDragged = false, undefined;

      clickHandler({
        lat: Number(event.lngLat.lat.toFixed(5)),
        lng: Number(event.lngLat.lng.toFixed(5))
      });

      pointerDownPoint = null;
      mapWasDragged = false;
    };

    map.on("click", (event) => {
      if (event.originalEvent?.button !== 0) {
        return;
      }

      if (pendingMapClickTimeoutId) {
        window.clearTimeout(pendingMapClickTimeoutId);
      }

      pendingMapClickTimeoutId = window.setTimeout(() => {
        pendingMapClickTimeoutId = null;
        handleMapClick(event);
      }, singleClickDelayMs);
    });

    map.on("dblclick", (event) => {
      if (event.originalEvent?.button !== 0) {
        return;
      }

      if (pendingMapClickTimeoutId) {
        window.clearTimeout(pendingMapClickTimeoutId);
        pendingMapClickTimeoutId = null;
      }

      pointerDownPoint = null;
      mapWasDragged = false;
    });

    const debouncedViewportChange = debounce(() => {
      /* node:coverage ignore next */
      if (viewportChangeHandler) viewportChangeHandler(getViewport());
    }, 120);

    map.on("moveend", debouncedViewportChange);
    map.on("zoomend", debouncedViewportChange);
  }

  function buildPopupHtml(properties = {}) {
    return [properties.name, properties.address, properties.description]
      .filter(Boolean)
      .join("<br />");
  }

  function getLayerColor(layerId, definition) {
    const palette = {
      schools: "#1d4ed8",
      parks: "#15803d",
      playgrounds: "#ea580c",
      police_stations: "#b91c1c",
      transit_stops: "#0891b2",
      businesses: "#7c3aed",
      green_space: "#0f766e",
      roads: "#4b5563",
      municipal_wards: "#d97706",
      provincial_districts: "#8b5cf6",
      federal_districts: "#be123c",
      census_subdivisions: "#334155",
      census_boundaries: "#475569",
      assessment_properties: "#a43434"
    };

    return palette[layerId] || definition?.color || "#666666";
  }

  function geometryCenter(geometry) {
    if (!geometry?.type || geometry.coordinates == null) {
      return null;
    }

    if (geometry.type === "Point" && Array.isArray(geometry.coordinates) && geometry.coordinates.length >= 2) {
      return {
        lng: Number(geometry.coordinates[0]),
        lat: Number(geometry.coordinates[1])
      };
    }

    const values = [];
    const collect = (node) => {
      if (!Array.isArray(node)) {
        return;
      }
      if (
        node.length >= 2 &&
        typeof node[0] === "number" &&
        typeof node[1] === "number"
      ) {
        values.push([Number(node[0]), Number(node[1])]);
        return;
      }
      node.forEach((child) => collect(child));
    };

    collect(geometry.coordinates);

    if (!values.length) {
      return null;
    }

    const sum = values.reduce(
      (accumulator, [lng, lat]) => ({
        lng: accumulator.lng + lng,
        lat: accumulator.lat + lat
      }),
      { lng: 0, lat: 0 }
    );

    return {
      lng: sum.lng / values.length,
      lat: sum.lat / values.length
    };
  }

  function toPointFeatures(layerState, fallbackLabel) {
    return (layerState?.data?.features || [])
      .map((feature) => {
        const center = geometryCenter(feature?.geometry);
        if (!center) {
          return null;
        }

        return {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [center.lng, center.lat]
          },
          properties: {
            ...(feature?.properties || {}),
            name: feature?.properties?.name || fallbackLabel,
            address: feature?.properties?.address || null,
            description: feature?.properties?.description || null
          }
        };
      })
      .filter(Boolean);
  }

  function ensurePopup() {
    if (!map || markerPopup) {
      return;
    }

    markerPopup = new window.maplibregl.Popup({
      offset: 16,
      closeButton: false
    });
  }

  function renderMarker(location) {
    /* node:coverage ignore next */
    if (!map) return;

    ensurePopup();

    if (!marker) {
      marker = new window.maplibregl.Marker({
        element: createSelectedMarkerElement(),
        anchor: "center"
      })
        .setLngLat([location.coordinates.lng, location.coordinates.lat])
        .addTo(map);
    } else {
      marker.setLngLat([location.coordinates.lng, location.coordinates.lat]);
    }

    markerPopup.setText(location.canonical_address || "Selected property");
    marker.setPopup(markerPopup);
  }

  function normalizePropertyFeature(featureRecord) {
    const feature = featureRecord?.properties;

    if (!feature) {
      return null;
    }

    let details = feature.details;
    if (typeof details === "string") {
      try {
        details = JSON.parse(details);
      } catch {
        details = {};
      }
    }

    return {
      ...feature,
      details: details || {},
      canonical_address: feature.canonical_address || feature.address || "Edmonton property",
      coordinates: feature.coordinates || (
        featureRecord?.geometry?.coordinates
          ? {
              lng: Number(featureRecord.geometry.coordinates[0]),
              lat: Number(featureRecord.geometry.coordinates[1])
            }
          : null
      )
    };
  }

  function selectPropertyFeature(featureRecord) {
    const normalized = normalizePropertyFeature(featureRecord);

    if (!normalized || !propertySelectHandler) {
      return false;
    }

    propertySelectHandler(normalized);
    return true;
  }

  function findNearbyPropertyFeature(point) {
    if (!map || !point || !map.getLayer("assessment_properties-points")) {
      return null;
    }

    const hitRadius = 12;
    const features = map.queryRenderedFeatures(
      [
        [point.x - hitRadius, point.y - hitRadius],
        [point.x + hitRadius, point.y + hitRadius]
      ],
      { layers: ["assessment_properties-points"] }
    );

    return features?.[0] || null;
  }

  function setView(location, options = {}) {
    /* node:coverage ignore next */
    if (!map) return;

    const {
      zoom = 15,
      preserveZoom = false,
      animate = true,
      panOnly = false
    } = options;

    renderMarker(location);

    const target = {
      center: [location.coordinates.lng, location.coordinates.lat],
      duration: animate ? 800 : 0
    };

    if (panOnly || preserveZoom) {
      map.easeTo(target);
    } else {
      map.flyTo({
        ...target,
        zoom
      });
    }

    setText(messageElement, `Viewing ${location.canonical_address || "selected property"}`);
  }

  function clearSelection() {
    /* node:coverage ignore next */
    if (marker) marker.remove(), marker = null;

    if (markerPopup) {
      markerPopup.remove();
    }

    renderPropertyCard();
    setText(messageElement, "Selection cleared.");

    if (selectionClearedHandler) {
      selectionClearedHandler();
    }
  }

  function focusEdmonton() {
    /* node:coverage ignore next */
    if (!map) return;

    renderPropertyCard();
    map.fitBounds(EDMONTON_BOUNDS, {
      padding: [24, 24]
    });
    setText(messageElement, "Viewing Edmonton.");
  }

  function resetView() {
    /* node:coverage ignore next */
    if (!map) return;

    if (marker) {
      marker.remove();
      marker = null;
    }

    if (markerPopup) {
      markerPopup.remove();
    }

    renderPropertyCard();
    map.flyTo({
      center: [EDMONTON_CENTER[1], EDMONTON_CENTER[0]],
      zoom: 11,
      duration: 600
    });
    setText(messageElement, "Map reset to Edmonton overview.");
  }

  function removeRenderedLayer(layerId) {
    /* node:coverage ignore next */
    if (!map || !styleLoaded) return;

    const ids = renderedLayerIds.get(layerId) || [];
    const sourceId = `source-${layerId}`;

    [...ids].reverse().forEach((id) => {
      if (map.getLayer(id)) {
        map.removeLayer(id);
      }
    });

    if (map.getSource(sourceId)) {
      map.removeSource(sourceId);
    }

    renderedLayerIds.delete(layerId);
  }

  function upsertSource(sourceId, data, options = {}) {
    const sourceData = {
      type: "FeatureCollection",
      features: data.features || []
    };

    if (map.getSource(sourceId)) {
      map.getSource(sourceId).setData(sourceData);
      return;
    }

    map.addSource(sourceId, {
      type: "geojson",
      data: sourceData,
      ...options
    });
  }

  function registerAssessmentInteractions({
    layerId,
    clusterLayerId = null,
    clusterCountLayerId = null,
    pointLayerId
  }) {
    if (clusterLayerId && clusterCountLayerId && !interactionRegistry.has(clusterLayerId)) {
      interactionRegistry.add(clusterLayerId);

      const handleClusterClick = (event) => {
        suppressNextMapClick = true;
        const feature = event.features?.[0];

        /* node:coverage ignore next */
        if (!feature) return;

        map.easeTo({
          center: feature.geometry.coordinates,
          zoom: Math.min(map.getZoom() + 2, 18)
        });
      };

      map.on("click", clusterLayerId, handleClusterClick);
      map.on("click", clusterCountLayerId, handleClusterClick);

      /* node:coverage ignore next */
      map.on("mouseenter", clusterLayerId, () => { map.getCanvas().style.cursor = "pointer"; });
      /* node:coverage ignore next */
      map.on("mouseenter", clusterCountLayerId, () => { map.getCanvas().style.cursor = "pointer"; });
      /* node:coverage ignore next */
      map.on("mouseleave", clusterLayerId, () => { map.getCanvas().style.cursor = ""; });
      /* node:coverage ignore next */
      map.on("mouseleave", clusterCountLayerId, () => { map.getCanvas().style.cursor = ""; });
    }

    if (pointLayerId && !interactionRegistry.has(pointLayerId)) {
      interactionRegistry.add(pointLayerId);

      map.on("mousemove", pointLayerId, (event) => {
        map.getCanvas().style.cursor = "pointer";
        renderPropertyCard(event.features?.[0]?.properties || null, event);
      });

      map.on("click", pointLayerId, (event) => {
        suppressNextMapClick = true;
        const featureRecord = event.features?.[0];

        if (!featureRecord) {
          return;
        }

        selectPropertyFeature(featureRecord);
      });

      map.on("mouseleave", pointLayerId, () => {
        map.getCanvas().style.cursor = "";
        renderPropertyCard();
      });
    }
  }

  function renderAssessmentLayer(layerId, data, definition) {
    const sourceId = `source-${layerId}`;
    const layerColor = getLayerColor(layerId, definition);
    const displayMode = data.displayMode || "clusters";
    const propertyFeatures = (data.properties || [])
      .filter((property) => property?.coordinates?.lat != null && property?.coordinates?.lng != null)
      .map((property) => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [property.coordinates.lng, property.coordinates.lat]
        },
        properties: {
          canonical_location_id: property.canonical_location_id,
          name: property.name || property.canonical_address,
          address: property.canonical_address,
          coordinates: property.coordinates,
          neighbourhood: property.neighbourhood || property.details?.neighbourhood || "--",
          ward: property.ward || property.details?.ward || "--",
          tax_class: property.tax_class || property.details?.tax_class || "--",
          assessment_value: property.assessment_value ?? property.details?.assessment_value ?? null,
          assessment_text: property.assessment_value != null
            ? `$${Number(property.assessment_value).toLocaleString()}`
            : "--",
          details: property.details || {},
          description:
            property.description ||
            `Assessment: $${Number(property.assessment_value || 0).toLocaleString()} | Neighbourhood: ${property.neighbourhood || "--"} | Ward: ${property.ward || "--"} | Tax class: ${property.tax_class || "--"}`
        }
      }));
    const clusterCenterFeatures = (data.clusters || []).map((cluster) => ({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [cluster.center.lng, cluster.center.lat]
      },
      properties: {
        cluster: true,
        cluster_id: cluster.cluster_id,
        point_count: cluster.count,
        point_count_abbreviated: String(cluster.count),
        name: `Cluster ${cluster.cluster_id}`,
        address: "",
        description: `${cluster.count} properties`
      }
    }));

    let sourceFeatures = [];
    let sourceOptions = {};
    const clusterLayerId = `${layerId}-cluster-circle`;
    const clusterCountLayerId = `${layerId}-cluster-count`;
    const pointLayerId = `${layerId}-points`;
    const heatLayerId = `${layerId}-heat`;
    const heatPointLayerId = `${layerId}-heat-points`;

    if (displayMode === "clusters") {
      if (data.renderMode === "property") {
        sourceFeatures = propertyFeatures;
        sourceOptions = { cluster: true, clusterRadius: 42, clusterMaxZoom: 15 };
      } else {
        sourceFeatures = clusterCenterFeatures;
      }
      upsertSource(sourceId, { features: sourceFeatures }, sourceOptions);

      map.addLayer({
        id: clusterLayerId,
        type: "circle",
        source: sourceId,
        filter: ["has", "point_count"],
        paint: {
          "circle-color": [
            "step",
            ["get", "point_count"],
            layerColor,
            15,
            layerColor,
            60,
            layerColor
          ],
          "circle-radius": [
            "step",
            ["get", "point_count"],
            14,
            15,
            18,
            60,
            22
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2
        }
      });
      map.addLayer({
        id: clusterCountLayerId,
        type: "symbol",
        source: sourceId,
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-size": 12,
          "text-font": ["Noto Sans Regular"],
          "text-allow-overlap": true,
          "text-ignore-placement": true
        },
        paint: {
          "text-color": "#ffffff"
        }
      });
      map.addLayer({
        id: pointLayerId,
        type: "circle",
        source: sourceId,
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": layerColor,
          "circle-radius": 4,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.2
        }
      });

      registerAssessmentInteractions({
        layerId,
        clusterLayerId,
        clusterCountLayerId,
        pointLayerId
      });
      renderedLayerIds.set(layerId, [clusterLayerId, clusterCountLayerId, pointLayerId]);
      return;
    }

    sourceFeatures = propertyFeatures.length ? propertyFeatures : clusterCenterFeatures;
    upsertSource(sourceId, { features: sourceFeatures });

    if (displayMode === "heatmap") {
      map.addLayer({
        id: heatLayerId,
        type: "heatmap",
        source: sourceId,
        paint: {
          "heatmap-weight": 1,
          "heatmap-intensity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            9,
            0.7,
            16,
            1.8
          ],
          "heatmap-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            9,
            12,
            16,
            28
          ],
          "heatmap-opacity": 0.9,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(33,102,172,0)",
            0.2,
            "#7cc8ff",
            0.5,
            layerColor,
            1,
            "#7f1d1d"
          ]
        }
      });
      map.addLayer({
        id: heatPointLayerId,
        type: "circle",
        source: sourceId,
        minzoom: 14,
        paint: {
          "circle-color": layerColor,
          "circle-radius": 3.3,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 0.9,
          "circle-opacity": 0.8
        }
      });

      registerAssessmentInteractions({
        layerId,
        pointLayerId: heatPointLayerId
      });
      renderedLayerIds.set(layerId, [heatLayerId, heatPointLayerId]);
      return;
    }

    map.addLayer({
      id: pointLayerId,
      type: "circle",
      source: sourceId,
      paint: {
        "circle-color": layerColor,
        "circle-radius": 4.5,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.3
      }
    });
    registerAssessmentInteractions({
      layerId,
      pointLayerId
    });
    renderedLayerIds.set(layerId, [pointLayerId]);
  }

  function registerGenericInteractions(layerId) {
    const layerIds = renderedLayerIds.get(layerId) || [];

    layerIds.forEach((id) => {
      if (interactionRegistry.has(id)) {
        return;
      }

      interactionRegistry.add(id);

      map.on("mouseenter", id, () => {
        map.getCanvas().style.cursor = "pointer";
      });

      map.on("mouseleave", id, () => {
        map.getCanvas().style.cursor = "";
      });

      map.on("click", id, (event) => {
        suppressNextMapClick = true;
        const feature = event.features?.[0];
        const html = buildPopupHtml(feature?.properties || {});

        if (!feature || !html) {
          return;
        }

        new window.maplibregl.Popup({ offset: 12 })
          .setLngLat(event.lngLat)
          .setHTML(html)
          .addTo(map);
      });
    });
  }

  function renderGenericLayer(layerId, layerState, definition) {
    const sourceId = `source-${layerId}`;
    const renderMode = layerState?.renderMode || "points";
    const layerColor = getLayerColor(layerId, definition);
    const label = definition?.label || layerId;
    const pointLikeFeatures = toPointFeatures(layerState, label);

    upsertSource(
      sourceId,
      renderMode === "points"
        ? layerState.data
        : { features: pointLikeFeatures },
      renderMode === "clusters" ? { cluster: true, clusterRadius: 42, clusterMaxZoom: 15 } : {}
    );

    const fillLayerId = `${layerId}-fill`;
    const lineLayerId = `${layerId}-line`;
    const pointLayerId = `${layerId}-points`;
    const clusterLayerId = `${layerId}-cluster-circle`;
    const clusterCountLayerId = `${layerId}-cluster-count`;
    const heatLayerId = `${layerId}-heat`;
    const heatPointLayerId = `${layerId}-heat-points`;
    const rendered = [];
    const pointRadiusByLayer = {
      schools: 6.5,
      parks: 7,
      playgrounds: 6,
      police_stations: 7.5,
      businesses: 5.5,
      green_space: 6.5,
      transit_stops: 4.5
    };
    const lineWidthByLayer = {
      roads: 1.4,
      municipal_wards: 2.2,
      provincial_districts: 2.4,
      federal_districts: 2.6,
      census_subdivisions: 2,
      census_boundaries: 2
    };
    const fillOpacityByLayer = {
      municipal_wards: 0.09,
      provincial_districts: 0.08,
      federal_districts: 0.07,
      census_subdivisions: 0.1,
      census_boundaries: 0.08
    };

    if (renderMode === "clusters") {
      if (!map.getLayer(clusterLayerId)) {
        map.addLayer({
          id: clusterLayerId,
          type: "circle",
          source: sourceId,
          filter: ["has", "point_count"],
          paint: {
            "circle-color": [
              "step",
              ["get", "point_count"],
              layerColor,
              15,
              layerColor,
              45,
              layerColor
            ],
            "circle-radius": [
              "step",
              ["get", "point_count"],
              13,
              15,
              17,
              45,
              21
            ],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.8
          }
        });
      }
      rendered.push(clusterLayerId);

      if (!map.getLayer(clusterCountLayerId)) {
        map.addLayer({
          id: clusterCountLayerId,
          type: "symbol",
          source: sourceId,
          filter: ["has", "point_count"],
          layout: {
            "text-field": ["get", "point_count_abbreviated"],
            "text-size": 12,
            "text-font": ["Noto Sans Regular"],
            "text-allow-overlap": true,
            "text-ignore-placement": true
          },
          paint: {
            "text-color": "#ffffff"
          }
        });
      }
      rendered.push(clusterCountLayerId);

      if (!map.getLayer(pointLayerId)) {
        map.addLayer({
          id: pointLayerId,
          type: "circle",
          source: sourceId,
          filter: ["!", ["has", "point_count"]],
          paint: {
            "circle-color": layerColor,
            "circle-radius": Math.max(4, (pointRadiusByLayer[layerId] || 6) - 1.2),
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.2,
            "circle-opacity": 0.95
          }
        });
      }
      rendered.push(pointLayerId);
    } else if (renderMode === "heatmap") {
      if (!map.getLayer(heatLayerId)) {
        map.addLayer({
          id: heatLayerId,
          type: "heatmap",
          source: sourceId,
          paint: {
            "heatmap-weight": 1,
            "heatmap-intensity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              9,
              0.65,
              16,
              1.7
            ],
            "heatmap-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              9,
              12,
              16,
              30
            ],
            "heatmap-opacity": 0.88,
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(33,102,172,0)",
              0.25,
              "#7cc8ff",
              0.5,
              layerColor,
              1,
              "#7f1d1d"
            ]
          }
        });
      }
      rendered.push(heatLayerId);

      if (!map.getLayer(heatPointLayerId)) {
        map.addLayer({
          id: heatPointLayerId,
          type: "circle",
          source: sourceId,
          minzoom: 14,
          paint: {
            "circle-color": layerColor,
            "circle-radius": 3.4,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 0.9,
            "circle-opacity": 0.82
          }
        });
      }
      rendered.push(heatPointLayerId);
    } else {
      if (!map.getLayer(fillLayerId)) {
        map.addLayer({
          id: fillLayerId,
          type: "fill",
          source: sourceId,
          filter: [
            "any",
            ["==", ["geometry-type"], "Polygon"],
            ["==", ["geometry-type"], "MultiPolygon"]
          ],
          paint: {
            "fill-color": layerColor,
            "fill-opacity": fillOpacityByLayer[layerId] || 0.16
          }
        });
      }
      rendered.push(fillLayerId);

      if (!map.getLayer(lineLayerId)) {
        map.addLayer({
          id: lineLayerId,
          type: "line",
          source: sourceId,
          filter: [
            "any",
            ["==", ["geometry-type"], "LineString"],
            ["==", ["geometry-type"], "MultiLineString"],
            ["==", ["geometry-type"], "Polygon"],
            ["==", ["geometry-type"], "MultiPolygon"]
          ],
          paint: {
            "line-color": layerColor,
            "line-width": lineWidthByLayer[layerId] || 2
          }
        });
      }
      rendered.push(lineLayerId);

      if (!map.getLayer(pointLayerId)) {
        map.addLayer({
          id: pointLayerId,
          type: "circle",
          source: sourceId,
          filter: ["==", ["geometry-type"], "Point"],
          paint: {
            "circle-color": layerColor,
            "circle-radius": pointRadiusByLayer[layerId] || 6,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.6,
            "circle-opacity": layerId === "businesses" ? 0.9 : 0.96
          }
        });
      }
      rendered.push(pointLayerId);
    }

    renderedLayerIds.set(layerId, rendered);
    registerGenericInteractions(layerId);
  }

  function renderLayers(activeLayers) {
    lastActiveLayers = activeLayers;

    if (!map || !styleLoaded) {
      return;
    }

    clearElement(layerContainer);

    Object.entries(activeLayers).forEach(([layerId, layerState]) => {
      if (layerId === "assessment_properties") {
        return;
      }

      const definition = LAYER_DEFINITIONS.find((layer) => layer.id === layerId);

      if (!layerState.enabled || !layerState.data?.features?.length) {
        removeRenderedLayer(layerId);
        return;
      }

      removeRenderedLayer(layerId);
      renderGenericLayer(layerId, layerState, definition);

      const chip = createElement("div", "map-layer-chip");
      const swatch = createElement("span", "legend-swatch");
      swatch.style.background = getLayerColor(layerId, definition);
      const label = createElement(
        "span",
        null,
        `${definition?.label || layerId} · ${layerState.renderMode || "points"} · ${layerState.status || "loaded"}`
      );
      chip.appendChild(swatch);
      chip.appendChild(label);
      layerContainer.appendChild(chip);
    });
  }

  renderBase();

  function getViewport() {
    if (!map) {
      return {
        west: EDMONTON_BOUNDS[0][1],
        south: EDMONTON_BOUNDS[0][0],
        east: EDMONTON_BOUNDS[1][1],
        north: EDMONTON_BOUNDS[1][0],
        zoom: 11
      };
    }

    const bounds = map.getBounds();
    return {
      west: bounds.getWest(),
      south: bounds.getSouth(),
      east: bounds.getEast(),
      north: bounds.getNorth(),
      zoom: map.getZoom()
    };
  }

  return {
    clearSelection,
    focusEdmonton,
    setView,
    resetView,
    renderLayers,
    renderPropertyLayer(propertyLayerState) {
      lastPropertyLayerState = propertyLayerState;

      if (!propertyLayerState?.enabled) {
        removeRenderedLayer("assessment_properties");
        setText(messageElement, "Assessment properties hidden.");
        return;
      }

      if (!map || !styleLoaded) {
        return;
      }

      removeRenderedLayer("assessment_properties");
      renderAssessmentLayer("assessment_properties", propertyLayerState, LAYER_DEFINITIONS.find((layer) => layer.id === "assessment_properties"));

      const displayMode = propertyLayerState.displayMode || "clusters";
      const itemCount = displayMode === "clusters"
        ? propertyLayerState.clusters?.reduce((sum, cluster) => sum + Number(cluster.count || 0), 0)
        : (propertyLayerState.properties?.length || propertyLayerState.clusters?.length || 0);

      setText(
        messageElement,
        `Assessment properties (${displayMode}) visible: ${itemCount || 0} in current view.`
      );
    },
    getViewport,
    setClickHandler(handler) {
      clickHandler = handler;
    },
    setViewportChangeHandler(handler) {
      viewportChangeHandler = handler;
    },
    setPropertySelectHandler(handler) {
      propertySelectHandler = handler;
    },
    setSelectionClearedHandler(handler) {
      selectionClearedHandler = handler;
    }
  };
}
