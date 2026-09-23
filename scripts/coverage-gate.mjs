#!/usr/bin/env node
// The frontend suite's coverage floor, measured over every production module
// rather than over whichever modules the tests happen to import.
//
// WHY THIS IS A SCRIPT AND NOT A FLAG. Node's built-in coverage reports the
// files a test run LOADED. A module no test imports is not reported as 0% --
// it is not reported at all, and `--test-coverage-include` does not change
// that (checked on node 22.22: an imported a.js and an unimported b.js report
// a.js alone, with or without the include glob). So the flags this replaced
// (`--test-coverage-lines=95` and friends) held a floor that an entirely
// untested new module could never lower: the one regression a coverage
// ratchet exists to catch. Codex, on PR #105. On 2026-09-23 twenty production
// modules, 1,110 lines, sat outside the old measurement for exactly this
// reason.
//
// WHAT IS MEASURED. Every tracked or untracked-but-not-ignored file matching
// SCOPE, minus test files. The enumeration comes from git, not from the
// coverage report, so a file the suite never touches is still on the list.
// A module the suite loaded contributes node's own line, branch and function
// counts. A module it never loaded contributes every one of its lines as
// uncovered -- node's own convention, since node counts every source line of
// a loaded file, blank and comment lines included (verified on all 57 loaded
// files: LF equals the line count). Its functions and branches cannot be
// counted without executing or parsing it, so an unloaded module lowers the
// LINE total only, and is named in the output either way.
//
// Test files are not in the totals. A suite that covers its own test files
// reports a number that means nothing -- the same rule .coveragerc applies
// to the API suite.
//
// WHAT IS NOT MEASURED. `.jsx` files: node cannot load JSX without a
// transform, so no node-side floor can say anything about them. The
// Playwright smoke run (`npm run test:smoke`) is what exercises the pages
// and components.

import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));

export const TESTS = "src/features/grove/*.test.js";
export const SCOPE = ["src/**/*.js", "scripts/*.mjs"];

// Measured 2026-09-23 over 279 passing tests: 83.87 lines / 82.76 branches /
// 89.16 functions, over 58 production files of which 20 (1,111 lines) no
// test loads. The floor sits at or just below each.
//
// These are lower than the 95 / 87 / 93 they replace because they measure a
// different, larger set, not because coverage fell. The old figures counted
// the test files themselves (95.44 / 87.82 / 93.80 on the same run) and left
// out every unimported module; production files alone, loaded ones only, are
// 93.34 / 82.76 / 89.16, and adding the unloaded modules takes lines to
// 83.87. Branches and functions do not move with the unloaded modules
// because those cannot be counted without loading them (above).
//
// It is a ratchet against regression, not a target: raise it when real
// coverage rises, never lower it to make a red run green.
export const FLOOR = { lines: 83, branches: 82, functions: 89 };

const isTest = (file) => /\.test\.[cm]?js$/.test(file);

/** Every production file in scope, from git, so untested files are included. */
export function productionFiles(cwd = ROOT, scope = SCOPE) {
  const listed = spawnSync(
    "git",
    [
      "ls-files",
      "--cached",
      "--others",
      "--exclude-standard",
      "-z",
      "--",
      ...scope.map((pattern) => `:(glob)${pattern}`),
    ],
    { cwd, encoding: "utf8" },
  );
  if (listed.status !== 0) {
    throw new Error(`git ls-files failed in ${cwd}: ${listed.stderr}`);
  }
  return [...new Set(listed.stdout.split("\0").filter(Boolean))]
    .filter((file) => !isTest(file))
    .filter((file) => existsSync(join(cwd, file)))
    .sort();
}

/** Per-file counts out of an lcov report, keyed by the path as written. */
export function parseLcov(text) {
  const records = new Map();
  let current = null;
  for (const line of text.split("\n")) {
    const [key, ...rest] = line.trim().split(":");
    const value = rest.join(":");
    if (key === "SF") {
      current = { lf: 0, lh: 0, brf: 0, brh: 0, fnf: 0, fnh: 0 };
      records.set(value, current);
    } else if (key === "end_of_record") {
      current = null;
    } else if (current && ["LF", "LH", "BRF", "BRH", "FNF", "FNH"].includes(key)) {
      current[key.toLowerCase()] = Number(value);
    }
  }
  return records;
}

/** Node's line count for a file: every line, the trailing newline not a line. */
export function lineCount(source) {
  const parts = source.split("\n");
  return source.endsWith("\n") ? parts.length - 1 : parts.length;
}

const pct = (hit, found) => (found === 0 ? 100 : (100 * hit) / found);

/**
 * Totals over `files`, taking loaded files from `records` and counting every
 * other file as `lines(file)` uncovered lines.
 */
export function account(records, files, lines) {
  const sum = { lf: 0, lh: 0, brf: 0, brh: 0, fnf: 0, fnh: 0 };
  const unloaded = [];
  for (const file of files) {
    const record = records.get(file);
    if (record) {
      for (const key of Object.keys(sum)) sum[key] += record[key];
    } else {
      const count = lines(file);
      unloaded.push({ file, lines: count });
      sum.lf += count;
    }
  }
  return {
    unloaded,
    counts: sum,
    totals: {
      lines: pct(sum.lh, sum.lf),
      branches: pct(sum.brh, sum.brf),
      functions: pct(sum.fnh, sum.fnf),
    },
  };
}

/** Which metrics are under their floor. */
export function belowFloor(totals, floor = FLOOR) {
  return Object.keys(floor).filter((metric) => totals[metric] < floor[metric]);
}

/** Run the suite with coverage, then hold the whole production set to the floor. */
export function run({
  cwd = ROOT,
  tests = TESTS,
  scope = SCOPE,
  floor = FLOOR,
  log = console.log,
  quiet = false,
} = {}) {
  const dir = mkdtempSync(join(tmpdir(), "cedar-coverage-"));
  const lcovPath = join(dir, "lcov.info");
  try {
    // A test that runs this gate against a fixture is itself running under
    // the node test runner: without these two stripped, the child would
    // report to the parent's runner and write into the parent's coverage.
    const env = { ...process.env };
    delete env.NODE_TEST_CONTEXT;
    delete env.NODE_V8_COVERAGE;
    const suite = spawnSync(
      process.execPath,
      [
        "--experimental-test-coverage",
        "--test-reporter=spec",
        "--test-reporter-destination=stdout",
        "--test-reporter=lcov",
        `--test-reporter-destination=${lcovPath}`,
        "--test",
        tests,
      ],
      { cwd, env, stdio: ["ignore", quiet ? "ignore" : "inherit", quiet ? "ignore" : "inherit"] },
    );
    if (suite.status !== 0) {
      log(`\nThe test suite failed (exit ${suite.status}); coverage was not assessed.`);
      return { ok: false, testsPassed: false };
    }
    const records = parseLcov(readFileSync(lcovPath, "utf8"));
    const files = productionFiles(cwd, scope);
    const result = account(records, files, (file) =>
      lineCount(readFileSync(join(cwd, file), "utf8")),
    );
    const failing = belowFloor(result.totals, floor);

    log(`\nCoverage over ${files.length} production files (${scope.join(", ")}, tests excluded):`);
    if (result.unloaded.length) {
      log(`  ${result.unloaded.length} never loaded by the suite, every line counted as uncovered:`);
      for (const { file, lines } of result.unloaded) log(`    ${file} (${lines} lines)`);
    }
    for (const metric of Object.keys(floor)) {
      const mark = failing.includes(metric) ? "BELOW FLOOR" : "ok";
      log(`  ${metric.padEnd(9)} ${result.totals[metric].toFixed(2).padStart(6)}%  floor ${floor[metric]}  ${mark}`);
    }
    return { ok: failing.length === 0, testsPassed: true, failing, ...result };
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = run();
  process.exit(result.ok ? 0 : 1);
}
