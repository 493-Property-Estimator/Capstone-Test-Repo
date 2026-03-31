import { setText } from "../../utils/dom.js";

export function createMapSelectionController({
  apiClient,
  store,
  mapAdapter,
  mapMessageElement
}) {
  return async function handleMapClick(coordinates) {
    const clickId = `click-${Date.now()}`;
    store.setState({ latestClickId: clickId });
    setText(mapMessageElement, "Resolving clicked location...");

    try {
      const response = await apiClient.resolveMapClick({
        click_id: clickId,
        coordinates,
        timestamp: new Date().toISOString()
      });

      if (response.status === "resolved" && response.location) {
        store.setState({ selectedLocation: response.location });
        mapAdapter.setView(response.location, {
          preserveZoom: true,
          panOnly: true
        });
        return;
      }

      if (response.status === "outside_supported_area") {
        setText(
          mapMessageElement,
          "Location is outside the supported area. Click within Edmonton."
        );
        return;
      }

      setText(
        mapMessageElement,
        "Location could not be determined from the click. Click again to retry."
      );
    } catch (error) {
      setText(mapMessageElement, "Map click resolution unavailable.");
    }
  };
}
