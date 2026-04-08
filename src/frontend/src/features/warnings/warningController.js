import { clearElement, createElement, toggleHidden } from "../../utils/dom.js";

export function createWarningController({
  store,
  warningPanel,
  warningIndicator
}) {
  function renderWarnings() {
    clearElement(warningPanel);
    toggleHidden(warningPanel, true);
    toggleHidden(warningIndicator, true);
  }

  store.subscribe((state) => {
    renderWarnings(state.estimate);
  });
}
