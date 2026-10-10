import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { RELEASED_SOURCE_KINDS, SOURCE_REACH_FIGURE, SOURCE_ROTATION, SOURCE_ROTATION_ORDER } from "./sourceRotation.js";
import { PRESS_SOURCES } from "./pressSources.js";

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

// Owner, 2026-09-27: gaming is not a Cedar Press collection, so the door
// names none of its sources.
test("no gaming source is named on the Cedar Press door", () => {
  for (const label of SOURCE_ROTATION) assert.doesNotMatch(label, /gaming|casino|NIGC/i, label);
});

// The figure is measured (2026-10-06): the kinds of source the released
// collections name, counted from pressSources.js. It never moves because
// labels were added to this list, and it is never an unmeasured "700+".
test("the reach figure is the measured count of kinds of source", () => {
  const measured = PRESS_SOURCES.filter((source) => !source.declared).length;
  assert.equal(RELEASED_SOURCE_KINDS, measured);
  assert.equal(SOURCE_REACH_FIGURE, String(measured));
  assert.doesNotMatch(SOURCE_REACH_FIGURE, /\+/);
});

// Owner, 2026-09-27: the source count is never "websites". Owner,
// 2026-10-06: the landing page and Cedar's answers state no source count at
// all, and no surface repeats the unmeasured 700.
test("the source count is never worded as websites, and no page states one", () => {
  const files = [
    new URL("./sourceRotation.js", import.meta.url),
    new URL("./doorCedar.js", import.meta.url),
    new URL("../../pages/grove/PressGate.jsx", import.meta.url),
  ];
  for (const file of files) {
    const text = readFileSync(file, "utf8");
    assert.doesNotMatch(text, /(?:700\+?|SOURCE_REACH_FIGURE\}?|distinct|source) (?:source )?websites/i, file.pathname);
    if (!file.pathname.endsWith("sourceRotation.js")) assert.doesNotMatch(text, /kinds of (?:public )?source/, file.pathname);
    assert.doesNotMatch(text, /700\+|more than 700|documented upstream sources|total sources/, file.pathname);
  }
});
