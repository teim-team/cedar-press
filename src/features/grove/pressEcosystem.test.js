// The ecosystem diagram's geometry, held to account. The solver in
// pressEcosystem.js promises that every source gets its own ray, that no
// ray crosses any collection's label, that no source name lands on another
// label or a sibling, and that the whole figure fits its canvas. Copy edits
// to RING or SOURCES re-run the solver; this file makes sure the promises
// survive them.
import test from "node:test";
import assert from "node:assert/strict";
import {
  RING,
  SOURCES,
  FEEDS,
  LAYOUT,
  labelBoxFor,
  srcBoxFor,
  clears,
  overlaps,
} from "./pressEcosystem.js";

const centered = (p) => ({
  ...p,
  x: p.x - LAYOUT.cx,
  y: p.y - LAYOUT.cy,
  ...(p.dx == null ? {} : { dx: p.dx - LAYOUT.cx, dy: p.dy - LAYOUT.cy }),
});
const nodes = LAYOUT.nodes.map(centered);
const labelBoxes = nodes.map(labelBoxFor);

test("every collection is on the ring with a fan", () => {
  assert.equal(LAYOUT.nodes.length, RING.length);
  for (const name of RING) {
    assert.ok(SOURCES[name]?.length, `${name} has sources`);
    assert.ok(FEEDS[name]?.feeds?.length, `${name} has feeds`);
    assert.equal(
      LAYOUT.fans[name].length,
      SOURCES[name].length,
      `${name}: every source placed on its own ray`,
    );
    for (const feed of FEEDS[name].feeds) {
      assert.ok(RING.includes(feed), `${name} feed ${feed} is a collection`);
    }
  }
});

test("no fan ray crosses any collection label", () => {
  for (const node of nodes) {
    for (const p of LAYOUT.fans[node.name].map(centered)) {
      for (const box of labelBoxes) {
        assert.ok(
          clears(node.dx - 0, node.dy - 0, p.x, p.y, box),
          `${node.name}/${p.source} ray clears every label`,
        );
      }
    }
  }
});

test("no source name lands on a label or a sibling source", () => {
  for (const node of nodes) {
    const placed = LAYOUT.fans[node.name].map(centered);
    placed.forEach((p, i) => {
      const sb = srcBoxFor(p.x, p.y, p.source);
      for (const box of labelBoxes) {
        assert.ok(!overlaps(sb, box), `${node.name}/${p.source} clear of labels`);
      }
      placed.slice(i + 1).forEach((q) => {
        assert.ok(
          !overlaps(sb, srcBoxFor(q.x, q.y, q.source)),
          `${node.name}: ${p.source} clear of ${q.source}`,
        );
      });
    });
  }
});

test("everything fits inside the canvas", () => {
  const inside = (box, what) => {
    assert.ok(box.l >= 0 && box.r <= LAYOUT.w, `${what} inside horizontally`);
    assert.ok(box.t >= 0 && box.b <= LAYOUT.h, `${what} inside vertically`);
  };
  for (const node of LAYOUT.nodes) {
    const box = labelBoxFor(centered(node));
    inside(
      { l: box.l + LAYOUT.cx, r: box.r + LAYOUT.cx, t: box.t + LAYOUT.cy, b: box.b + LAYOUT.cy },
      `label ${node.name}`,
    );
  }
  for (const [name, placed] of Object.entries(LAYOUT.fans)) {
    for (const p of placed) {
      const c = centered(p);
      const sb = srcBoxFor(c.x, c.y, p.source);
      inside(
        { l: sb.l + LAYOUT.cx, r: sb.r + LAYOUT.cx, t: sb.t + LAYOUT.cy, b: sb.b + LAYOUT.cy },
        `source ${name}/${p.source}`,
      );
    }
  }
});

test("the core and the ring sit inside the canvas", () => {
  assert.ok(LAYOUT.cx - LAYOUT.coreR > 0 && LAYOUT.cx + LAYOUT.coreR < LAYOUT.w);
  assert.ok(LAYOUT.cy - LAYOUT.r > 0 && LAYOUT.cy + LAYOUT.r < LAYOUT.h);
});
