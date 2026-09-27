/**
 * How the door's use-case band moves: the counter, the rotation rules, and
 * which photograph a use case shows on each visit.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  INITIAL_ROTATION,
  ROTATE_MS,
  counterLabel,
  imageFor,
  rotationReducer,
  shouldRotate,
} from "./pressRotation.js";
import { visibleAudiences } from "./pressJobs.js";

// ── Rotation ──────────────────────────────────────────────────────────────

const run = (state, ...actions) => actions.reduce((s, a) => rotationReducer(s, { total: 9, ...a }), state);
const onScreen = run(INITIAL_ROTATION, { type: "visible", on: true });

test("the step is slow: inside the brief's seven to nine seconds", () => {
  assert.ok(ROTATE_MS >= 7000 && ROTATE_MS <= 9000, String(ROTATE_MS));
});

test("it advances on screen and wraps round", () => {
  assert.equal(run(onScreen, { type: "tick" }).index, 1);
  assert.equal(run({ ...onScreen, index: 8 }, { type: "tick" }).index, 0);
  assert.equal(run(INITIAL_ROTATION, { type: "tick" }).index, 0, "off screen, nothing moves");
});

test("hover and focus pause it, and releasing them resumes it", () => {
  const hovered = run(onScreen, { type: "hover", on: true });
  assert.equal(shouldRotate(hovered, { total: 9 }), false);
  assert.equal(run(hovered, { type: "tick" }).index, 0);
  const focused = run(onScreen, { type: "focus", on: true });
  assert.equal(shouldRotate(focused, { total: 9 }), false);
  assert.equal(run(focused, { type: "tick" }).index, 0);
  assert.equal(shouldRotate(run(hovered, { type: "hover", on: false }), { total: 9 }), true);
});

test("any choice stops it for good, and a late tick cannot move the chosen example", () => {
  for (const action of [{ type: "select", index: 4 }, { type: "next" }, { type: "prev" }]) {
    const chosen = run(onScreen, action);
    assert.equal(chosen.stopped, true, action.type);
    assert.equal(shouldRotate(chosen, { total: 9 }), false, action.type);
    assert.equal(run(chosen, { type: "tick" }).index, chosen.index, `${action.type} then tick`);
    // Leaving and re-entering does not restart it.
    const back = run(chosen, { type: "hover", on: true }, { type: "hover", on: false }, { type: "visible", on: true });
    assert.equal(shouldRotate(back, { total: 9 }), false, action.type);
  }
  assert.equal(run(onScreen, { type: "prev" }).index, 8, "previous from the first wraps to the last");
  assert.equal(run(onScreen, { type: "select", index: -1 }).index, 8);
});

test("committing a collection stops the rotation and keeps the example in place", () => {
  const moved = run(onScreen, { type: "tick" }, { type: "tick" });
  const committed = run(moved, { type: "stop" });
  assert.equal(committed.index, moved.index);
  assert.equal(committed.stopped, true);
  assert.equal(run(committed, { type: "tick" }).index, moved.index);
});

test("rotation state carries no collection: only a visitor's click selects one", () => {
  const after = run(onScreen, { type: "tick" }, { type: "tick" }, { type: "next" }, { type: "stop" });
  assert.deepEqual(Object.keys(after).sort(), ["focused", "hovered", "index", "stopped", "visible"]);
});

test("reduced motion never cycles, and one example has nothing to cycle", () => {
  assert.equal(shouldRotate(onScreen, { total: 9 }), true);
  assert.equal(shouldRotate(onScreen, { total: 9, reducedMotion: true }), false);
  assert.equal(shouldRotate(onScreen, { total: 1 }), false);
  assert.equal(rotationReducer(onScreen, { type: "nonsense" }), onScreen);
});

test("the counter counts what is shown", () => {
  // The total is the shown set's size, derived, never typed: twelve today.
  const shown = visibleAudiences().length;
  assert.equal(counterLabel(0, shown), `01 / ${String(shown).padStart(2, "0")}`);
  assert.equal(counterLabel(0, 12), "01 / 12");
  assert.equal(counterLabel(9, 10), "10 / 10");
});

test("a use case shows the next photograph in its pool on each visit, and wraps", () => {
  const pool = ["a", "b", "c"];
  assert.equal(imageFor(pool, 1), "a");
  assert.equal(imageFor(pool, 2), "b");
  assert.equal(imageFor(pool, 4), "a");
  assert.equal(imageFor(pool), "a", "the first visit when none is counted yet");
  assert.equal(imageFor(pool, 0), "a", "never before the first");
  assert.equal(imageFor(["only"], 7), "only");
  assert.equal(imageFor([], 1), null);
  assert.equal(imageFor(undefined, 1), null);
});
