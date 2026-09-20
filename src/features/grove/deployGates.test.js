// The gates run twice, and they have to be the same gates both times.
//
// `deploy.yml` checks and then ships; `ci.yml` checks a pull request. Two
// copies of one list is two things to forget, and the failure mode is quiet
// in the worst way: the pull request goes green against a shorter list, the
// merge goes red against the longer one, and the site stops updating without
// anybody being told. That is not hypothetical — it is what 2026-09-20 was.
//
// So the lists are compared rather than trusted. A step added to one and not
// the other fails here, which is before either of them runs.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const workflow = (name) =>
  readFileSync(new URL(`../../../.github/workflows/${name}`, import.meta.url), "utf8");

/**
 * The steps of a workflow, in order, as comparable strings.
 *
 * Deliberately a reader rather than a YAML parse: the repository has no YAML
 * dependency and adding one to compare two files it can read as text would be
 * the tail wagging the dog. A step is a `- uses:`/`- run:`/`- working-directory:`
 * line plus every line indented under it, which is enough to catch a changed
 * command, a changed action version, and a changed `with:` block.
 */
function steps(source) {
  const found = [];
  let current = null;
  for (const raw of source.split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim() || /^\s*#/.test(line)) continue;
    const opener = line.match(/^(\s+)- (uses|run|working-directory):\s*(.*)$/);
    if (opener) {
      if (current) found.push(current);
      current = { indent: opener[1].length, parts: [`${opener[2]}: ${opener[3]}`.trim()] };
      continue;
    }
    if (current) {
      const deeper = line.match(/^(\s+)(\S.*)$/);
      if (deeper && deeper[1].length > current.indent) {
        current.parts.push(deeper[2]);
        continue;
      }
      found.push(current);
      current = null;
    }
  }
  if (current) found.push(current);
  return found.map((step) => step.parts.join(" · "));
}

/** Everything up to the first step that builds the deployed site. */
function gatesOf(source) {
  const all = steps(source);
  const build = all.findIndex((step) => step.includes("npm run build:site"));
  return build === -1 ? all : all.slice(0, build);
}

test("the pull request runs the same gates the deploy runs", () => {
  const deploy = gatesOf(workflow("deploy.yml"));
  const checks = gatesOf(workflow("ci.yml"));
  assert.ok(deploy.length >= 8, `only found ${deploy.length} gate steps in deploy.yml`);
  assert.deepEqual(
    checks,
    deploy,
    "ci.yml and deploy.yml must run the same checks, in the same order",
  );
});

test("the deploy still builds and publishes after its gates", () => {
  // The slice above is only meaningful if the thing it slices at is there.
  const all = steps(workflow("deploy.yml"));
  const build = all.findIndex((step) => step.includes("npm run build:site"));
  assert.ok(build > 0, "deploy.yml no longer builds the site after its gates");
  const after = all.slice(build).join("\n");
  assert.match(after, /upload-pages-artifact/, "the Pages artifact step is gone");
  assert.match(after, /aws s3 sync/, "the S3 publish step is gone");
});

test("a pull request check holds no publishing credentials", () => {
  // A pull request can come from anywhere. The deploy's permissions are
  // valuable precisely because only `refs/heads/main` reaches them, and a
  // checks workflow that asked for them would hand that away.
  //
  // Read from the declaration rather than from the file's text: the first
  // version of this scanned the whole source and matched the comment in
  // `ci.yml` that explains which permissions it does NOT take, which is a
  // test that fails hardest on the file doing the right thing loudest.
  const checks = workflow("ci.yml");
  const granted = checks.match(/^permissions:\n((?:[ \t]+\S.*\n)+)/m);
  assert.ok(granted, "ci.yml declares no permissions block at all");
  assert.deepEqual(
    granted[1].trim().split("\n").map((line) => line.trim()),
    ["contents: read"],
    "a checks workflow needs to read the code and nothing else",
  );
  // And no step reaches for a credential the block did not grant.
  const used = steps(checks).join("\n");
  for (const credential of ["configure-aws-credentials", "deploy-pages", "upload-pages-artifact"]) {
    assert.ok(!used.includes(credential), `ci.yml must not run ${credential}`);
  }
});
