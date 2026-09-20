// The cue has to be wrong in neither direction: silent when there is nothing
// past the edge, and lit when there is. The bug it replaces was a hardcoded
// `data-end="1"` that stayed lit at the last column.

import assert from "node:assert/strict";
import test from "node:test";

import { edgeAttrs, scrollEdges } from "./scrollEdges.js";

test("a table that fits shows no cue at either edge", () => {
  assert.deepEqual(scrollEdges({ scrollLeft: 0, scrollWidth: 800, clientWidth: 800 }), {
    start: false, end: false,
  });
  // And one a pixel over is still not worth an arrow.
  assert.deepEqual(scrollEdges({ scrollLeft: 0, scrollWidth: 801, clientWidth: 800 }), {
    start: false, end: false,
  });
});

test("at the start, only the right edge has more past it", () => {
  assert.deepEqual(scrollEdges({ scrollLeft: 0, scrollWidth: 1727, clientWidth: 800 }), {
    start: false, end: true,
  });
});

test("mid-scroll, both edges do", () => {
  assert.deepEqual(scrollEdges({ scrollLeft: 400, scrollWidth: 1727, clientWidth: 800 }), {
    start: true, end: true,
  });
});

test("at the last column the right cue goes out", () => {
  // The exact failure the hardcoded attribute produced.
  assert.deepEqual(scrollEdges({ scrollLeft: 927, scrollWidth: 1727, clientWidth: 800 }), {
    start: true, end: false,
  });
  // Sub-pixel layout rarely lands on the integer, so within tolerance counts.
  assert.deepEqual(scrollEdges({ scrollLeft: 926.4, scrollWidth: 1727, clientWidth: 800 }), {
    start: true, end: false,
  });
});

test("the attributes are present or absent, never a string to compare", () => {
  // `[data-end="1"]` is what the old markup wrote and what the old CSS then
  // could not switch off. Presence is the whole state.
  assert.deepEqual(edgeAttrs({ scrollLeft: 0, scrollWidth: 1727, clientWidth: 800 }), { "data-end": "" });
  assert.deepEqual(edgeAttrs({ scrollLeft: 927, scrollWidth: 1727, clientWidth: 800 }), { "data-start": "" });
  assert.deepEqual(edgeAttrs({ scrollLeft: 400, scrollWidth: 1727, clientWidth: 800 }),
    { "data-start": "", "data-end": "" });
  assert.deepEqual(edgeAttrs({ scrollLeft: 0, scrollWidth: 800, clientWidth: 800 }), {});
});

test("nothing measured yet is not a cue", () => {
  // First paint, before layout: every number is 0 and the honest answer is
  // "no idea", which must render as silence rather than as two arrows.
  assert.deepEqual(scrollEdges(), { start: false, end: false });
  assert.deepEqual(scrollEdges({}), { start: false, end: false });
});
