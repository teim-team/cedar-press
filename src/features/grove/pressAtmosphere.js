/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * Depth, without moving anything a reader is trying to read.
 *
 * The surfaces are deliberately flat: one colour each, hard edges between
 * them, no gradient anywhere. That is a founder decision and it is not the
 * thing to reach for when the page feels static. Depth comes from here
 * instead, behind the content, where it cannot compete with the type.
 *
 * RULES
 * Parallax moves background layers only. Cards, body copy and controls stay
 * exactly where the reader put them; a page where the text drifts is a page
 * nobody can read. Everything here is inert under prefers-reduced-motion.
 */

/**
 * The section palette, in the order the reader meets it.
 *
 * Six steps rather than two, so a transition can be a shift in temperature
 * instead of a hard switch between the same two colours. `--paper` and
 * `--mist` are only a few degrees apart on purpose: the change should be felt
 * before it is noticed.
 */
export const SURFACE = Object.freeze({
  PAPER: "paper",
  MIST: "mist",
  PALE: "pale",
  TEAL: "teal",
  DEEP: "deep",
});

/**
 * Tracks how far a node has travelled through the viewport, as -1 to 1, and
 * writes it to a CSS custom property.
 *
 * A custom property rather than a React state update: this fires on every
 * frame of a scroll, and re-rendering a tree that often is how a smooth page
 * becomes a stuttering one. The style engine can take a number sixty times a
 * second; the reconciler should not have to.
 */
export function trackParallax(node, { property = "--p", strength = 1 } = {}) {
  if (!node || typeof window === "undefined") return () => {};
  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  if (reduced?.matches) return () => {};

  let frame = 0;
  const measure = () => {
    frame = 0;
    const rect = node.getBoundingClientRect();
    const middle = rect.top + rect.height / 2;
    const progress = (window.innerHeight / 2 - middle) / (window.innerHeight / 2 + rect.height / 2);
    node.style.setProperty(property, (Math.max(-1, Math.min(1, progress)) * strength).toFixed(4));
  };
  const onScroll = () => {
    if (frame) return;
    frame = window.requestAnimationFrame(measure);
  };

  measure();
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  return () => {
    if (frame) window.cancelAnimationFrame(frame);
    window.removeEventListener("scroll", onScroll);
    window.removeEventListener("resize", onScroll);
  };
}
