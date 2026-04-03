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
<<<<<<< HEAD:src/frontend/src/map/mapAdapter.js
  onSelectionCleared
}) {
  let clickHandler = onMapClick;
  let viewportChangeHandler = onViewportChange;
  let selectionClearedHandler = onSelectionCleared;
  let marker = null;
  let layerContainer = null;
=======
  propertyCardElement
}) {
  let clickHandler = onMapClick;
  let viewportChangeHandler = onViewportChange;
>>>>>>> master:frontend/src/map/mapAdapter.js
  let map = null;
  let mapCanvas = null;
  let marker = null;
  let markerPopup = null;
  let layerContainer = null;
  let lastActiveLayers = null;
  let propertyCardAnimationFrame = null;
  let pointerDownPoint = null;
  let mapWasDragged = false;
  let suppressNextMapClick = false;
  let styleLoaded = false;

  const renderedLayerIds = new Map();
  const interactionRegistry = new Set();

  function createSelectedMarkerElement() {
    const element = document.createElement("span");
    element.className = "selected-property-marker";
    return element;
  }

  function positionPropertyCard(clientX, clientY) {
    if (!propertyCardElement) {
      return;
    }

    const rootRect = root.getBoundingClientRect();
    const cardRect = propertyCardElement.getBoundingClientRect();
    const offset = 18;
    const maxLeft = Math.max(12, rootRect.width - cardRect.width - 12);
    const maxTop = Math.max(12, rootRect.height - cardRect.height - 12);
    const nextLeft = Math.min(
      maxLeft,
      Math.max(12, clientX - rootRect.left + offset)
    );
    const nextTop = Math.min(
      maxTop,
      Math.max(12, clientY - rootRect.top + offset)
    );

    propertyCardElement.style.left = `${nextLeft}px`;
    propertyCardElement.style.top = `${nextTop}px`;
  }

  function updatePropertyCardPosition(event) {
    const originalEvent = event?.originalEvent;

    if (!propertyCardElement || !originalEvent) {
      return;
    }

    if (propertyCardAnimationFrame) {
      window.cancelAnimationFrame(propertyCardAnimationFrame);
    }

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

    const description = properties.description || "";
    const parts = description.split(" | ");

    propertyCardElement.innerHTML = `
      <p class="eyebrow">Property Card</p>
      <h3>${properties.name || "Selected property"}</h3>
      <p class="property-card-copy">${properties.address || "Edmonton property"}</p>
      <div class="property-card-metric">
        <div class="property-card-chip">
          <span>Assessment</span>
          <strong>${parts[0]?.replace("Assessment: ", "") || "--"}</strong>
        </div>
        <div class="property-card-chip">
          <span>Neighbourhood</span>
          <strong>${parts[1]?.replace("Neighbourhood: ", "") || "--"}</strong>
        </div>
        <div class="property-card-chip">
          <span>Ward</span>
          <strong>${parts[2]?.replace("Ward: ", "") || "--"}</strong>
        </div>
        <div class="property-card-chip">
          <span>Tax Class</span>
          <strong>${parts[3]?.replace("Tax class: ", "") || "--"}</strong>
        </div>
      </div>
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

    map.on("click", (event) => {
      if (suppressNextMapClick) {
        suppressNextMapClick = false;
        return;
      }

      const movedDistance = pointerDownPoint
        ? Math.hypot(
            event.originalEvent.clientX - pointerDownPoint.x,
            event.originalEvent.clientY - pointerDownPoint.y
          )
        : 0;

      if (mapWasDragged || movedDistance > 8) {
        pointerDownPoint = null;
        mapWasDragged = false;
        return;
      }

      clickHandler({
        lat: Number(event.lngLat.lat.toFixed(5)),
        lng: Number(event.lngLat.lng.toFixed(5))
      });

      pointerDownPoint = null;
      mapWasDragged = false;
    });

    const debouncedViewportChange = debounce(() => {
      if (viewportChangeHandler) {
        viewportChangeHandler(getViewport());
      }
    }, 120);

    map.on("moveend", debouncedViewportChange);
    map.on("zoomend", debouncedViewportChange);
  }

  function buildPopupHtml(properties = {}) {
    return [properties.name, properties.address, properties.description]
      .filter(Boolean)
      .join("<br />");
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
    if (!map) {
      return;
    }

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

<<<<<<< HEAD:src/frontend/src/map/mapAdapter.js
    marker.bindPopup(location.canonical_address || "Selected property");
    marker.off("click");
    marker.on("click", () => marker.openPopup());
    marker.off("contextmenu");
    marker.on("contextmenu", () => {
      clearSelection();
      if (selectionClearedHandler) {
        selectionClearedHandler();
      }
    });
=======
    markerPopup.setText(location.canonical_address || "Selected property");
    marker.setPopup(markerPopup);
>>>>>>> master:frontend/src/map/mapAdapter.js
  }

  function setView(location, options = {}) {
    if (!map) {
      return;
    }

    const {
      zoom = 15,
      preserveZoom = false,
      animate = true,
      panOnly = false
    } = options;

    renderMarker(location);
<<<<<<< HEAD:src/frontend/src/map/mapAdapter.js
    map.flyTo([location.coordinates.lat, location.coordinates.lng], 15, {
      duration: 0.8
    });
    marker.openPopup();
=======

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

>>>>>>> master:frontend/src/map/mapAdapter.js
    setText(
      messageElement,
      `Viewing ${location.canonical_address || "selected property"}`
    );
  }

<<<<<<< HEAD:src/frontend/src/map/mapAdapter.js
  function clearSelection() {
    if (map && marker) {
      map.removeLayer(marker);
      marker = null;
    }
    setText(messageElement, "Selection cleared.");
  }

  function focusEdmonton() {
    if (!map) {
      return;
    }
    map.fitBounds(EDMONTON_BOUNDS, {
      padding: [24, 24]
    });
    setText(messageElement, "Viewing Edmonton.");
  }

  function renderLayers(activeLayers) {
=======
  function resetView() {
>>>>>>> master:frontend/src/map/mapAdapter.js
    if (!map) {
      return;
    }

    if (marker) {
      marker.remove();
      marker = null;
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
    if (!map || !styleLoaded) {
      return;
    }

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

  function registerAssessmentInteractions(layerId) {
    const clusterLayerId = `${layerId}-cluster-circle`;
    const clusterCountLayerId = `${layerId}-cluster-count`;
    const pointLayerId = `${layerId}-points`;
    const sourceId = `source-${layerId}`;

    if (!interactionRegistry.has(clusterLayerId)) {
      interactionRegistry.add(clusterLayerId);

      const handleClusterClick = (event) => {
        suppressNextMapClick = true;
        const feature = event.features?.[0];

        if (!feature) {
          return;
        }

        map.easeTo({
          center: feature.geometry.coordinates,
          zoom: Math.min(map.getZoom() + 2, 18)
        });
      };

      map.on("click", clusterLayerId, handleClusterClick);
      map.on("click", clusterCountLayerId, handleClusterClick);

      map.on("mouseenter", clusterLayerId, () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseenter", clusterCountLayerId, () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", clusterLayerId, () => {
        map.getCanvas().style.cursor = "";
      });
      map.on("mouseleave", clusterCountLayerId, () => {
        map.getCanvas().style.cursor = "";
      });
    }

    if (!interactionRegistry.has(pointLayerId)) {
      interactionRegistry.add(pointLayerId);

      map.on("mousemove", pointLayerId, (event) => {
        map.getCanvas().style.cursor = "pointer";
        renderPropertyCard(event.features?.[0]?.properties || null, event);
      });

      map.on("mouseleave", pointLayerId, () => {
        map.getCanvas().style.cursor = "";
        renderPropertyCard();
      });
    }
  }

  function renderAssessmentLayer(layerId, data, definition) {
    const sourceId = `source-${layerId}`;
    const features =
      data.renderMode === "property"
        ? (data.properties || []).map((property) => ({
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [property.coordinates.lng, property.coordinates.lat]
            },
            properties: {
              canonical_location_id: property.canonical_location_id,
              name: property.name || property.canonical_address,
              address: property.canonical_address,
              description:
                property.description ||
                `Assessment: $${Number(property.assessment_value || 0).toLocaleString()} | Neighbourhood: ${property.neighbourhood || "--"} | Ward: ${property.ward || "--"} | Tax class: ${property.tax_class || "--"}`
            }
          }))
        : (data.clusters || []).map((cluster) => ({
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [cluster.center.lng, cluster.center.lat]
            },
            properties: {
              cluster: true,
              cluster_id: cluster.cluster_id,
              point_count: cluster.count,
              point_count_abbreviated: String(cluster.count)
            }
          }));

    upsertSource(sourceId, { features });

    const clusterLayerId = `${layerId}-cluster-circle`;
    const clusterCountLayerId = `${layerId}-cluster-count`;
    const pointLayerId = `${layerId}-points`;

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
            "#b64949",
            15,
            "#a43434",
            60,
            "#8b2323"
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
    }

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

    if (!map.getLayer(pointLayerId)) {
      map.addLayer({
        id: pointLayerId,
        type: "circle",
        source: sourceId,
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": definition?.color || "#a43434",
          "circle-radius": 4,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.2
        }
      });
    }

    registerAssessmentInteractions(layerId);
    renderedLayerIds.set(layerId, [clusterLayerId, clusterCountLayerId, pointLayerId]);
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

    upsertSource(sourceId, layerState.data);

    const fillLayerId = `${layerId}-fill`;
    const lineLayerId = `${layerId}-line`;
    const pointLayerId = `${layerId}-points`;
    const rendered = [];

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
          "fill-color": definition?.color || "#666666",
          "fill-opacity": 0.18
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
          "line-color": definition?.color || "#666666",
          "line-width": 2
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
          "circle-color": definition?.color || "#666666",
          "circle-radius": 6,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5
        }
      });
    }
    rendered.push(pointLayerId);

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

      renderGenericLayer(layerId, layerState, definition);

      const chip = createElement("div", "map-layer-chip");
      const swatch = createElement("span", "legend-swatch");
      swatch.style.background =
        layerState.data?.legend?.items?.[0]?.color || definition?.color || "#666";
      const label = createElement(
        "span",
        null,
        `${definition?.label || layerId} · ${layerState.status || "loaded"}`
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
    renderPropertyLayer(propertyLayer) {
      if (!map || !styleLoaded) {
        return;
      }

      const definition = LAYER_DEFINITIONS.find((layer) => layer.id === "assessment_properties");

      if (!propertyLayer?.enabled) {
        removeRenderedLayer("assessment_properties");
        return;
      }

      const totalVisible =
        propertyLayer.renderMode === "property"
          ? (propertyLayer.properties || []).length
          : (propertyLayer.clusters || []).reduce(
              (sum, cluster) => sum + Number(cluster.count || 0),
              0
            );

      if (
        !(propertyLayer.clusters || []).length &&
        !(propertyLayer.properties || []).length
      ) {
        removeRenderedLayer("assessment_properties");
        return;
      }

      renderAssessmentLayer("assessment_properties", propertyLayer, definition);
      setText(
        messageElement,
        `Assessment properties visible: ${totalVisible.toLocaleString()} in current view.`
      );
    },
    setClickHandler(handler) {
      clickHandler = handler;
    },
    setViewportChangeHandler(handler) {
      viewportChangeHandler = handler;
    },
<<<<<<< HEAD:src/frontend/src/map/mapAdapter.js
    setSelectionClearedHandler(handler) {
      selectionClearedHandler = handler;
    },
    getViewport() {
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
=======
    rerenderPropertyLayer(activeLayers) {
      renderLayers(activeLayers);
    },
    getViewport
>>>>>>> master:frontend/src/map/mapAdapter.js
  };
}
