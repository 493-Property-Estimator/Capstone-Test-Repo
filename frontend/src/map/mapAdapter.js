import { createElement, clearElement, setText } from "../utils/dom.js";

export function createMapAdapter({ root, onMapClick, messageElement }) {
  let clickHandler = onMapClick;
  let marker = null;
  let layerContainer = null;
  let overlay = null;
  let bounds = {
    west: -113.7136,
    south: 53.3958,
    east: -113.2714,
    north: 53.716
  };
  let zoom = 11;

  function renderBase() {
    clearElement(root);

    overlay = createElement("div", "map-overlay-copy");
    overlay.innerHTML = `
      <p class="eyebrow">Map Adapter</p>
      <h3>OpenStreetMap placeholder</h3>
      <p class="feature-summary">
        Replace this adapter with Leaflet or another OpenStreetMap renderer.
        The rest of the frontend modules can stay unchanged.
      </p>
    `;

    layerContainer = createElement("div", "map-layer-container");
    layerContainer.style.position = "absolute";
    layerContainer.style.right = "18px";
    layerContainer.style.bottom = "18px";
    layerContainer.style.maxWidth = "340px";

    root.appendChild(overlay);
    root.appendChild(layerContainer);
  }

  function toViewportPosition(lat, lng) {
    const xRatio = (lng - bounds.west) / (bounds.east - bounds.west);
    const yRatio = 1 - (lat - bounds.south) / (bounds.north - bounds.south);

    return {
      x: Math.min(Math.max(xRatio * root.clientWidth, 20), root.clientWidth - 20),
      y: Math.min(Math.max(yRatio * root.clientHeight, 20), root.clientHeight - 20)
    };
  }

  function renderMarker(location) {
    if (marker) {
      marker.remove();
    }

    const position = toViewportPosition(
      location.coordinates.lat,
      location.coordinates.lng
    );

    marker = createElement("div", "map-pin");
    marker.style.left = `${position.x}px`;
    marker.style.top = `${position.y}px`;
    marker.title = location.canonical_address || "Selected property";
    root.appendChild(marker);
  }

  function setView(location) {
    renderMarker(location);
    setText(
      messageElement,
      `Viewing ${location.canonical_address || "selected property"}`
    );
  }

  function renderLayers(activeLayers) {
    clearElement(layerContainer);

    Object.entries(activeLayers).forEach(([layerId, layerState]) => {
      if (!layerState.enabled) {
        return;
      }

      const chip = createElement("div", "map-layer-chip");
      const swatch = createElement("span", "legend-swatch");
      swatch.style.background = layerState.data?.legend?.items?.[0]?.color || "#666";
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
    getViewport() {
      return { ...bounds, zoom };
    }
  };
}
