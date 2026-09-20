import { useEffect, useRef, useState } from "react";

// Which edges of a sideways-scrolling table still have content past them.
//
// WHY THIS IS A FUNCTION AND NOT A `data-end="1"` IN THE MARKUP.
// It was the latter. One scrollwrap hardcoded `data-end="1"` and the other
// set nothing at all, so the right-edge cue on the record table was painted
// permanently — it said "there is more to the right" just as loudly when you
// had already scrolled to the last column. A cue that is always on is not a
// cue, it is a decoration, and the one place it mattered it was wrong.
//
// The record table hides 927px of columns at 1280px wide. A reader who
// cannot tell that is not reading a wide table, they are reading a truncated
// one, and "Department of Housing and Urban Develo" looks like a bug.

/** A tolerance in px. Sub-pixel layout means `scrollLeft` rarely lands exactly. */
const EPS = 2;

/**
 * `{ start, end }` — whether content continues past the left and right edges.
 *
 * Takes plain numbers rather than an element so it can be checked without a
 * DOM, and so the caller decides when to measure.
 */
export function scrollEdges({ scrollLeft = 0, scrollWidth = 0, clientWidth = 0 } = {}) {
  const max = scrollWidth - clientWidth;
  if (!(max > EPS)) return { start: false, end: false };
  return {
    start: scrollLeft > EPS,
    end: scrollLeft < max - EPS,
  };
}

/**
 * The same answer as the attribute pair a stylesheet reads.
 *
 * `data-start` / `data-end` are present only when that edge has more past
 * it, so the CSS selector is the presence of the attribute rather than a
 * comparison against a string — `[data-end]`, not `[data-end="0"]`, which is
 * what the old markup got wrong in both directions.
 */
export function edgeAttrs(metrics) {
  const { start, end } = scrollEdges(metrics);
  return {
    ...(start ? { "data-start": "" } : {}),
    ...(end ? { "data-end": "" } : {}),
  };
}

/**
 * Keep a scroller's edge attributes true, in React.
 *
 * Returns `[ref, attrs]`: put the ref on the scrolling element and spread the
 * attrs on its wrapper, which is the box the cue is painted on.
 *
 * It listens to `scroll` passively, and to the element's own resize, because
 * the answer changes when a column is shown or hidden without anybody
 * scrolling — which is exactly what the column picker does.
 */
export function useScrollEdges() {
  const ref = useRef(null);
  const [attrs, setAttrs] = useState({});

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    // Compare the rendered attribute set, not the object: this runs on every
    // scroll frame and a new object each time would re-render the table.
    let last = "";
    const measure = () => {
      const next = edgeAttrs(el);
      const key = Object.keys(next).sort().join(",");
      if (key !== last) {
        last = key;
        setAttrs(next);
      }
    };
    measure();
    el.addEventListener("scroll", measure, { passive: true });
    // ResizeObserver is absent in jsdom and in older Safari; the listeners
    // above still carry the common case, so this degrades rather than throws.
    const ro = typeof ResizeObserver === "function" ? new ResizeObserver(measure) : null;
    ro?.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      el.removeEventListener("scroll", measure);
      ro?.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  return [ref, attrs];
}
