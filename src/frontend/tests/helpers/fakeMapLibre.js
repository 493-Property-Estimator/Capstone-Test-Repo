class FakeSource {
  constructor(definition) {
    this.definition = { ...definition };
    this.data = definition.data;
  }

  setData(data) {
    this.data = data;
  }
}

export class FakePopup {
  constructor(options = {}) {
    this.options = options;
    this.text = "";
    this.html = "";
    this.lngLat = null;
    this.map = null;
    this.removed = false;
  }

  setText(text) {
    this.text = text;
    return this;
  }

  setHTML(html) {
    this.html = html;
    return this;
  }

  setLngLat(lngLat) {
    this.lngLat = lngLat;
    return this;
  }

  addTo(map) {
    this.map = map;
    map.popups.push(this);
    return this;
  }

  remove() {
    this.removed = true;
    return this;
  }
}

export class FakeMarker {
  constructor(options = {}) {
    this.options = options;
    this.lngLat = null;
    this.map = null;
    this.popup = null;
    this.removed = false;
  }

  setLngLat(lngLat) {
    this.lngLat = lngLat;
    return this;
  }

  addTo(map) {
    this.map = map;
    map.markers.push(this);
    return this;
  }

  setPopup(popup) {
    this.popup = popup;
    return this;
  }

  remove() {
    this.removed = true;
    return this;
  }
}

export class FakeMap {
  constructor(options = {}) {
    this.options = options;
    this.controls = [];
    this.layers = new Map();
    this.sources = new Map();
    this.events = new Map();
    this.canvas = { style: {} };
    this.markers = [];
    this.popups = [];
    this.center = options.center || [-113.4938, 53.5461];
    this.zoom = options.zoom ?? 11;
    const maxBounds = options.maxBounds || [[-113.7134, 53.3385], [-113.2784, 53.7152]];
    this.bounds = {
      west: maxBounds[0][0],
      south: maxBounds[0][1],
      east: maxBounds[1][0],
      north: maxBounds[1][1]
    };
    this.loaded = FakeMap.autoLoad;
    FakeMap.instances.push(this);
  }

  addControl(control, position) {
    this.controls.push({ control, position });
  }

  on(eventName, layerOrHandler, maybeHandler) {
    const key = typeof layerOrHandler === "string" ? `${eventName}:${layerOrHandler}` : eventName;
    const handler = typeof layerOrHandler === "string" ? maybeHandler : layerOrHandler;
    if (!this.events.has(key)) {
      this.events.set(key, []);
    }
    this.events.get(key).push(handler);
    if (eventName === "load" && this.loaded && typeof handler === "function") {
      handler();
    }
  }

  emit(eventName, payload = {}, layerId = null) {
    const keys = [eventName];
    if (layerId) {
      keys.unshift(`${eventName}:${layerId}`);
    }
    keys.forEach((key) => {
      (this.events.get(key) || []).forEach((handler) => handler(payload));
    });
  }

  addSource(id, definition) {
    this.sources.set(id, new FakeSource(definition));
  }

  getSource(id) {
    return this.sources.get(id) || null;
  }

  removeSource(id) {
    this.sources.delete(id);
  }

  addLayer(layer) {
    this.layers.set(layer.id, { ...layer });
  }

  getLayer(id) {
    return this.layers.get(id) || null;
  }

  removeLayer(id) {
    this.layers.delete(id);
  }

  getCanvas() {
    return this.canvas;
  }

  easeTo(options = {}) {
    this.center = options.center || this.center;
    this.lastEaseTo = options;
  }

  flyTo(options = {}) {
    this.center = options.center || this.center;
    if (typeof options.zoom === "number") {
      this.zoom = options.zoom;
    }
    this.lastFlyTo = options;
  }

  fitBounds(bounds, options = {}) {
    this.bounds = {
      west: bounds[0][1],
      south: bounds[0][0],
      east: bounds[1][1],
      north: bounds[1][0]
    };
    this.lastFitBounds = { bounds, options };
  }

  getBounds() {
    return {
      getWest: () => this.bounds.west,
      getSouth: () => this.bounds.south,
      getEast: () => this.bounds.east,
      getNorth: () => this.bounds.north
    };
  }

  getZoom() {
    return this.zoom;
  }

  queryRenderedFeatures(_geometry, options = {}) {
    const targetLayers = new Set(options.layers || []);
    const features = [];

    targetLayers.forEach((layerId) => {
      const layer = this.layers.get(layerId);
      const source = layer?.source ? this.sources.get(layer.source) : null;
      const sourceFeatures = source?.data?.features || [];
      sourceFeatures.forEach((feature) => {
        if (layerId.includes("assessment_properties-points")) {
          if (!feature?.properties?.point_count) {
            features.push(feature);
          }
          return;
        }

        features.push(feature);
      });
    });

    return features;
  }
}

FakeMap.instances = [];
FakeMap.autoLoad = true;

export class FakeNavigationControl {}

export function installMapLibre(windowObject) {
  windowObject.maplibregl = {
    Map: FakeMap,
    Marker: FakeMarker,
    Popup: FakePopup,
    NavigationControl: FakeNavigationControl
  };

  return windowObject.maplibregl;
}

export function latestMapInstance() {
  return FakeMap.instances[FakeMap.instances.length - 1] || null;
}
