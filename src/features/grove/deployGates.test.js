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
//
// WHY THE READER BELOW PARSES LIST ITEMS RATHER THAN COMMANDS.
// Its first version opened a step only on a dashed `uses`, `run` or
// `working-directory`, which is how both workflows happen to be written
// today. Codex, on this pull request: a conventional `- name: …` step would
// not open a record — and worse than being skipped, its lines were swallowed
// as continuations of the step ABOVE it, so two steps parsed as one and a
// named gate could be added to one workflow alone without this noticing.
// A guard that stops seeing the thing it guards, as soon as somebody writes
// ordinary YAML, is not a guard. Every list item is a step now, and `name:`
// is dropped from the comparison rather than from the parse: two workflows
// that run the same command are the same gate whether or not one labels it.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const workflow = (name) =>
  readFileSync(new URL(`../../../.github/workflows/${name}`, import.meta.url), "utf8");

/**
 * Every step of every job, in order.
 *
 * Deliberately a reader rather than a YAML parse: the repository has no YAML
 * dependency, and adding one to compare two files it can already read as text
 * would be the tail wagging the dog. What it must get right is the shape of a
 * list item, which is what the fixtures at the bottom pin down.
 */
export function steps(source) {
  const found = [];
  let current = null;
  let inSteps = false;
  let stepsIndent = -1;
  const close = () => {
    if (current) found.push(current);
    current = null;
  };
  for (const raw of source.split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) continue;
    const indent = line.match(/^(\s*)/)[1].length;
    const bare = line.trim();
    if (/^steps:$/.test(bare)) {
      close();
      inSteps = true;
      stepsIndent = indent;
      continue;
    }
    if (!inSteps) continue;
    if (bare.startsWith("#")) continue;
    // Dedented back out of the list: this job's steps are done.
    if (indent <= stepsIndent) {
      close();
      inSteps = false;
      continue;
    }
    const item = line.match(/^(\s+)- (.*)$/);
    if (item) {
      close();
      current = { indent: item[1].length, keys: [] };
      if (item[2].trim()) current.keys.push(item[2].trim());
      continue;
    }
    if (current && indent > current.indent) current.keys.push(bare);
  }
  close();
  // `name:` is a label, not a difference. Everything else — the command, the
  // action version, the `with:` block, the working directory — is compared.
  return found.map((step) => step.keys.filter((key) => !/^name:\s/.test(key)).join(" · "));
}

/** Everything up to the first step that builds the deployed site. */
function gatesOf(source) {
  const all = steps(source);
  const build = all.findIndex((step) => step.includes("npm run build:site"));
  return build === -1 ? all : all.slice(0, build);
}

/**
 * Every `permissions:` block in the file, as a list of its entries.
 *
 * All of them, because a job-level block overrides the workflow-level one —
 * Codex, on this pull request: reading only the top one means `jobs.gates`
 * could quietly gain `pages: write` while the test still reported that the
 * checks workflow takes nothing.
 */
export function permissionBlocks(source) {
  const lines = source.split("\n");
  const blocks = [];
  for (let i = 0; i < lines.length; i += 1) {
    const opener = lines[i].match(/^(\s*)permissions:\s*$/);
    if (!opener) continue;
    const indent = opener[1].length;
    const entries = [];
    for (let j = i + 1; j < lines.length; j += 1) {
      const line = lines[j].replace(/\s+$/, "");
      if (!line.trim()) break;
      if (/^\s*#/.test(line)) continue;
      const deeper = line.match(/^(\s*)(\S.*)$/);
      if (!deeper || deeper[1].length <= indent) break;
      entries.push(deeper[2].trim());
    }
    blocks.push(entries);
  }
  return blocks;
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

test("the deploy still builds and publishes down both paths", () => {
  // The slice above is only meaningful if the thing it slices at is there —
  // and "publishes" is two destinations, not one. Codex, on this pull
  // request: uploading a Pages artifact is not deploying it, so asserting the
  // upload alone would miss the `deploy` job disappearing entirely.
  const all = steps(workflow("deploy.yml"));
  const build = all.findIndex((step) => step.includes("npm run build:site"));
  assert.ok(build > 0, "deploy.yml no longer builds the site after its gates");
  const after = all.slice(build).join("\n");
  for (const published of ["upload-pages-artifact", "deploy-pages", "aws s3 sync"]) {
    assert.match(after, new RegExp(published), `the ${published} step is gone`);
  }
});

test("a pull request check holds no publishing credentials", () => {
  // A pull request can come from anywhere. The deploy's permissions are
  // valuable precisely because only `refs/heads/main` reaches them, and a
  // checks workflow that asked for them would hand that away.
  //
  // Read from the declarations rather than from the file's text: the first
  // version of this scanned the whole source and matched the comment in
  // `ci.yml` that explains which permissions it does NOT take, which is a
  // test that fails hardest on the file doing the right thing loudest.
  const blocks = permissionBlocks(workflow("ci.yml"));
  assert.ok(blocks.length > 0, "ci.yml declares no permissions block at all");
  for (const entries of blocks) {
    assert.deepEqual(
      entries,
      ["contents: read"],
      "a checks workflow needs to read the code and nothing else",
    );
  }
  const used = steps(workflow("ci.yml")).join("\n");
  for (const credential of ["configure-aws-credentials", "deploy-pages", "upload-pages-artifact"]) {
    assert.ok(!used.includes(credential), `ci.yml must not run ${credential}`);
  }
});

// ── The shapes the reader has to survive ────────────────────────────────────
// Fixtures rather than a note, because each of these is a way the guard could
// have gone quietly blind, and a mutation nobody can run later is a claim.

const NAMED = `jobs:
  gates:
    steps:
      - uses: actions/checkout@v7
      - name: Lint everything
        run: npm run lint
      - run: npm run test
`;

test("a named step is still a step", () => {
  assert.deepEqual(steps(NAMED), [
    "uses: actions/checkout@v7",
    "run: npm run lint",
    "run: npm run test",
  ]);
});

test("a gate added under a name is a difference", () => {
  const without = NAMED.replace("      - name: Lint everything\n        run: npm run lint\n", "");
  assert.notDeepEqual(steps(NAMED), steps(without));
});

test("two jobs' steps do not run together", () => {
  const two = `jobs:
  gates:
    steps:
      - run: npm run lint
  deploy:
    needs: gates
    steps:
      - uses: actions/deploy-pages@v5
`;
  assert.deepEqual(steps(two), ["run: npm run lint", "uses: actions/deploy-pages@v5"]);
});

test("a job-level permissions override is seen", () => {
  const overridden = `permissions:
  contents: read

jobs:
  gates:
    permissions:
      contents: read
      pages: write
    steps:
      - run: npm run lint
`;
  const blocks = permissionBlocks(overridden);
  assert.equal(blocks.length, 2, "both the workflow and the job block are read");
  assert.deepEqual(blocks[1], ["contents: read", "pages: write"]);
  // Which is what the assertion above rejects.
  assert.throws(() => {
    for (const entries of blocks) assert.deepEqual(entries, ["contents: read"]);
  });
});
