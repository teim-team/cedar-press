import { test } from "node:test";
import assert from "node:assert/strict";
import { easeOut, tickValue } from "./useTicker.js";

test("the ease starts at 0, ends at 1 and settles rather than races", () => {
  assert.equal(easeOut(0), 0);
  assert.equal(easeOut(1), 1);
  assert.ok(easeOut(0.5) > 0.5, "most of the distance is covered early");
});

test("a figure lands exactly on its value and never overshoots", () => {
  assert.equal(tickValue(0, 8595567, 1), 8595567);
  assert.equal(tickValue(0, 8595567, 2), 8595567);
  assert.equal(tickValue(0, 14, 0), 0);
  for (let t = 0; t <= 1; t += 0.05) {
    const v = tickValue(0, 8595567, t);
    assert.ok(Number.isInteger(v) && v >= 0 && v <= 8595567, `${t}: ${v}`);
  }
});

test("a year can tick backwards to how far back the record goes", () => {
  assert.equal(tickValue(2026, 1880, 0), 2026);
  assert.equal(tickValue(2026, 1880, 1), 1880);
  const mid = tickValue(2026, 1880, 0.5);
  assert.ok(mid < 2026 && mid > 1880);
});
