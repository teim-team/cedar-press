// The ecosystem diagram's geometry, held to account. The solver in
// pressEcosystem.js promises that every collection is on the ring with a
// point for every record it is built from, that those points sit inside the
// ring and clear the entity layer in the middle, that no two collection
// labels land on each other, and that the whole resting figure fits a canvas
// the ring takes at least half of, which is what makes it readable at a
// third of the page. Copy edits to RING or SOURCES re-run the solver; this
// file makes sure the promises survive them.
import test from "node:test";
import assert from "node:assert/strict";
import {
  ECOSYSTEM,
  PROPER_NOUN,
  RING,
  SOURCES,
  FEEDS,
  LAYOUT,
  labelBoxFor,
  labelLines,
  nearestToCentre,
  overlaps,
} from "./pressEcosystem.js";
import { STOREFRONT_CATALOG } from "./pressCatalog.js";

const centered = (p) => ({
  ...p,
  x: p.x - LAYOUT.cx,
  y: p.y - LAYOUT.cy,
  ...(p.dx == null ? {} : { dx: p.dx - LAYOUT.cx, dy: p.dy - LAYOUT.cy }),
});
const nodes = LAYOUT.nodes.map(centered);
const labelBoxes = nodes.map(labelBoxFor);

// The ring is the storefront: every collection sold has a place on it and a
// declaration behind it, and nothing is declared that the storefront does
// not sell. This is the drift the diagram had twice, in both directions.
test("the ring is exactly the storefront catalog", () => {
  assert.deepEqual(RING, STOREFRONT_CATALOG.map((entry) => entry.short));
  const ids = new Set(STOREFRONT_CATALOG.map((entry) => entry.id));
  for (const id of ids) {
    assert.ok(ECOSYSTEM[id]?.sources?.length, `${id} declares no sources`);
    assert.ok(ECOSYSTEM[id]?.feeds?.length, `${id} declares no feeds`);
    assert.ok(ECOSYSTEM[id]?.line, `${id} has no sentence`);
    for (const feed of ECOSYSTEM[id].feeds) {
      assert.ok(ids.has(feed), `${id} is fed by ${feed}, which the storefront does not sell`);
      assert.notEqual(feed, id, `${id} feeds itself`);
    }
  }
  for (const id of Object.keys(ECOSYSTEM)) {
    assert.ok(ids.has(id), `${id} is declared and not sold`);
  }
});

// A source name is read into a sentence, and the first word decides whether
// it keeps its capital. Every source must be one or the other on purpose:
// an agency name lowercased reads as a typo, and a common noun capitalised
// reads as a proper noun nobody can look up.
test("every source is either a proper noun or reads lowercased", () => {
  for (const [id, record] of Object.entries(ECOSYSTEM)) {
    for (const source of record.sources) {
      const proper = PROPER_NOUN.test(source);
      const acronymLed = /^[A-Z]{2,}/.test(source);
      assert.ok(
        proper || !acronymLed,
        `${id}: "${source}" starts with an acronym PROPER_NOUN does not know`,
      );
    }
  }
});

test("every collection is on the ring with a fan", () => {
  assert.equal(LAYOUT.nodes.length, RING.length);
  for (const name of RING) {
    assert.ok(SOURCES[name]?.length, `${name} has sources`);
    assert.ok(FEEDS[name]?.feeds?.length, `${name} has feeds`);
    assert.deepEqual(
      LAYOUT.fans[name].map((p) => p.source),
      SOURCES[name],
      `${name}: every source placed, in the order it is declared`,
    );
    for (const feed of FEEDS[name].feeds) {
      assert.ok(RING.includes(feed), `${name} feed ${feed} is a collection`);
    }
  }
});

// The records a collection is built from sit inside the ring, between the
// collection's own point and the entity layer: that is the direction they
// travel, and it is the only region twelve readable labels leave free.
test("every source point sits inside the ring and its ray clears the entity layer", () => {
  for (const node of nodes) {
    for (const p of LAYOUT.fans[node.name].map(centered)) {
      const radius = Math.hypot(p.x, p.y);
      assert.ok(radius < LAYOUT.dotR - 8, `${node.name}/${p.source} inside the ring`);
      assert.ok(radius > LAYOUT.coreR + 8, `${node.name}/${p.source} clear of the core`);
      assert.ok(
        nearestToCentre(node.dx, node.dy, p.x, p.y) > LAYOUT.coreR + 4,
        `${node.name}/${p.source} ray clears the core`,
      );
    }
  }
});

test("sibling sources are distinct points, spread about their collection's spoke", () => {
  for (const node of nodes) {
    const placed = LAYOUT.fans[node.name].map(centered);
    placed.forEach((p, i) => {
      placed.slice(i + 1).forEach((q) => {
        assert.ok(Math.hypot(p.x - q.x, p.y - q.y) >= 14, `${node.name}: ${p.source} apart from ${q.source}`);
      });
    });
    // Balanced about the spoke, so a fan reads as belonging to its collection.
    // A circular mean (of unit vectors), because a fan that straddles the
    // angle where atan2 wraps would otherwise average to the far side.
    const sumX = placed.reduce((sum, p) => sum + p.x / Math.hypot(p.x, p.y), 0);
    const sumY = placed.reduce((sum, p) => sum + p.y / Math.hypot(p.x, p.y), 0);
    const mean = Math.atan2(sumY, sumX);
    const spoke = Math.atan2(node.dy, node.dx);
    const wrapped = Math.atan2(Math.sin(mean - spoke), Math.cos(mean - spoke));
    assert.ok(Math.abs(wrapped) < 0.01, `${node.name}: fan centred on its spoke`);
  }
});

// Two-line labels are what let the ring be small: a long name breaks at the
// space nearest its middle, and a single word or a short name stays whole.
test("long names break onto two balanced lines and short ones stay whole", () => {
  assert.deepEqual(labelLines("Deals"), ["Deals"]);
  assert.deepEqual(labelLines("Subcontracting"), ["Subcontracting"]);
  assert.deepEqual(labelLines("Native-Owned Businesses"), ["Native-Owned", "Businesses"]);
  assert.deepEqual(labelLines("Prime Contracting"), ["Prime", "Contracting"]);
  for (const name of RING) {
    const lines = labelLines(name);
    assert.ok(lines.length <= 2, `${name} is at most two lines`);
    assert.equal(lines.join(" "), name, `${name} keeps every word`);
  }
});

test("no two collection labels land on each other", () => {
  labelBoxes.forEach((a, i) => {
    labelBoxes.slice(i + 1).forEach((b, j) => {
      assert.ok(!overlaps(a, b), `${nodes[i].name} clear of ${nodes[i + 1 + j].name}`);
    });
  });
});

test("everything fits inside the canvas, and the ring takes at least half of it", () => {
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
      inside({ l: p.x - 4, r: p.x + 4, t: p.y - 4, b: p.y + 4 }, `source ${name}/${p.source}`);
    }
  }
  // Readable at a third of the page: the ring, not the margins, is the figure.
  assert.ok((2 * LAYOUT.r) / LAYOUT.w >= 0.5, `ring is ${((2 * LAYOUT.r) / LAYOUT.w).toFixed(2)} of the canvas width`);
  assert.ok(LAYOUT.w <= 800, `canvas ${LAYOUT.w} wide would scale 22px labels below 12px at a third of the page`);
});

test("the core and the ring sit inside the canvas", () => {
  assert.ok(LAYOUT.cx - LAYOUT.coreR > 0 && LAYOUT.cx + LAYOUT.coreR < LAYOUT.w);
  assert.ok(LAYOUT.cy - LAYOUT.r > 0 && LAYOUT.cy + LAYOUT.r < LAYOUT.h);
});
