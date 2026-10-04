/**
 * PURPOSE
 * Reload a page whose code did not arrive, once, when the connection returns.
 *
 * PageBoundary.jsx shows a Reload button when a lazy chunk fails. If the
 * reader was offline, the button is still the right answer once they are back
 * online, but nothing told them so and the page sat broken until they noticed
 * (2026-10-04 audit). A rejected lazy import cannot be re-attempted in place
 * (React keeps the rejection), so the retry is a reload, exactly what the
 * button does. It fires on an `online` event only, which needs the browser to
 * have gone offline first, so it cannot loop; and at most once per failure.
 *
 * Returns the unsubscribe. A no-op where there is no `window` (Node).
 */
export function reloadOnceWhenOnline({
  target = globalThis.window,
  reload = () => target.location.reload(),
} = {}) {
  if (!target?.addEventListener) return () => {};
  const handler = () => {
    target.removeEventListener("online", handler);
    reload();
  };
  target.addEventListener("online", handler);
  return () => target.removeEventListener("online", handler);
}
