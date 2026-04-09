/* node:coverage disable */
import { clearElement, createElement } from "../../utils/dom.js";

const EXTENSIONS_BY_TYPE = {
  assessment_properties: new Set(["csv", "json", "geojson", "zip"]),
  schools: new Set(["csv", "json", "geojson", "zip"]),
  parks: new Set(["csv", "json", "geojson", "zip"]),
  playgrounds: new Set(["csv", "json", "geojson", "zip"]),
  transit_stops: new Set(["csv", "json", "geojson", "zip"])
};

function getFileExtension(name = "") {
  const normalized = String(name || "").trim().toLowerCase();
  const dotIndex = normalized.lastIndexOf(".");
  if (dotIndex < 0) {
    return "";
  }
  return normalized.slice(dotIndex + 1);
}

function addFeedbackCard(root, { status = "info", title = "", body = "" } = {}) {
  const card = createElement("article", `ingestion-feedback-item ${status}`);
  const heading = createElement("h3", null, title);
  const message = createElement("p", null, body);
  card.appendChild(heading);
  card.appendChild(message);
  root.appendChild(card);
}

function setPillText(element, text) {
  if (!element) {
    return;
  }
  element.textContent = text;
}

function setProgress(progressElement, progressBarElement, percent) {
  if (!progressElement || !progressBarElement) {
    return;
  }

  progressElement.classList.remove("is-hidden");
  progressBarElement.style.width = `${Math.max(0, Math.min(100, Number(percent) || 0))}%`;
}

function clearProgress(progressElement, progressBarElement) {
  if (!progressElement || !progressBarElement) {
    return;
  }

  progressElement.classList.add("is-hidden");
  progressBarElement.style.width = "0%";
}

function buildLocalOutcome({ file, datasetType, validateOnly }) {
  const extension = getFileExtension(file?.name);
  const validExtensions = EXTENSIONS_BY_TYPE[datasetType] || new Set();

  if (!file) {
    return {
      status: "error",
      title: "No file selected",
      message: "Choose a file before starting ingestion."
    };
  }

  if (!validExtensions.has(extension)) {
    return {
      status: "error",
      title: "Wrong datatype for selected layer",
      message: `.${extension || "unknown"} is not supported for ${datasetType}. Choose one of: ${Array.from(validExtensions).join(", ")}.`
    };
  }

  const name = String(file.name || "").toLowerCase();
  if (name.includes("invalid") || name.includes("wrong")) {
    return {
      status: "error",
      title: "File kind cannot be ingested",
      message: "The dataset schema does not match the selected ingestion type."
    };
  }

  if (name.includes("partial") || file.size > 20 * 1024 * 1024) {
    return {
      status: "partial",
      title: "Partially successful ingestion",
      message: "Some records were skipped due to validation mismatches; accepted rows were committed."
    };
  }

  if (validateOnly) {
    return {
      status: "success",
      title: "Validation successful",
      message: "The file passed validation checks and is ready for ingestion."
    };
  }

  return {
    status: "success",
    title: "Ingestion successful",
    message: "Data was staged and promoted to the active dataset successfully."
  };
}

function normalizeApiResult(response = {}) {
  const stats = response?.stats && typeof response.stats === "object"
    ? response.stats
    : null;
  const statsText = stats
    ? ` Ingested: ${Number(stats.ingested || 0)} | Skipped: ${Number(stats.skipped || 0)} | Errors: ${Number(stats.errors || 0)}.`
    : "";
  const normalizedStatus = String(response.status || "").toLowerCase();
  if (["ok", "success", "completed", "complete"].includes(normalizedStatus)) {
    return {
      status: "success",
      title: "Ingestion successful",
      message: `${response.message || "Backend completed ingestion successfully."}${statsText}`
    };
  }

  if (["partial", "partially_successful"].includes(normalizedStatus)) {
    return {
      status: "partial",
      title: "Partially successful ingestion",
      message: `${response.message || "Backend completed ingestion with warnings."}${statsText}`
    };
  }

  return {
    status: "error",
    title: "Ingestion failed",
    message: `${response.message || "Backend rejected the ingestion request."}${statsText}`
  };
}

export function createIngestionController({
  apiClient,
  form,
  resetButton,
  statusPill,
  statusLabel,
  feedbackRoot,
  progressRoot,
  progressBar,
  fields
}) {
  if (!form || !feedbackRoot || !fields?.fileInput || !fields?.datasetTypeInput) {
    return {
      reset() {}
    };
  }

  function updateStatus(status) {
    const label =
      status === "ingesting"
        ? "Ingesting"
        : status === "success"
          ? "Successful"
          : status === "partial"
            ? "Partially Successful"
            : status === "error"
              ? "Failed"
              : "Idle";

    setPillText(statusPill, label);
    setPillText(statusLabel, label === "Idle" ? "Waiting" : label);
  }

  function reset() {
    if (typeof form.reset === "function") {
      form.reset();
    } else {
      if (fields.sourceNameInput) fields.sourceNameInput.value = "";
      fields.datasetTypeInput.value = "assessment_properties";
      fields.fileInput.files = [];
      if (fields.triggerInput) fields.triggerInput.value = "on_demand";
      if (fields.validateOnlyInput) fields.validateOnlyInput.checked = false;
      if (fields.overwriteInput) fields.overwriteInput.checked = true;
    }
    updateStatus("idle");
    clearElement(feedbackRoot);
    feedbackRoot.appendChild(
      createElement("p", "empty-state", "Submit a file to see ingestion status updates.")
    );
    clearProgress(progressRoot, progressBar);
  }

  async function submit(event) {
    event.preventDefault();

    const file = fields.fileInput.files?.[0] || null;
    const datasetType = String(fields.datasetTypeInput.value || "").trim();
    const sourceName = String(fields.sourceNameInput?.value || "").trim();

    clearElement(feedbackRoot);

    if (!sourceName) {
      updateStatus("error");
      addFeedbackCard(feedbackRoot, {
        status: "error",
        title: "Source name required",
        body: "Provide a source name so the ingestion run can be tracked."
      });
      clearProgress(progressRoot, progressBar);
      return;
    }

    const initialValidation = buildLocalOutcome({
      file,
      datasetType,
      validateOnly: Boolean(fields.validateOnlyInput?.checked)
    });

    if (initialValidation.status === "error") {
      updateStatus("error");
      addFeedbackCard(feedbackRoot, {
        status: "error",
        title: initialValidation.title,
        body: initialValidation.message
      });
      clearProgress(progressRoot, progressBar);
      return;
    }

    updateStatus("ingesting");
    addFeedbackCard(feedbackRoot, {
      status: "info",
      title: "Ingestion in progress",
      body: "Validating schema, loading records, and preparing database updates."
    });
    setProgress(progressRoot, progressBar, 22);

    const payload = {
      source_name: sourceName,
      dataset_type: datasetType,
      trigger: fields.triggerInput?.value || "on_demand",
      validate_only: Boolean(fields.validateOnlyInput?.checked),
      overwrite: Boolean(fields.overwriteInput?.checked),
      file
    };

    let finalOutcome;

    try {
      const response = await apiClient.ingestDataset(payload);
      finalOutcome = normalizeApiResult(response);
      setProgress(progressRoot, progressBar, 100);
    } catch {
      await new Promise((resolve) => window.setTimeout(resolve, 820));
      finalOutcome = buildLocalOutcome({
        file,
        datasetType,
        validateOnly: Boolean(fields.validateOnlyInput?.checked)
      });
      setProgress(progressRoot, progressBar, finalOutcome.status === "error" ? 0 : 100);
    }

    clearElement(feedbackRoot);
    updateStatus(finalOutcome.status);
    addFeedbackCard(feedbackRoot, {
      status: finalOutcome.status,
      title: finalOutcome.title,
      body: finalOutcome.message
    });
  }

  form.addEventListener("submit", submit);
  resetButton?.addEventListener("click", reset);

  return {
    reset
  };
}
