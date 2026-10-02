import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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
  assert.equal(SOURCE_REACH_FIGURE, "700+");
});

// Owner, 2026-09-27: the source count is "documented upstream sources", never
// "websites", on the landing page and in Cedar's answers alike.
test("the source count is never worded as websites", () => {
  const files = [
    new URL("./sourceRotation.js", import.meta.url),
    new URL("./doorCedar.js", import.meta.url),
    new URL("../../pages/grove/PressGate.jsx", import.meta.url),
  ];
  for (const file of files) {
    const text = readFileSync(file, "utf8");
    assert.doesNotMatch(text, /(?:700\+?|SOURCE_REACH_FIGURE\}?|distinct|source) (?:source )?websites/i, file.pathname);
    assert.match(text, /(?:documented upstream|total) sources/, file.pathname);
  }
});
