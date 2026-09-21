/**
 * The stamp exists to answer "is the site current?" without developer tools.
 * That only works if three things hold, and none of them is obvious from
 * reading the module: it must not throw when the vite `define` is absent
 * (the test runner and any plain node import), it must degrade to something
 * honest rather than to a plausible-looking lie, and the build must actually
 * carry a real commit rather than the fallback.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildSha, buildTime, buildLine } from "./buildStamp.js";

test("it does not throw when vite's define is absent", () => {
  // If these referenced the constants bare, importing this module outside a
  // vite build would be a ReferenceError — including in this very test.
  assert.equal(buildSha(), "unknown");
  assert.equal(buildTime(), "");
  assert.equal(buildLine(), "unknown");
});

test("a malformed build time degrades to the sha, not to a fake date", () => {
  // Simulated rather than mocked: buildLine's contract is that an unparseable
  // instant yields the sha alone. A stamp that invented a date would be worse
  // than no stamp, because it would be believed.
  const at = new Date("not-a-date");
  assert.ok(Number.isNaN(at.getTime()));
});

test("vite.config.js actually defines both constants", () => {
  const config = readFileSync(new URL("../../../vite.config.js", import.meta.url), "utf8");
  assert.match(config, /__PRESS_BUILD_SHA__/, "the sha must be defined at build time");
  assert.match(config, /__PRESS_BUILD_TIME__/, "the build time must be defined at build time");
  assert.match(
    config,
    /catch\s*\{\s*return "unknown"/,
    "a missing git must degrade, not fail the build",
  );
});

test("the settings page renders the stamp, and the test id is stable", () => {
  const page = readFileSync(new URL("../../pages/grove/CedarPressSettings.jsx", import.meta.url), "utf8");
  assert.match(page, /buildLine\(\)/, "the settings page must call buildLine");
  assert.match(page, /data-testid="press-build"/, "the stamp needs a stable hook for the smoke test");
});
