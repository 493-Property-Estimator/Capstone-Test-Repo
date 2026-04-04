import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals, createMockResponse, wait } from "./helpers/fakeDom.js";

test("store updates layers, property layer, and subscriptions", async () => {
  installDomGlobals();
  globalThis.fetch = async () => createMockResponse("");

  const { createStore } = await import("../src/state/store.js");
  const store = createStore();
  const snapshots = [];
  const unsubscribe = store.subscribe((state) => {
    snapshots.push(state);
  });

  store.setState({ selectedLocation: { canonical_address: "Test" } });
  store.updateLayer("schools", { enabled: true, status: "ready", data: { features: [] } });
  store.updatePropertyLayer({ status: "ready", renderMode: "property" });

  assert.equal(store.getState().selectedLocation.canonical_address, "Test");
  assert.equal(store.getState().activeLayers.schools.status, "ready");
  assert.equal(store.getState().propertyLayer.renderMode, "property");
  assert.equal(snapshots.length, 3);

  unsubscribe();
  store.setState({ warningsCollapsed: true });
  assert.equal(snapshots.length, 3);
});

test("dom helpers and debounce support basic UI interactions", async () => {
  const { document } = installDomGlobals();
  const { createElement, clearElement, setText, toggleHidden } = await import(
    "../src/utils/dom.js"
  );
  const { debounce } = await import("../src/utils/debounce.js");

  const parent = document.createElement("div");
  const child = createElement("span", "chip", "Hello");
  parent.appendChild(child);
  assert.equal(child.className, "chip");
  assert.equal(child.textContent, "Hello");

  setText(child, "Updated");
  assert.equal(child.textContent, "Updated");

  toggleHidden(child, true);
  assert.equal(child.classList.contains("is-hidden"), true);

  clearElement(parent);
  assert.equal(parent.children.length, 0);

  let callCount = 0;
  const debounced = debounce(() => {
    callCount += 1;
  }, 5);

  debounced();
  debounced();
  await wait(15);

  assert.equal(callCount, 1);
});
