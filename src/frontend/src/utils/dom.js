export function createElement(tagName, className, textContent) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  if (textContent !== undefined) {
    element.textContent = textContent;
  }
  return element;
}

export function clearElement(element) {
  if (!element) {
    return;
  }
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

export function setText(element, value) {
  if (!element) {
    return;
  }
  element.textContent = value;
}

export function toggleHidden(element, hidden) {
  element.classList.toggle("is-hidden", hidden);
}
