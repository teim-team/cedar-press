// The citation register: the shape both intake paths (reader reports and the
// future automated watch) write into, and the page's zero-safety.

import assert from "node:assert/strict";
import test from "node:test";

import { LAUNCH_COLLECTION } from "./collection.js";
import { CITATIONS, REPORT_CITATION_HREF, citationCountFor } from "./pressCitations.js";

test("every recorded citation names a launch dataset and carries its fields", () => {
  for (const entry of CITATIONS) {
    assert.ok(LAUNCH_COLLECTION.some((d) => d.id === entry.datasetId), entry.id);
    assert.ok(entry.outlet && entry.piece && entry.version && entry.date && entry.href, entry.id);
  }
});

test("counts are zero-safe for every dataset and unknown ids", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    assert.ok(citationCountFor(dataset.id) >= 0, dataset.id);
  }
  assert.equal(citationCountFor("nope"), 0);
});

test("the report action is a mailto to the real contact address", () => {
  assert.match(REPORT_CITATION_HREF, /^mailto:contact@lumecon\.ai/);
});
