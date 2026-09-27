/**
 * REVIEW OWNER: Havala
 *
 * How the door's use-case band moves: the counter, the rotation between use
 * cases, and which photograph a use case shows on each visit. The use cases
 * themselves are `AUDIENCE_JOBS` in `pressJobs.js`; this is only the motion,
 * kept as pure functions so the node suite can hold each rule and the
 * component only turns events into actions.
 */

/** "01 / 10": the counter, from the shown set, never from the declared ten. */
export function counterLabel(index, total) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(index + 1)} / ${pad(total)}`;
}

// ── Rotation ──────────────────────────────────────────────────────────────
//
// The band advances by itself, slowly, until the visitor does anything with
// it. The rules (owner's brief, section 3): about 7 to 9 seconds a step;
// automatic rotation stops for good once the visitor interacts; it pauses
// while the band is hovered or holds focus; and under prefers-reduced-motion
// it never cycles. A fifth condition is this page's own: it does not advance
// while the band is off screen, so a visitor who scrolls down to it starts on
// the first example rather than on whichever one the timer reached.
//
// Kept as a pure reducer so the node suite can hold each rule, and the
// component only turns events into actions and `shouldRotate` into a timer.

/** Milliseconds between automatic steps: inside the brief's 7 to 9 seconds. */
export const ROTATE_MS = 8000;

export const INITIAL_ROTATION = Object.freeze({
  index: 0,
  stopped: false,
  hovered: false,
  focused: false,
  visible: false,
});

/** The next state. `total` is the number of audiences shown. */
export function rotationReducer(state, action) {
  const total = Math.max(1, action.total ?? 1);
  switch (action.type) {
    case "tick":
      // A tick only ever arrives while `shouldRotate` holds, but the reducer
      // re-checks rather than trusting the timer: a late tick after a click
      // must not move the example the visitor just chose.
      if (state.stopped || state.hovered || state.focused || !state.visible) return state;
      return { ...state, index: (state.index + 1) % total };
    case "select":
      return { ...state, stopped: true, index: ((action.index % total) + total) % total };
    case "stop":
      // The visitor committed to something inside the band (a collection):
      // the example they were reading stays put.
      return { ...state, stopped: true };
    case "next":
      return { ...state, stopped: true, index: (state.index + 1) % total };
    case "prev":
      return { ...state, stopped: true, index: (state.index - 1 + total) % total };
    case "hover":
      return { ...state, hovered: Boolean(action.on) };
    case "focus":
      return { ...state, focused: Boolean(action.on) };
    case "visible":
      return { ...state, visible: Boolean(action.on) };
    default:
      return state;
  }
}

/** Whether a timer should be running. */
export function shouldRotate(state, { reducedMotion = false, total = 0 } = {}) {
  return !reducedMotion && total > 1 && !state.stopped && !state.hovered && !state.focused && state.visible;
}

/**
 * The photograph a use case shows on its `visit`th showing (1 for the first),
 * cycling through its imagery. The band counts a visit each time a use case
 * becomes the one in view, so a visitor who comes back to Tribal Nations sees
 * the next of its six photographs rather than the same one. Nothing moves
 * while a use case is on screen: the photograph changes only between visits.
 */
export function imageFor(imagery, visit = 1) {
  if (!imagery?.length) return null;
  const n = Math.max(1, Math.floor(visit));
  return imagery[(n - 1) % imagery.length];
}
