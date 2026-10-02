import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseDumpArguments, renderDump } from "../../../scripts/dump.mjs";
import { parseDocumentArguments, renderDocuments, staleDocuments } from "../../../scripts/docs-markdown.mjs";

const root = fileURLToPath(new URL("../../../", import.meta.url));
const dump = join(root, "scripts", "dump.mjs");
const docs = join(root, "scripts", "docs-markdown.mjs");
const run = (file, args, cwd = root) => spawnSync(process.execPath, [file, ...args], { cwd, encoding: "utf8" });

test("dispatch rejects ambiguous or incomplete requests before doing work", () => {
  for (const args of [[], ["--kind"], ["--kind", "unknown"], ["--kind", "press", "--kind", "access"], ["--kind", "press", "--target"], ["--kind", "press", "--oops"], ["--kind", "access", "--check"]]) assert.throws(() => parseDumpArguments(args));
  for (const args of [[], ["--kind"], ["--kind", "unknown"], ["--kind", "all", "--kind", "guides"], ["--kind", "guides", "--target", "x"], ["--kind", "guides", "--check", "--check"]]) assert.throws(() => parseDocumentArguments(args));
  assert.deepEqual(parseDumpArguments(["--kind", "collection", "--target", "a path.json", "--check"]), { kind: "collection", target: "a path.json", check: true });
});

test("each dump CLI emits exactly its imported renderer output", async () => {
  for (const kind of ["access", "collection", "press"]) {
    const actual = run(dump, ["--kind", kind]);
    assert.equal(actual.status, 0, actual.stderr);
    assert.equal(actual.stdout, await renderDump(kind), kind);
    assert.ok(JSON.parse(actual.stdout), kind);
  }
  const check = run(dump, ["--kind", "press", "--check"]);
  assert.equal(check.status, 0, check.stderr);
});

test("dump target paths preserve spaces and check never writes missing or stale files", async () => {
  const dir = mkdtempSync(join(tmpdir(), "press commands "));
  const target = join(dir, "access rules.json");
  try {
    let result = run(dump, ["--kind", "access", "--check", "--target", target], dir);
    assert.equal(result.status, 1, result.stderr);
    assert.equal(existsSync(target), false);
    writeFileSync(target, "stale\n");
    result = run(dump, ["--kind", "access", "--check", "--target", target], dir);
    assert.equal(result.status, 1, result.stderr);
    assert.equal(readFileSync(target, "utf8"), "stale\n");
    result = run(dump, ["--kind", "access", "--target", "access rules.json"], dir);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(readFileSync(target, "utf8"), await renderDump("access"));
    assert.equal(run(dump, ["--kind", "access", "--check", "--target", target], dir).status, 0);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test("all document outputs are exactly the three supported selections and remain current", () => {
  const byKind = ["codebook", "field-map", "guides"].map(renderDocuments);
  const all = renderDocuments("all");
  assert.deepEqual(all, Object.assign({}, ...byKind));
  assert.equal(Object.keys(all).length, byKind.reduce((count, files) => count + Object.keys(files).length, 0));
  const before = Object.fromEntries(Object.keys(all).map(path => [path, readFileSync(path, "utf8")]));
  for (const [path, expected] of Object.entries(all)) assert.equal(before[path], expected, path);
  const check = run(docs, ["--kind", "all", "--check"]);
  assert.equal(check.status, 0, check.stderr);
  for (const [path, expected] of Object.entries(before)) assert.equal(readFileSync(path, "utf8"), expected);
});

test("the maintained scripts inventory stays below twenty without old dispatch wrappers", () => {
  const files = readdirSync(join(root, "scripts"), { withFileTypes: true }).filter(entry => entry.isFile()).map(entry => entry.name);
  assert.ok(files.length < 20, files.join(", "));
  for (const name of ["dump-access.mjs", "dump-collection.mjs", "dump-press.mjs", "codebook-markdown.mjs", "field-map-markdown.mjs", "guides-markdown.mjs"]) assert.equal(files.includes(name), false, name);
});

test("one stale or missing document fails the shared all-output check without creating or changing files", () => {
  const dir = mkdtempSync(join(tmpdir(), "press document check "));
  try {
    const good = join(dir, "current.md"), stale = join(dir, "stale.md"), missing = join(dir, "missing.md");
    writeFileSync(good, "current\n"); writeFileSync(stale, "old\n");
    assert.deepEqual(staleDocuments({ [good]: "current\n", [stale]: "new\n", [missing]: "expected\n" }), [stale, missing]);
    assert.equal(readFileSync(stale, "utf8"), "old\n");
    assert.equal(existsSync(missing), false);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
