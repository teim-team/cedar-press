// The door names ~forty source systems. Every one of them has to be a system
// a collection descriptor actually names, and no descriptor may quietly drop
// one the door still advertises. These two assertions are the whole contract.
import assert from "node:assert/strict";
import test from "node:test";

import { LAUNCH_COLLECTION } from "./collection.js";
import {
  PRESS_SOURCES,
  SOURCE_COUNT,
  SOURCE_GROUPS,
  SOURCE_PROSE,
  evidenceFor,
  isEvidenced,
} from "./pressSources.js";

test("every source the door names is named by a collection descriptor", () => {
  for (const source of PRESS_SOURCES) {
    assert.ok(
      isEvidenced(source),
      `"${source.name}" claims ${source.collections.join(", ")}, but no descriptor's sources ` +
        `prose contains "${evidenceFor(source)}". Either the workspace renamed it, or the door ` +
        `is advertising a system Cedar does not read.`,
    );
  }
});

test("every collection a source claims is a real storefront collection", () => {
  const known = new Set(LAUNCH_COLLECTION.map((entry) => entry.id));
  for (const source of PRESS_SOURCES) {
    assert.ok(source.collections.length > 0, `${source.name} names no collection`);
    for (const id of source.collections) {
      assert.ok(known.has(id), `${source.name} claims unknown collection "${id}"`);
    }
  }
});

test("every collection with sources prose contributes at least one named system", () => {
  // The other direction: a collection whose prose names systems but which no
  // entry here claims is a collection the door silently under-credits.
  const claimed = new Set(PRESS_SOURCES.flatMap((source) => source.collections));
  for (const [id, prose] of Object.entries(SOURCE_PROSE)) {
    if (!prose) continue;
    assert.ok(claimed.has(id), `${id} declares sources and no entry in pressSources.js reads them`);
  }
});

test("the count is derived, and the groups are non-empty", () => {
  assert.equal(SOURCE_COUNT, PRESS_SOURCES.length);
  assert.ok(SOURCE_COUNT > 30, `expected the door to name more than thirty systems, got ${SOURCE_COUNT}`);
  for (const group of SOURCE_GROUPS) {
    assert.ok(group.sources.length > 0, `${group.id} is an empty group`);
    assert.ok(group.label, `${group.id} has no label`);
  }
});

test("no source is listed twice under the same name", () => {
  const seen = new Map();
  for (const source of PRESS_SOURCES) {
    assert.ok(!seen.has(source.name), `"${source.name}" is listed twice`);
    seen.set(source.name, true);
  }
});
