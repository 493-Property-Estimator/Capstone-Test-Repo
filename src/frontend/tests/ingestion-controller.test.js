import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals } from "./helpers/fakeDom.js";

function buildController(apiClient) {
  const { document, window } = installDomGlobals();
  const form = document.createElement("form");
  const resetButton = document.createElement("button");
  const statusPill = document.createElement("span");
  const statusLabel = document.createElement("span");
  const feedbackRoot = document.createElement("div");
  const progressRoot = document.createElement("div");
  progressRoot.classList.add("is-hidden");
  const progressBar = document.createElement("div");

  const sourceNameInput = document.createElement("input");
  const datasetTypeInput = document.createElement("select");
  datasetTypeInput.value = "schools";
  const fileInput = document.createElement("input");
  const triggerInput = document.createElement("select");
  triggerInput.value = "on_demand";
  const validateOnlyInput = document.createElement("input");
  const overwriteInput = document.createElement("input");
  overwriteInput.checked = true;

  return import("../src/features/ingestion/ingestionController.js").then(({ createIngestionController }) => {
    const controller = createIngestionController({
      apiClient,
      form,
      resetButton,
      statusPill,
      statusLabel,
      feedbackRoot,
      progressRoot,
      progressBar,
      fields: {
        sourceNameInput,
        datasetTypeInput,
        fileInput,
        triggerInput,
        validateOnlyInput,
        overwriteInput,
      },
    });

    return {
      controller,
      window,
      form,
      resetButton,
      statusPill,
      statusLabel,
      feedbackRoot,
      progressRoot,
      progressBar,
      sourceNameInput,
      datasetTypeInput,
      fileInput,
      validateOnlyInput,
    };
  });
}

function submit(form) {
  form.dispatchEvent({ type: "submit", target: form });
}

test("ingestion controller handles validation errors and reset", async () => {
  const ctx = await buildController({
    async ingestDataset() {
      return { status: "success", message: "ok" };
    },
  });

  submit(ctx.form);
  assert.equal(ctx.statusPill.textContent, "Failed");
  assert.match(ctx.feedbackRoot.textContent, /Source name required/);

  ctx.sourceNameInput.value = "source-a";
  submit(ctx.form);
  assert.equal(ctx.statusPill.textContent, "Failed");
  assert.match(ctx.feedbackRoot.textContent, /No file selected/);

  ctx.fileInput.files = [{ name: "schools.txt", size: 100 }];
  submit(ctx.form);
  assert.equal(ctx.statusPill.textContent, "Failed");
  assert.match(ctx.feedbackRoot.textContent, /Wrong datatype/);

  ctx.form.reset = () => {};
  ctx.resetButton.click();
  assert.equal(ctx.statusPill.textContent, "Idle");
  assert.equal(ctx.statusLabel.textContent, "Waiting");
  assert.equal(ctx.progressRoot.classList.contains("is-hidden"), true);
  assert.match(ctx.feedbackRoot.textContent, /Submit a file/);
});

test("ingestion controller guard branches for missing elements", async () => {
  const { document } = installDomGlobals();
  const { createIngestionController } = await import("../src/features/ingestion/ingestionController.js");

  const minimal = createIngestionController({
    apiClient: { async ingestDataset() { return { status: "success" }; } },
    form: null,
    resetButton: null,
    statusPill: null,
    statusLabel: null,
    feedbackRoot: null,
    progressRoot: null,
    progressBar: null,
    fields: null,
  });
  assert.equal(typeof minimal.reset, "function");
  minimal.reset();

  const form = document.createElement("form");
  const resetButton = document.createElement("button");
  const feedbackRoot = document.createElement("div");
  const sourceNameInput = document.createElement("input");
  sourceNameInput.value = "src-x";
  const datasetTypeInput = document.createElement("select");
  datasetTypeInput.value = "schools";
  const fileInput = document.createElement("input");
  fileInput.files = [{ name: "schools.csv", size: 1 }];

  createIngestionController({
    apiClient: { async ingestDataset() { return { status: "success" }; } },
    form,
    resetButton,
    statusPill: null,
    statusLabel: null,
    feedbackRoot,
    progressRoot: null,
    progressBar: null,
    fields: {
      sourceNameInput,
      datasetTypeInput,
      fileInput,
      triggerInput: null,
      validateOnlyInput: null,
      overwriteInput: null,
    },
  });

  form.dispatchEvent({ type: "submit", target: form });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(feedbackRoot.textContent, /Ingestion successful/);

  const formNoReset = document.createElement("form");
  const resetNoReset = document.createElement("button");
  const feedbackNoReset = document.createElement("div");
  const sourceNoReset = document.createElement("input");
  sourceNoReset.value = "";
  const datasetNoReset = document.createElement("select");
  datasetNoReset.value = "schools";
  const fileNoReset = document.createElement("input");
  fileNoReset.files = [{ name: "schools.csv", size: 1 }];

  createIngestionController({
    apiClient: { async ingestDataset() { return { status: "success" }; } },
    form: formNoReset,
    resetButton: resetNoReset,
    statusPill: null,
    statusLabel: null,
    feedbackRoot: feedbackNoReset,
    progressRoot: null,
    progressBar: null,
    fields: {
      sourceNameInput: sourceNoReset,
      datasetTypeInput: datasetNoReset,
      fileInput: fileNoReset,
      triggerInput: null,
      validateOnlyInput: null,
      overwriteInput: null,
    },
  });

  resetNoReset.click();
  formNoReset.dispatchEvent({ type: "submit", target: formNoReset });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(feedbackNoReset.textContent, /Source name required/);
});

test("ingestion controller uses API result statuses", async () => {
  const responses = [
    { status: "success", message: "good", stats: { ingested: 9, skipped: 1, errors: 0 } },
    { status: "partial", message: "some", stats: { ingested: 3, skipped: 2, errors: 1 } },
    { status: "failed", message: "bad", stats: { ingested: 0, skipped: 0, errors: 4 } },
  ];

  const ctx = await buildController({
    async ingestDataset() {
      return responses.shift();
    },
  });

  ctx.sourceNameInput.value = "source-b";
  ctx.fileInput.files = [{ name: "schools.csv", size: 200 }];

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Successful");
  assert.match(ctx.feedbackRoot.textContent, /Ingestion successful/);
  assert.match(ctx.feedbackRoot.textContent, /Ingested: 9/);

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Partially Successful");
  assert.match(ctx.feedbackRoot.textContent, /Partially successful ingestion/);
  assert.match(ctx.feedbackRoot.textContent, /Skipped: 2/);

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Failed");
  assert.match(ctx.feedbackRoot.textContent, /Ingestion failed/);
  assert.match(ctx.feedbackRoot.textContent, /Errors: 4/);
});

test("ingestion controller fallback handles validate-only and partial files", async () => {
  const ctx = await buildController({
    async ingestDataset() {
      throw new Error("network");
    },
  });

  ctx.window.setTimeout = (fn) => {
    fn();
    return 1;
  };

  ctx.sourceNameInput.value = "source-c";
  ctx.validateOnlyInput.checked = true;
  ctx.fileInput.files = [{ name: "schools.csv", size: 200 }];

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Successful");
  assert.match(ctx.feedbackRoot.textContent, /Validation successful/);

  ctx.validateOnlyInput.checked = false;
  ctx.fileInput.files = [{ name: "schools_partial.csv", size: 500 }];

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Partially Successful");
  assert.match(ctx.feedbackRoot.textContent, /Partially successful ingestion/);

  ctx.fileInput.files = [{ name: "schools_wrong.csv", size: 500 }];
  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Failed");
  assert.match(ctx.feedbackRoot.textContent, /cannot be ingested/);
});

test("ingestion controller covers status aliases, missing stats, and extension fallback messaging", async () => {
  const responses = [
    { status: "OK", message: "All good" },
    { status: "partially_successful", message: "Warnings", stats: "not-an-object" },
    { status: "complete", message: "Done", stats: { ingested: 1, skipped: 0, errors: 0 } }
  ];

  const ctx = await buildController({
    async ingestDataset() {
      return responses.shift();
    },
  });

  ctx.sourceNameInput.value = "source-d";
  ctx.fileInput.files = [{ name: "schools.csv", size: 200 }];

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Successful");
  assert.match(ctx.feedbackRoot.textContent, /All good/);
  assert.equal(ctx.feedbackRoot.textContent.includes("Ingested:"), false);

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Partially Successful");
  assert.match(ctx.feedbackRoot.textContent, /Warnings/);
  assert.equal(ctx.feedbackRoot.textContent.includes("Skipped:"), false);

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Successful");
  assert.match(ctx.feedbackRoot.textContent, /Ingested: 1/);

  ctx.datasetTypeInput.value = "unknown_layer";
  ctx.fileInput.files = [{ name: "schools", size: 10 }];
  submit(ctx.form);
  assert.equal(ctx.statusPill.textContent, "Failed");
  assert.match(ctx.feedbackRoot.textContent, /\.unknown is not supported/);
});

test("ingestion controller fallback treats large files as partial ingestion", async () => {
  const ctx = await buildController({
    async ingestDataset() {
      throw new Error("network");
    },
  });

  ctx.window.setTimeout = (fn) => {
    fn();
    return 1;
  };

  ctx.sourceNameInput.value = "source-e";
  ctx.fileInput.files = [{ name: "schools.csv", size: 25 * 1024 * 1024 }];

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Partially Successful");
  assert.match(ctx.feedbackRoot.textContent, /Partially successful ingestion/);
});

test("ingestion controller reset fallback clears all fields when form.reset is absent", async () => {
  const { document } = installDomGlobals();
  const { createIngestionController } = await import("../src/features/ingestion/ingestionController.js");

  const form = document.createElement("form");
  const resetButton = document.createElement("button");
  const statusPill = document.createElement("span");
  const statusLabel = document.createElement("span");
  const feedbackRoot = document.createElement("div");
  const progressRoot = document.createElement("div");
  const progressBar = document.createElement("div");

  const sourceNameInput = document.createElement("input");
  sourceNameInput.value = "dirty";
  const datasetTypeInput = document.createElement("select");
  datasetTypeInput.value = "schools";
  const fileInput = document.createElement("input");
  fileInput.files = [{ name: "schools.csv", size: 1 }];
  const triggerInput = document.createElement("select");
  triggerInput.value = "scheduled";
  const validateOnlyInput = document.createElement("input");
  validateOnlyInput.checked = true;
  const overwriteInput = document.createElement("input");
  overwriteInput.checked = false;

  const controller = createIngestionController({
    apiClient: { async ingestDataset() { return { status: "success", message: "ok" }; } },
    form,
    resetButton,
    statusPill,
    statusLabel,
    feedbackRoot,
    progressRoot,
    progressBar,
    fields: {
      sourceNameInput,
      datasetTypeInput,
      fileInput,
      triggerInput,
      validateOnlyInput,
      overwriteInput,
    },
  });

  assert.equal(typeof controller.reset, "function");
  resetButton.click();

  assert.equal(sourceNameInput.value, "");
  assert.equal(datasetTypeInput.value, "assessment_properties");
  assert.deepEqual(fileInput.files, []);
  assert.equal(triggerInput.value, "on_demand");
  assert.equal(validateOnlyInput.checked, false);
  assert.equal(overwriteInput.checked, true);
});

test("ingestion controller skips reset wiring when reset button is missing", async () => {
  const { document } = installDomGlobals();
  const { createIngestionController } = await import("../src/features/ingestion/ingestionController.js");

  const form = document.createElement("form");
  const feedbackRoot = document.createElement("div");
  const sourceNameInput = document.createElement("input");
  sourceNameInput.value = "src-y";
  const datasetTypeInput = document.createElement("select");
  datasetTypeInput.value = "schools";
  const fileInput = document.createElement("input");
  fileInput.files = [{ name: "schools.csv", size: 1 }];

  const controller = createIngestionController({
    apiClient: { async ingestDataset() { return { status: "success", message: "ok" }; } },
    form,
    resetButton: null,
    statusPill: null,
    statusLabel: null,
    feedbackRoot,
    progressRoot: null,
    progressBar: null,
    fields: {
      sourceNameInput,
      datasetTypeInput,
      fileInput,
      triggerInput: null,
      validateOnlyInput: null,
      overwriteInput: null,
    },
  });

  assert.equal(typeof controller.reset, "function");
  form.dispatchEvent({ type: "submit", target: form });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(feedbackRoot.textContent, /Ingestion successful/);
});

test("ingestion controller guard covers each missing required element branch", async () => {
  const { document } = installDomGlobals();
  const { createIngestionController } = await import("../src/features/ingestion/ingestionController.js");

  const form = document.createElement("form");
  const feedbackRoot = document.createElement("div");
  const datasetTypeInput = document.createElement("select");
  const fileInput = document.createElement("input");

  const missingFieldsObject = createIngestionController({
    apiClient: null,
    form,
    resetButton: null,
    statusPill: null,
    statusLabel: null,
    feedbackRoot,
    progressRoot: null,
    progressBar: null,
    fields: null,
  });
  assert.equal(typeof missingFieldsObject.reset, "function");

  const missingFeedbackRoot = createIngestionController({
    apiClient: null,
    form,
    resetButton: null,
    statusPill: null,
    statusLabel: null,
    feedbackRoot: null,
    progressRoot: null,
    progressBar: null,
    fields: {
      datasetTypeInput,
      fileInput,
    },
  });
  assert.equal(typeof missingFeedbackRoot.reset, "function");

  const missingFileInput = createIngestionController({
    apiClient: null,
    form,
    resetButton: null,
    statusPill: null,
    statusLabel: null,
    feedbackRoot,
    progressRoot: null,
    progressBar: null,
    fields: {
      datasetTypeInput,
      fileInput: null,
    },
  });
  assert.equal(typeof missingFileInput.reset, "function");

  const missingDatasetTypeInput = createIngestionController({
    apiClient: null,
    form,
    resetButton: null,
    statusPill: null,
    statusLabel: null,
    feedbackRoot,
    progressRoot: null,
    progressBar: null,
    fields: {
      datasetTypeInput: null,
      fileInput,
    },
  });
  assert.equal(typeof missingDatasetTypeInput.reset, "function");
});

test("ingestion controller covers invalid filename branch and missing status normalization", async () => {
  const ctx = await buildController({
    async ingestDataset() {
      return { message: "missing status field" };
    },
  });

  ctx.sourceNameInput.value = "source-f";
  ctx.fileInput.files = [{ name: "schools.csv", size: 200 }];

  submit(ctx.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(ctx.statusPill.textContent, "Failed");
  assert.match(ctx.feedbackRoot.textContent, /Ingestion failed/);
  assert.match(ctx.feedbackRoot.textContent, /missing status field/);

  const missingMessage = await buildController({
    async ingestDataset() {
      return {};
    },
  });

  missingMessage.sourceNameInput.value = "source-f2";
  missingMessage.fileInput.files = [{ name: "schools.csv", size: 200 }];
  submit(missingMessage.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(missingMessage.statusPill.textContent, "Failed");
  assert.match(missingMessage.feedbackRoot.textContent, /Backend rejected the ingestion request/);

  const fallback = await buildController({
    async ingestDataset() {
      throw new Error("network");
    },
  });

  fallback.window.setTimeout = (fn) => {
    fn();
    return 1;
  };
  fallback.sourceNameInput.value = "source-g";
  fallback.fileInput.files = [{ name: "schools_invalid.csv", size: 200 }];

  submit(fallback.form);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(fallback.statusPill.textContent, "Failed");
  assert.match(fallback.feedbackRoot.textContent, /cannot be ingested/);
});

test("ingestion controller handles missing source input and blank dataset type values", async () => {
  const { document } = installDomGlobals();
  const { createIngestionController } = await import("../src/features/ingestion/ingestionController.js");

  const form = document.createElement("form");
  const resetButton = document.createElement("button");
  const statusPill = document.createElement("span");
  const statusLabel = document.createElement("span");
  const feedbackRoot = document.createElement("div");

  const datasetTypeInput = document.createElement("select");
  datasetTypeInput.value = "";
  const fileInput = document.createElement("input");
  fileInput.files = [{ name: "schools.csv", size: 10 }];

  createIngestionController({
    apiClient: { async ingestDataset() { return { status: "success" }; } },
    form,
    resetButton,
    statusPill,
    statusLabel,
    feedbackRoot,
    progressRoot: null,
    progressBar: null,
    fields: {
      sourceNameInput: null,
      datasetTypeInput,
      fileInput,
      triggerInput: null,
      validateOnlyInput: null,
      overwriteInput: null,
    },
  });

  form.dispatchEvent({ type: "submit", target: form });
  assert.equal(statusPill.textContent, "Failed");
  assert.match(feedbackRoot.textContent, /Source name required/);
});

test("ingestion controller covers blank trigger values and empty file list branches", async () => {
  const { document } = installDomGlobals();
  const { createIngestionController } = await import("../src/features/ingestion/ingestionController.js");

  const emptyForm = document.createElement("form");
  const emptyFeedback = document.createElement("div");
  const emptySource = document.createElement("input");
  emptySource.value = "src-h";
  const emptyDatasetType = document.createElement("select");
  emptyDatasetType.value = "schools";
  const emptyFileInput = document.createElement("input");
  emptyFileInput.files = [];

  createIngestionController({
    apiClient: { async ingestDataset() { return { status: "success", message: "ok" }; } },
    form: emptyForm,
    resetButton: null,
    statusPill: null,
    statusLabel: null,
    feedbackRoot: emptyFeedback,
    progressRoot: null,
    progressBar: null,
    fields: {
      sourceNameInput: emptySource,
      datasetTypeInput: emptyDatasetType,
      fileInput: emptyFileInput,
      triggerInput: null,
      validateOnlyInput: null,
      overwriteInput: null,
    },
  });

  emptyForm.dispatchEvent({ type: "submit", target: emptyForm });
  assert.match(emptyFeedback.textContent, /No file selected/);

  let captured = null;
  const triggerForm = document.createElement("form");
  const triggerFeedback = document.createElement("div");
  const triggerSource = document.createElement("input");
  triggerSource.value = "src-i";
  const triggerDatasetType = document.createElement("select");
  triggerDatasetType.value = "schools";
  const triggerFileInput = document.createElement("input");
  triggerFileInput.files = [{ name: "schools.csv", size: 5 }];
  const triggerSelect = document.createElement("select");
  triggerSelect.value = "";

  createIngestionController({
    apiClient: { async ingestDataset(payload) { captured = payload; return { status: "success", message: "ok" }; } },
    form: triggerForm,
    resetButton: null,
    statusPill: null,
    statusLabel: null,
    feedbackRoot: triggerFeedback,
    progressRoot: null,
    progressBar: null,
    fields: {
      sourceNameInput: triggerSource,
      datasetTypeInput: triggerDatasetType,
      fileInput: triggerFileInput,
      triggerInput: triggerSelect,
      validateOnlyInput: null,
      overwriteInput: null,
    },
  });

  triggerForm.dispatchEvent({ type: "submit", target: triggerForm });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(captured.trigger, "on_demand");
});

test("ingestion controller rejects files missing a name", async () => {
  const ctx = await buildController({
    async ingestDataset() {
      return { status: "success", message: "ok" };
    },
  });

  ctx.sourceNameInput.value = "source-j";
  ctx.datasetTypeInput.value = "schools";
  ctx.fileInput.files = [{ size: 10 }];

  submit(ctx.form);
  assert.equal(ctx.statusPill.textContent, "Failed");
  assert.match(ctx.feedbackRoot.textContent, /\.unknown is not supported/);
});
