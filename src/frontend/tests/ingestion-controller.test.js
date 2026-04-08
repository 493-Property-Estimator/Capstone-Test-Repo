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
