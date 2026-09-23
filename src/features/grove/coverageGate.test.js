// The coverage floor has to see files the tests never import.
//
// Node's own coverage leaves an unimported module out of its report instead
// of counting it as 0%, so a floor built on node's totals alone cannot be
// lowered by an entirely untested new file. Codex, on PR #105.
// `scripts/coverage-gate.mjs` enumerates the production files from git and
// counts the unloaded ones; these tests hold it to that, including an
// end-to-end run of the exact reproduction (an imported a.js, an unimported
// b.js) in a throwaway repository.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  account,
  belowFloor,
  lineCount,
  parseLcov,
  productionFiles,
  run,
} from "../../../scripts/coverage-gate.mjs";

const LCOV = `TN:
SF:src/a.js
FN:1,a
FNDA:1,a
FNF:1
FNH:1
BRDA:3,0,0,1
BRF:3
BRH:2
DA:1,1
LF:6
LH:4
end_of_record
SF:src/a.test.js
FNF:1
FNH:1
BRF:2
BRH:2
LF:3
LH:3
end_of_record
`;

test("lcov records are read per file", () => {
  const records = parseLcov(LCOV);
  assert.deepEqual(records.get("src/a.js"), { lf: 6, lh: 4, brf: 3, brh: 2, fnf: 1, fnh: 1 });
  assert.equal(records.size, 2);
});

test("a line count follows node's convention", () => {
  // Node counts every line of a loaded file, blank and comment lines too;
  // a trailing newline ends the last line rather than starting another.
  assert.equal(lineCount("a\n\n// c\nb\n"), 4);
  assert.equal(lineCount("a\nb"), 2);
});

test("an unloaded file counts as uncovered lines and is named", () => {
  const records = parseLcov(LCOV);
  const loadedOnly = account(records, ["src/a.js"], () => 0);
  assert.equal(loadedOnly.totals.lines, (100 * 4) / 6);
  assert.deepEqual(loadedOnly.unloaded, []);

  const withUntested = account(records, ["src/a.js", "src/b.js"], () => 3);
  assert.deepEqual(withUntested.unloaded, [{ file: "src/b.js", lines: 3 }]);
  assert.equal(withUntested.counts.lf, 9);
  assert.equal(withUntested.counts.lh, 4);
  assert.ok(withUntested.totals.lines < loadedOnly.totals.lines, "the untested file lowered nothing");
});

test("only the files in scope are totalled, so test files do not pad the number", () => {
  const records = parseLcov(LCOV);
  const { counts } = account(records, ["src/a.js"], () => 0);
  assert.equal(counts.lf, 6, "src/a.test.js leaked into the totals");
});

test("a metric under its floor is reported, one at or above it is not", () => {
  assert.deepEqual(belowFloor({ lines: 80, branches: 90, functions: 93 }, { lines: 81, branches: 90, functions: 93 }), [
    "lines",
  ]);
});

// ── The reproduction, end to end ────────────────────────────────────────────

function fixtureRepo({ withUntested }) {
  const dir = mkdtempSync(join(tmpdir(), "cedar-coverage-fixture-"));
  writeFileSync(join(dir, "package.json"), '{"type":"module"}\n');
  writeFileSync(join(dir, "a.js"), "export function a(x) {\n  // comment\n  if (x) return 1;\n\n  return 2;\n}\n");
  writeFileSync(
    join(dir, "a.test.js"),
    'import test from "node:test";\nimport { a } from "./a.js";\ntest("a", () => { a(1); });\n',
  );
  if (withUntested) writeFileSync(join(dir, "b.js"), "export function b() {\n  return 3;\n}\n");
  const init = spawnSync("git", ["init", "--quiet"], { cwd: dir });
  assert.equal(init.status, 0, "git init failed");
  return dir;
}

const quietRun = (cwd, floor) =>
  run({ cwd, tests: "a.test.js", scope: ["*.js"], floor, log: () => {}, quiet: true });

test("the file enumeration comes from git, test files excluded", () => {
  const dir = fixtureRepo({ withUntested: true });
  try {
    assert.deepEqual(productionFiles(dir, ["*.js"]), ["a.js", "b.js"]);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("an untested module lowers the floor's measurement and can fail it", () => {
  const floor = { lines: 60, branches: 0, functions: 0 };

  const clean = fixtureRepo({ withUntested: false });
  try {
    const result = quietRun(clean, floor);
    assert.equal(result.testsPassed, true);
    assert.equal(result.totals.lines, (100 * 4) / 6);
    assert.equal(result.ok, true, "a.js alone meets the fixture floor");
  } finally {
    rmSync(clean, { recursive: true, force: true });
  }

  // The same repository plus a module nothing imports. Node's own report
  // would still say 66.67% here; the gate counts b.js's three lines.
  const dirty = fixtureRepo({ withUntested: true });
  try {
    const result = quietRun(dirty, floor);
    assert.deepEqual(result.unloaded, [{ file: "b.js", lines: 3 }]);
    assert.equal(result.totals.lines, (100 * 4) / 9);
    assert.equal(result.ok, false, "the untested module left the gate green");
    assert.deepEqual(result.failing, ["lines"]);
  } finally {
    rmSync(dirty, { recursive: true, force: true });
  }
});

test("a failing suite fails the gate before coverage is read", () => {
  const dir = fixtureRepo({ withUntested: false });
  try {
    writeFileSync(
      join(dir, "a.test.js"),
      'import test from "node:test";\nimport assert from "node:assert";\ntest("a", () => { assert.fail("red"); });\n',
    );
    const result = quietRun(dir, { lines: 0, branches: 0, functions: 0 });
    assert.deepEqual(result, { ok: false, testsPassed: false });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
