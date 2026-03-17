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
  messageElement
}) {
  let clickHandler = onMapClick;
  let viewportChangeHandler = onViewportChange;
  let marker = null;
  let layerContainer = null;
  let map = null;
  const layerInstances = {};
  let pointerDownLatLng = null;
  let mapWasDragged = false;

  function renderBase() {
    clearElement(root);

    layerContainer = createElement("div", "map-layer-container");
    root.appendChild(layerContainer);

    if (!window.L) {
      setText(messageElement, "Leaflet failed to load.");
      return;
    }

    map = window.L.map(root, {
      center: EDMONTON_CENTER,
      zoom: 11,
      minZoom: 10,
      maxZoom: 18,
      maxBounds: EDMONTON_BOUNDS,
      maxBoundsViscosity: 0.8,
      zoomControl: true
    });

    window.L.tileLayer(OSM_TILE_URL, {
      attribution: OSM_ATTRIBUTION
    }).addTo(map);

    map.on("mousedown", (event) => {
      pointerDownLatLng = event.latlng;
      mapWasDragged = false;
    });

    map.on("dragstart", () => {
      mapWasDragged = true;
    });

    map.on("click", (event) => {
      const movedDistance =
        pointerDownLatLng && typeof pointerDownLatLng.distanceTo === "function"
          ? pointerDownLatLng.distanceTo(event.latlng)
          : 0;

      if (mapWasDragged || movedDistance > 8) {
        pointerDownLatLng = null;
        mapWasDragged = false;
        return;
      }

      clickHandler({
        lat: Number(event.latlng.lat.toFixed(5)),
        lng: Number(event.latlng.lng.toFixed(5))
      });

      pointerDownLatLng = null;
      mapWasDragged = false;
    });

    const debouncedViewportChange = debounce(() => {
      if (viewportChangeHandler) {
        viewportChangeHandler(getViewport());
      }
    }, 250);

    map.on("moveend zoomend", debouncedViewportChange);
    debouncedViewportChange();
  }

  function renderMarker(location) {
    if (!map) {
      return;
    }

    if (!marker) {
      marker = window.L.marker([
        location.coordinates.lat,
        location.coordinates.lng
      ]).addTo(map);
    } else {
      marker.setLatLng([location.coordinates.lat, location.coordinates.lng]);
    }

    marker.bindPopup(location.canonical_address || "Selected property");
  }

  function setView(location) {
    if (!map) {
      return;
    }

    renderMarker(location);
    map.flyTo([location.coordinates.lat, location.coordinates.lng], 15, {
      duration: 0.8
    });
    setText(
      messageElement,
      `Viewing ${location.canonical_address || "selected property"}`
    );
  }

  function renderLayers(activeLayers) {
    if (!map) {
      return;
    }

    clearElement(layerContainer);

    Object.entries(activeLayers).forEach(([layerId, layerState]) => {
      const definition = LAYER_DEFINITIONS.find((layer) => layer.id === layerId);

      if (!layerState.enabled) {
        if (layerInstances[layerId]) {
          map.removeLayer(layerInstances[layerId]);
          delete layerInstances[layerId];
        }
        return;
      }

      if (layerInstances[layerId]) {
        map.removeLayer(layerInstances[layerId]);
        delete layerInstances[layerId];
      }

      if (layerState.data?.features?.length) {
        layerInstances[layerId] = window.L.geoJSON(layerState.data.features, {
          pointToLayer(feature, latlng) {
            return window.L.circleMarker(latlng, {
              radius: 6,
              color: definition?.color || "#666",
              weight: 2,
              fillColor: definition?.color || "#666",
              fillOpacity: 0.65
            });
          },
          style() {
            return {
              color: definition?.color || "#666",
              weight: 2,
              fillOpacity: 0.2
            };
          },
          onEachFeature(feature, layer) {
            const properties = feature.properties || {};
            const popupText = [
              properties.name,
              properties.address,
              properties.description
            ]
              .filter(Boolean)
              .join("<br />");

            if (popupText) {
              layer.bindPopup(popupText);
            }
          }
        }).addTo(map);
      }

      if (!layerState.enabled) {
        return;
      }

      if (!layerState.enabled) {
        return;
      }

      const chip = createElement("div", "map-layer-chip");
      const swatch = createElement("span", "legend-swatch");
      swatch.style.background =
        layerState.data?.legend?.items?.[0]?.color || definition?.color || "#666";
      const label = createElement(
        "span",
        null,
        `${layerId} · ${layerState.status || "loaded"}`
      );
      chip.appendChild(swatch);
      chip.appendChild(label);
      layerContainer.appendChild(chip);
    });
  }

  root.addEventListener("click", (event) => {
    const rect = root.getBoundingClientRect();
    const xRatio = (event.clientX - rect.left) / rect.width;
    const yRatio = (event.clientY - rect.top) / rect.height;
    const lng = bounds.west + xRatio * (bounds.east - bounds.west);
    const lat = bounds.north - yRatio * (bounds.north - bounds.south);

    clickHandler({
      lat: Number(lat.toFixed(5)),
      lng: Number(lng.toFixed(5))
    });
  });

  renderBase();

  return {
    setView,
    renderLayers,
    setClickHandler(handler) {
      clickHandler = handler;
    },
    setViewportChangeHandler(handler) {
      viewportChangeHandler = handler;
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
  };
}
