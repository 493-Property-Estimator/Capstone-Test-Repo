import { clearElement, createElement, toggleHidden } from "../../utils/dom.js";

export function createWarningController({
  store,
  warningPanel,
  warningIndicator
}) {
  function renderWarnings(estimate) {
    clearElement(warningPanel);

    const warnings = estimate?.warnings || [];
    const confidence = estimate?.confidence;

    if (!warnings.length && !confidence) {
      toggleHidden(warningPanel, true);
      toggleHidden(warningIndicator, true);
      return;
    }

    toggleHidden(warningPanel, store.getState().warningsCollapsed);

    if (store.getState().warningsCollapsed) {
      warningIndicator.textContent = "Warnings hidden. Reopen warning details.";
      toggleHidden(warningIndicator, false);
    } else {
      toggleHidden(warningIndicator, true);
    }

    if (confidence) {
      const confidenceCard = createElement("article", "warning-item info");
      confidenceCard.appendChild(
        createElement(
          "h3",
          null,
          `Confidence: ${confidence.percentage ?? "--"}%${confidence.label ? ` · ${confidence.label}` : ""}`
        )
      );
      confidenceCard.appendChild(
        createElement(
          "p",
          "warning-body",
          `Estimate completeness: ${confidence.completeness || "unknown"}.`
        )
      );
      warningPanel.appendChild(confidenceCard);
    }

    warnings.forEach((warning) => {
      const card = createElement("article", `warning-item ${warning.severity || "warning"}`);
      card.appendChild(createElement("h3", null, warning.title));
      card.appendChild(createElement("p", "warning-body", warning.message));

      if (warning.affected_factors?.length) {
        card.appendChild(
          createElement(
            "p",
            "factor-meta",
            `Affected factors: ${warning.affected_factors.join(", ")}`
          )
        );
      }

      if (warning.dismissible) {
        const actions = createElement("div", "warning-actions");
        const dismiss = createElement("button", "button button-secondary", "Dismiss");
        dismiss.type = "button";
        dismiss.addEventListener("click", () => {
          store.setState({ warningsCollapsed: true });
        });
        actions.appendChild(dismiss);
        card.appendChild(actions);
      }

      warningPanel.appendChild(card);
    });
  }

  warningIndicator.addEventListener("click", () => {
    store.setState({ warningsCollapsed: false });
  });

  store.subscribe((state) => {
    renderWarnings(state.estimate);
  });
}
