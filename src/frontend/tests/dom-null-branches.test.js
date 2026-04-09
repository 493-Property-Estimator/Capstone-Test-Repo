import test from "node:test";
import assert from "node:assert/strict";

import { installDomGlobals } from "./helpers/fakeDom.js";

test("dom helpers handle null elements without throwing", async () => {
  installDomGlobals();
  const { clearElement, setText, toggleHidden } = await import("../src/utils/dom.js");

  assert.doesNotThrow(() => clearElement(null));
  assert.doesNotThrow(() => setText(null, "x"));

  const element = document.createElement("div");
  toggleHidden(element, true);
  assert.equal(element.classList.contains("is-hidden"), true);
});

