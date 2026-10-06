// Focus return and the Tab boundary for the panels that open over a page.
// The browser behaviour is in tests/accessibility.spec.js; these pin the rules
// on stand-in elements, so each branch is checked without a DOM.

import assert from "node:assert/strict";
import test from "node:test";

import { FOCUSABLE, focusWasWithin, isShown, keepTabInside, rememberFocus } from "./focusReturn.js";

function node(name, { shown = true, connected = true, inside = [] } = {}) {
  return {
    name,
    isConnected: connected,
    getClientRects: () => (shown ? [{}] : []),
    focused: 0,
    focus() { this.focused += 1; doc.activeElement = this; },
    contains(other) { return other === this || inside.includes(other); },
  };
}
const doc = { body: null, activeElement: null };
// A real <body> is attached and laid out, so only the explicit check keeps
// focus from being "returned" to it.
doc.body = node("body");

test("isShown needs an attached element with a layout box", () => {
  assert.equal(isShown(null), false);
  assert.equal(isShown({}), false);
  assert.equal(isShown(node("hidden", { shown: false })), false);
  assert.equal(isShown(node("gone", { connected: false })), false);
  assert.equal(isShown(node("here")), true);
});

test("focus returns to the opener when it is still on screen", () => {
  const opener = node("opener");
  const fallback = node("fallback");
  doc.activeElement = opener;
  const restore = rememberFocus(doc);
  doc.activeElement = doc.body;
  assert.equal(restore(fallback), opener);
  assert.equal(opener.focused, 1);
  assert.equal(fallback.focused, 0);
});

test("a hidden opener hands focus to the first fallback on screen", () => {
  const opener = node("launcher", { shown: false });
  const gone = node("gone", { connected: false });
  const fallback = node("fallback");
  doc.activeElement = opener;
  const restore = rememberFocus(doc);
  assert.equal(restore(null, gone, fallback), fallback);
  assert.equal(opener.focused, 0);
});

test("an opener that was <body> is never focused, and nothing left returns null", () => {
  doc.activeElement = doc.body;
  const restore = rememberFocus(doc);
  assert.equal(restore(), null);
  assert.equal(rememberFocus(undefined)(), null);
});

test("focusWasWithin is true inside the panel or on <body>, false elsewhere", () => {
  const inner = node("inner");
  const panel = node("panel", { inside: [inner] });
  doc.activeElement = inner;
  assert.equal(focusWasWithin(panel, doc), true);
  doc.activeElement = doc.body;
  assert.equal(focusWasWithin(panel, doc), true);
  doc.activeElement = null;
  assert.equal(focusWasWithin(panel, doc), true);
  doc.activeElement = node("elsewhere");
  assert.equal(focusWasWithin(panel, doc), false);
  assert.equal(focusWasWithin(null, doc), false);
  assert.equal(focusWasWithin(panel, undefined), true);
});

function sheet(items) {
  const panel = node("panel", { inside: items });
  panel.ownerDocument = doc;
  panel.selector = null;
  panel.querySelectorAll = (selector) => { panel.selector = selector; return items; };
  return panel;
}
function key(name, shiftKey = false) {
  return { key: name, shiftKey, prevented: false, preventDefault() { this.prevented = true; } };
}

test("Tab off the last control wraps to the first, Shift+Tab off the first wraps to the last", () => {
  const first = node("close");
  const middle = node("link");
  const hidden = node("collapsed", { shown: false });
  const last = node("send");
  const panel = sheet([first, middle, hidden, last]);

  doc.activeElement = last;
  const forward = key("Tab");
  assert.equal(keepTabInside(forward, panel), true);
  assert.equal(forward.prevented, true);
  assert.equal(doc.activeElement, first);
  assert.equal(panel.selector, FOCUSABLE);

  const back = key("Tab", true);
  assert.equal(keepTabInside(back, panel), true);
  assert.equal(doc.activeElement, last);

  doc.activeElement = middle;
  const plain = key("Tab");
  assert.equal(keepTabInside(plain, panel), false);
  assert.equal(plain.prevented, false);
  const plainBack = key("Tab", true);
  assert.equal(keepTabInside(plainBack, panel), false);
});

test("focus outside the sheet is brought back in on Tab", () => {
  const first = node("close");
  const last = node("send");
  const panel = sheet([first, last]);
  doc.activeElement = node("row behind");
  assert.equal(keepTabInside(key("Tab"), panel), true);
  assert.equal(doc.activeElement, first);
  doc.activeElement = node("row behind");
  assert.equal(keepTabInside(key("Tab", true), panel), true);
  assert.equal(doc.activeElement, last);
});

test("a sheet with nothing focusable swallows Tab; other keys and no sheet are ignored", () => {
  const empty = sheet([node("hidden", { shown: false })]);
  const tab = key("Tab");
  assert.equal(keepTabInside(tab, empty), true);
  assert.equal(tab.prevented, true);
  assert.equal(keepTabInside(key("Escape"), empty), false);
  assert.equal(keepTabInside(key("Tab"), null), false);
  assert.equal(keepTabInside(undefined, empty), false);
  const orphan = sheet([node("a")]);
  delete orphan.ownerDocument;
  assert.equal(keepTabInside(key("Tab"), orphan), true);
});
