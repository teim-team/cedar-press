// Where keyboard focus goes when a panel opens and closes.
//
// Three panels (the door's Cedar, the signed-in Cedar launcher and the
// collection profile) moved focus into themselves on open and then let it
// fall to <body> on close, so a keyboard or screen reader user who pressed
// Escape was sent back to the top of the document. On a phone the launcher
// that opened Cedar is hidden while Cedar is open, so focus was lost on the
// way in as well. Measured with Playwright, 2026-10-04.
//
// `rememberFocus` records what had focus when a panel opened and hands back
// a function that returns focus there, or to the first fallback that is still
// on screen. `keepTabInside` holds Tab and Shift+Tab inside a sheet that
// covers the page, so a reader tabbing off its end does not land in the rows
// behind it.

export const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  'input:not([disabled]):not([type="hidden"])',
  "select:not([disabled])",
  "textarea:not([disabled])",
  "summary",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

/** Attached and laid out: an element focus can usefully land on. */
export function isShown(node) {
  return Boolean(node)
    && node.isConnected !== false
    && typeof node.getClientRects === "function"
    && node.getClientRects().length > 0;
}

export function rememberFocus(doc = globalThis.document) {
  const opener = doc?.activeElement ?? null;
  return function restore(...fallbacks) {
    for (const node of [opener, ...fallbacks]) {
      if (node && node !== doc?.body && isShown(node) && typeof node.focus === "function") {
        node.focus();
        return node;
      }
    }
    return null;
  };
}

/** True when focus is inside `container`, or nowhere (on <body>). */
export function focusWasWithin(container, doc = globalThis.document) {
  const active = doc?.activeElement ?? null;
  return !active || active === doc?.body || Boolean(container?.contains(active));
}

export function keepTabInside(event, container) {
  if (event?.key !== "Tab" || !container) return false;
  const items = [...container.querySelectorAll(FOCUSABLE)].filter(isShown);
  const active = container.ownerDocument?.activeElement ?? null;
  if (!items.length) {
    event.preventDefault();
    return true;
  }
  const first = items[0];
  const last = items[items.length - 1];
  const outside = !container.contains(active);
  if (event.shiftKey ? active === first || outside : active === last || outside) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
    return true;
  }
  return false;
}
