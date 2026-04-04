class FakeClassList {
  constructor(owner) {
    this.owner = owner;
    this.classes = new Set();
  }

  add(...names) {
    names.filter(Boolean).forEach((name) => this.classes.add(name));
    this.#sync();
  }

  remove(...names) {
    names.filter(Boolean).forEach((name) => this.classes.delete(name));
    this.#sync();
  }

  toggle(name, force) {
    if (force === true) {
      this.classes.add(name);
    } else if (force === false) {
      this.classes.delete(name);
    } else if (this.classes.has(name)) {
      this.classes.delete(name);
    } else {
      this.classes.add(name);
    }
    this.#sync();
    return this.classes.has(name);
  }

  contains(name) {
    return this.classes.has(name);
  }

  setFromString(value) {
    this.classes = new Set(String(value || "").split(/\s+/).filter(Boolean));
    this.#sync();
  }

  #sync() {
    this.owner._className = Array.from(this.classes).join(" ");
  }
}

class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = String(tagName || "div").toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.parentNode = null;
    this.style = {};
    this.attributes = new Map();
    this.eventListeners = new Map();
    this.classList = new FakeClassList(this);
    this._className = "";
    this._textContent = "";
    this._innerHTML = "";
    this._value = "";
    this._checked = false;
    this._type = "";
    this.id = "";
    this.disabled = false;
  }

  set className(value) {
    this.classList.setFromString(value);
  }

  get className() {
    return this._className;
  }

  set textContent(value) {
    this._textContent = String(value ?? "");
    this._innerHTML = "";
    this.children = [];
  }

  get textContent() {
    if (this.children.length) {
      return this.children.map((child) => child.textContent).join("");
    }
    return this._textContent;
  }

  set innerHTML(value) {
    this._innerHTML = String(value ?? "");
    this._textContent = this._innerHTML.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    this.children = [];
  }

  get innerHTML() {
    return this._innerHTML;
  }

  set value(nextValue) {
    this._value = String(nextValue ?? "");
  }

  get value() {
    return this._value;
  }

  set checked(nextValue) {
    this._checked = Boolean(nextValue);
  }

  get checked() {
    return this._checked;
  }

  set type(nextValue) {
    this._type = String(nextValue ?? "");
  }

  get type() {
    return this._type;
  }

  get firstChild() {
    return this.children[0] || null;
  }

  appendChild(child) {
    if (!child) {
      return child;
    }

    if (child.parentNode) {
      child.parentNode.removeChild(child);
    }

    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index >= 0) {
      this.children.splice(index, 1);
      child.parentNode = null;
    }
    return child;
  }

  remove() {
    if (this.parentNode) {
      this.parentNode.removeChild(this);
    }
  }

  addEventListener(type, handler) {
    if (!this.eventListeners.has(type)) {
      this.eventListeners.set(type, []);
    }
    this.eventListeners.get(type).push(handler);
  }

  dispatchEvent(event) {
    const payload = {
      type: event?.type,
      target: event?.target || this,
      currentTarget: this,
      key: event?.key,
      originalEvent: event?.originalEvent,
      lngLat: event?.lngLat,
      features: event?.features,
      button: event?.button,
      defaultPrevented: false,
      preventDefault() {
        this.defaultPrevented = true;
      }
    };

    (this.eventListeners.get(payload.type) || []).forEach((handler) => handler(payload));
    return !payload.defaultPrevented;
  }

  click() {
    this.dispatchEvent({ type: "click", target: this });
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
    if (name === "id") {
      this.id = String(value);
      this.ownerDocument.elementsById.set(this.id, this);
    }
  }

  getAttribute(name) {
    return this.attributes.get(name) || null;
  }

  getBoundingClientRect() {
    return this._boundingRect || {
      left: 0,
      top: 0,
      width: 120,
      height: 60
    };
  }

  setBoundingClientRect(rect) {
    this._boundingRect = { ...rect };
  }
}

class FakeDocument {
  constructor() {
    this.elementsById = new Map();
    this.body = new FakeElement("body", this);
  }

  createElement(tagName) {
    return new FakeElement(tagName, this);
  }

  getElementById(id) {
    return this.elementsById.get(id) || null;
  }

  registerElement(id, tagName = "div") {
    const element = this.createElement(tagName);
    element.id = id;
    this.elementsById.set(id, element);
    this.body.appendChild(element);
    return element;
  }
}

export function createMockResponse(body, init = {}) {
  const status = init.status ?? 200;
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      if (init.invalidJson) {
        throw new Error("invalid json");
      }
      return body;
    },
    async text() {
      return typeof body === "string" ? body : JSON.stringify(body);
    }
  };
}

export function installDomGlobals({ ids = [] } = {}) {
  const document = new FakeDocument();
  ids.forEach(({ id, tagName = "div", rect = null }) => {
    const element = document.registerElement(id, tagName);
    if (rect) {
      element.setBoundingClientRect(rect);
    }
  });

  const windowObject = {
    document,
    setTimeout: globalThis.setTimeout.bind(globalThis),
    clearTimeout: globalThis.clearTimeout.bind(globalThis),
    requestAnimationFrame(callback) {
      return windowObject.setTimeout(() => callback(Date.now()), 0);
    },
    cancelAnimationFrame(id) {
      windowObject.clearTimeout(id);
    }
  };

  globalThis.document = document;
  globalThis.window = windowObject;
  globalThis.HTMLElement = FakeElement;
  globalThis.Event = class Event {
    constructor(type) {
      this.type = type;
    }
  };
  globalThis.DOMException = globalThis.DOMException || class DOMException extends Error {
    constructor(message, name) {
      super(message);
      this.name = name;
    }
  };

  return {
    document,
    window: windowObject,
    getById(id) {
      return document.getElementById(id);
    }
  };
}

export function wait(ms = 0) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
