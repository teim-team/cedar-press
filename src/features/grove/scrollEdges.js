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
