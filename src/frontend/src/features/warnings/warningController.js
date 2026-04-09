import { clearElement, createElement, toggleHidden } from "../../utils/dom.js";

export function createWarningController({
  store,
  warningPanel,
  warningIndicator
}) {
  function renderWarnings(estimate, warningsCollapsed) {
    clearElement(warningPanel);
    toggleHidden(warningPanel, true);
    if (warningIndicator) {
      toggleHidden(warningIndicator, true);
    }

    if (!estimate || !Array.isArray(estimate.warnings) || estimate.warnings.length === 0) {
      return;
    }

    toggleHidden(warningPanel, false);

    const details = createElement("details", "warning-details");
    details.open = !warningsCollapsed;

    const summary = createElement("summary", "warning-summary");
    const confidence = estimate.confidence || {};
    const confidenceLabel = confidence.label ? String(confidence.label) : "unknown";
    const confidencePct = confidence.percentage != null ? `${confidence.percentage}%` : "--";
    summary.appendChild(
      createElement("span", "warning-summary-title", `Warnings (${confidenceLabel}, ${confidencePct})`)
    );
    details.appendChild(summary);

    details.addEventListener("toggle", () => {
      const collapsed = !details.open;
      if (store.getState().warningsCollapsed !== collapsed) {
        store.setState({ warningsCollapsed: collapsed });
      }
    });

    const body = createElement("div", "warning-body");
    body.appendChild(
      createElement(
        "div",
        "warning-confidence",
        confidence.percentage != null ? `Confidence: ${confidencePct}` : "Confidence: --"
      )
    );

    const warning = estimate.warnings[0];
    const card = createElement("div", `warning-card ${warning.severity || ""}`.trim());
    card.appendChild(createElement("div", "warning-title", warning.title || "Warning"));
    card.appendChild(createElement("div", "warning-message", warning.message || ""));
    card.appendChild(
      createElement(
        "div",
        "warning-factors",
        Array.isArray(warning.affected_factors) && warning.affected_factors.length
          ? `Affected factors: ${warning.affected_factors.join(", ")}`
          : ""
      )
    );
    const actions = createElement("div", "warning-actions");
    if (warning.dismissible) {
      const dismiss = createElement("button", "warning-dismiss", "Dismiss");
      dismiss.addEventListener("click", () => {
        store.setState({ warningsCollapsed: true });
      });
      actions.appendChild(dismiss);
    }
    card.appendChild(actions);
    body.appendChild(card);

    details.appendChild(body);
    warningPanel.appendChild(details);
  }

  store.subscribe((state) => {
    renderWarnings(state.estimate, state.warningsCollapsed);
  });

  warningIndicator?.addEventListener("click", () => {
    if (store.getState().warningsCollapsed) {
      store.setState({ warningsCollapsed: false });
    }
  });
}
