import { test } from "node:test";
import assert from "node:assert/strict";
import { SOURCE_REACH_FIGURE, SOURCE_ROTATION, SOURCE_ROTATION_ORDER } from "./sourceRotation.js";

test("no source label appears twice, even with different case or spacing", () => {
  const norm = SOURCE_ROTATION.map((l) => l.toLowerCase().replace(/\s+/g, " ").trim());
  const dupes = norm.filter((l, i) => norm.indexOf(l) !== i);
  assert.deepEqual(dupes, []);
});

test("the scrambled order holds every label exactly once", () => {
  assert.equal(SOURCE_ROTATION_ORDER.length, SOURCE_ROTATION.length);
  assert.deepEqual([...SOURCE_ROTATION_ORDER].sort(), [...SOURCE_ROTATION].sort());
});

test("replaced labels are gone, so a source is not named twice", () => {
  for (const gone of [
    "Building permit and inspection records",
    "USPTO patent grants",
    "USPTO patent assignment records",
    "PatentsView patent data",
    "Credit rating agency announcements",
  ]) {
    assert.ok(!SOURCE_ROTATION.includes(gone), gone);
  }
});

// The website count is the owner's stated distinct-site figure, and it
// never moves because labels were added to this list.
test("the reach figure is the stated one", () => {
  assert.equal(SOURCE_REACH_FIGURE, "600+");
});
