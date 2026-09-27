/**
 * A figure that ticks to its value once, when it first comes into view
 * (owner, 2026-09-27: the hero's collection, record and year figures).
 *
 * The final value is what renders first, so the prerendered page, a reader
 * without script and a reader who prefers reduced motion all see the real
 * number and nothing moves. Only a browser that can animate resets it to the
 * start value and runs it up (or back, for a year) on the page's ease.
 */
import { useEffect, useRef } from "react";

/** Ease-out cubic: fast at first, settling onto the value. */
export const easeOut = (t) => 1 - (1 - t) ** 3;

/** The whole number shown at progress `t` (0 to 1) between `from` and `to`. */
export function tickValue(from, to, t) {
  const p = Math.min(1, Math.max(0, t));
  if (p === 1) return to;
  return Math.round(from + (to - from) * easeOut(p));
}

/**
 * Writes the ticking number straight into the element rather than through
 * React state: the rendered value never changes, so the effect sets no state
 * and a re-render can never fight the animation.
 */
export function useTicker(target, { from = 0, duration = 1400, format = String } = {}) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof window === "undefined" || typeof IntersectionObserver === "undefined") return undefined;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
    let raf = 0;
    let started = false;
    el.textContent = format(from);
    const io = new IntersectionObserver(
      (entries) => {
        if (started || !entries.some((entry) => entry.isIntersecting)) return;
        started = true;
        io.disconnect();
        const start = performance.now();
        const step = (now) => {
          const t = (now - start) / duration;
          el.textContent = format(tickValue(from, target, t));
          if (t < 1) raf = requestAnimationFrame(step);
        };
        raf = requestAnimationFrame(step);
      },
      { threshold: 0.6 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
      el.textContent = format(target);
    };
  }, [target, from, duration, format]);
  return ref;
}
