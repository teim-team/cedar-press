// A disclosure that closes on Escape and on a click outside it.
//
// Shared by the masthead's two menus and, since 2026-10-04, by the record
// viewer's Filters and More panels. Those two open over the table like the
// masthead menus do, but stayed open on Escape and on a click elsewhere, so a
// keyboard reader had no way to dismiss them short of finding the summary
// again. Measured with Playwright at 375 and 1280 px.
import { useCallback } from "react";

/**
 * A disclosure that closes on Escape and on a click outside it.
 *
 * Both menus in the masthead are native `<details>`: they work with no state,
 * a keyboard reaches them, and a screen reader announces them. What details
 * does not do on its own is close when the reader looks elsewhere, which is
 * what a menu in a header has to do.
 */
export function useDismissable() {
  // A callback ref, with React 19's ref cleanup, rather than an effect that
  // runs once on mount: the viewer's toolbar unmounts and remounts as the
  // reader moves between an open, a locked and a structure-only collection,
  // and a mount-time effect would have attached to the first toolbar only.
  return useCallback((node) => {
    if (!node) return undefined;
    const close = (refocus) => {
      if (!node.open) return;
      node.open = false;
      if (refocus) node.querySelector("summary")?.focus();
    };
    const onKey = (event) => { if (event.key === "Escape") close(true); };
    const onDown = (event) => { if (!node.contains(event.target)) close(false); };
    node.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      node.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, []);
}
