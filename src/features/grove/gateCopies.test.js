// The gate is written down in four places, and they have to agree.
//
// The Makefile names each gate; ci.yml and deploy.yml run them (and
// deployGates.test.js holds those two to each other); AGENTS.md carries a
// copy a contributor is told to trust; server/pyproject.toml decides what
// the Python audit has to cover. Codex, on PR #105, found three ways they
// had already drifted:
//
//   - `make check`, the aggregate a contributor runs, left out the audits
//     CI enforces, so a vulnerable dependency passed locally and failed in CI;
//   - AGENTS.md's "exact CI check list" left out the smoke suite and both
//     audits, swapped `make test-python` for a bare unittest call without
//     warnings-as-errors or coverage, and installed none of the tools the
//     Makefile's gates call;
//   - the Python audit resolved `--extra dev` alone, so the `postgres` group
//     (psycopg, psycopg_pool) was never audited.
//
// Each is compared here rather than trusted.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../../../${path}`, import.meta.url), "utf8");

/**
 * Every `run:` command of a workflow, in order. A block scalar (`run: |`)
 * is read as its lines joined by newlines, so deploy.yml's publish step is
 * one command rather than a stray "|".
 */
export function runSteps(source) {
  const runs = [];
  const lines = source.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const match = lines[i].match(/^(\s+)(?:- )?run:\s*(.*)$/);
    if (!match) continue;
    if (!/^[|>][-+]?$/.test(match[2].trim())) {
      runs.push(match[2].trim());
      continue;
    }
    const body = [];
    for (let j = i + 1; j < lines.length; j += 1) {
      if (lines[j].trim() && lines[j].match(/^(\s*)/)[1].length <= match[1].length) break;
      body.push(lines[j].trim());
      i = j;
    }
    runs.push(body.filter(Boolean).join("\n"));
  }
  return runs;
}

/**
 * One job's lines of a workflow (from its `  <name>:` key to the next job),
 * so a check list is compared with the job that runs it and not with every
 * job in the file.
 */
export function jobSource(source, name) {
  const lines = source.split("\n");
  const start = lines.findIndex((line) => line === `  ${name}:`);
  if (start === -1) return "";
  const body = [];
  for (const line of lines.slice(start + 1)) {
    if (/^ {2}[A-Za-z0-9_-]+:\s*$/.test(line) || /^\S/.test(line)) break;
    body.push(line);
  }
  return body.join("\n");
}

/** The fenced block that follows an `<!-- gate:<name> -->` marker, as commands. */
export function markedBlock(markdown, name) {
  const marker = `<!-- gate:${name} -->`;
  const at = markdown.indexOf(marker);
  if (at === -1) return null;
  const fence = markdown.slice(at + marker.length).match(/^\s*```[a-z]*\n([\s\S]*?)```/);
  if (!fence) return null;
  return fence[1]
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
}

/** Each Makefile target's prerequisites and recipe lines. */
export function makeTargets(source) {
  const targets = new Map();
  let current = null;
  const lines = source.replace(/\\\n\s*/g, " ").split("\n");
  for (const line of lines) {
    const rule = line.match(/^([A-Za-z0-9_-]+):(?!=)\s*(.*)$/);
    if (rule) {
      current = { deps: rule[2].split(/\s+/).filter(Boolean), recipe: [] };
      targets.set(rule[1], current);
      continue;
    }
    if (current && line.startsWith("\t")) {
      current.recipe.push(line.trim().replace(/^@/, "").replace(/\s+/g, " "));
    } else if (line.trim() && !line.startsWith("#")) {
      current = null;
    }
  }
  return targets;
}

/** Every target `name` runs, itself included. */
function reachable(targets, name, seen = new Set()) {
  if (seen.has(name)) return seen;
  seen.add(name);
  for (const dep of targets.get(name)?.deps ?? []) reachable(targets, dep, seen);
  return seen;
}

/** The names of `[project.optional-dependencies]` in a pyproject file. */
export function optionalGroups(pyproject) {
  const section = pyproject.split(/^\[project\.optional-dependencies\]\s*$/m)[1];
  if (!section) return {};
  const body = section.split(/^\[/m)[0];
  const groups = {};
  for (const match of body.matchAll(/^([A-Za-z0-9_-]+)\s*=\s*\[([\s\S]*?)\]\s*$/gm)) {
    groups[match[1]] = [...match[2].matchAll(/"([A-Za-z0-9_.-]+)/g)].map((m) => m[1].toLowerCase());
  }
  return groups;
}

const makefile = () => makeTargets(read("Makefile"));

// ── `make check` covers every gate ──────────────────────────────────────────

test("make check reaches every make target a workflow runs", () => {
  const targets = makefile();
  assert.ok(targets.has("check"), "the Makefile has no check target");
  const covered = reachable(targets, "check");
  for (const workflow of ["ci.yml", "deploy.yml"]) {
    const invoked = runSteps(read(`.github/workflows/${workflow}`))
      .map((run) => run.match(/^make\s+(\S+)/)?.[1])
      .filter(Boolean);
    assert.ok(invoked.length >= 3, `found only ${invoked.length} make steps in ${workflow}`);
    for (const target of invoked) {
      assert.ok(covered.has(target), `${workflow} runs \`make ${target}\` and \`make check\` does not`);
    }
  }
});

test("make check includes both audits", () => {
  const covered = reachable(makefile(), "check");
  for (const target of ["audit-node", "audit-python", "test-node", "test-python", "lint", "check-generated"]) {
    assert.ok(covered.has(target), `make check skips ${target}`);
  }
});

// ── The Python audit covers every dependency group ──────────────────────────

test("the python audit resolves every optional dependency group", () => {
  const groups = Object.keys(optionalGroups(read("server/pyproject.toml")));
  assert.ok(groups.includes("postgres"), "the postgres group is gone; this test should be re-read");
  const compile = makefile()
    .get("audit-python")
    ?.recipe.find((line) => /\buv pip compile\b/.test(line));
  assert.ok(compile, "audit-python no longer resolves with uv pip compile");
  if (/--all-extras\b/.test(compile)) return;
  for (const group of groups) {
    assert.match(compile, new RegExp(`--extra[ =]${group}\\b`), `the ${group} group is not audited`);
  }
});

test("the group reader sees what a narrowed recipe would miss", () => {
  const groups = optionalGroups(`[project]
name = "x"

[project.optional-dependencies]
dev = ["ruff>=0.8", "httpx2>=2.12"]
postgres = [
  "psycopg[binary]>=3.1",
  "psycopg_pool>=3.2",
]

[tool.ruff]
line-length = 100
`);
  assert.deepEqual(groups, { dev: ["ruff", "httpx2"], postgres: ["psycopg", "psycopg_pool"] });
});

// ── AGENTS.md's copy is the gate, and can be run ────────────────────────────

test("AGENTS.md's check list is ci.yml's, step for step", () => {
  const documented = markedBlock(read("AGENTS.md"), "ci-steps");
  assert.ok(documented, "AGENTS.md has no <!-- gate:ci-steps --> block");
  assert.deepEqual(
    documented,
    runSteps(jobSource(read(".github/workflows/ci.yml"), "gates")),
    "AGENTS.md's check list and ci.yml's run steps differ; update the one that is wrong",
  );
});

test("every tool a Makefile gate calls is installed by AGENTS.md's setup", () => {
  const agents = read("AGENTS.md");
  const commands = [...(markedBlock(agents, "setup") ?? []), ...(markedBlock(agents, "ci-steps") ?? [])];
  const installed = new Set(
    commands
      .filter((command) => /^pip install\b/.test(command))
      .flatMap((command) => command.replace(/^pip install\s+/, "").split(/\s+/))
      .filter((word) => !word.startsWith("-"))
      .map((word) => word.toLowerCase()),
  );
  // An editable install of the server brings its own extras' packages.
  const groups = optionalGroups(read("server/pyproject.toml"));
  for (const word of [...installed]) {
    const extras = word.match(/^server\[([^\]]+)\]$/)?.[1].split(",") ?? [];
    for (const extra of extras) for (const pkg of groups[extra] ?? []) installed.add(pkg);
  }

  // What every checkout already has: node and its tools, the interpreter,
  // coreutils, and modules of the standard library.
  const present = new Set(["node", "npm", "npx", "python3", "rm", "unittest"]);
  const tools = new Set();
  for (const { recipe } of makefile().values()) {
    for (const line of recipe) {
      tools.add(line.split(/\s+/)[0]);
      for (const match of line.matchAll(/\s-m\s+(\S+)/g)) tools.add(match[1]);
    }
  }
  const missing = [...tools].filter((tool) => !present.has(tool) && !installed.has(tool));
  assert.deepEqual(missing, [], `AGENTS.md installs none of: ${missing.join(", ")}`);
});

test("a block-scalar run step is one command", () => {
  const source = `jobs:
  s3:
    steps:
      - run: make audit-node
      - run: |
          aws s3 sync a b
          aws cloudfront create-invalidation
      - run: npm run lint
`;
  assert.deepEqual(runSteps(source), [
    "make audit-node",
    "aws s3 sync a b\naws cloudfront create-invalidation",
    "npm run lint",
  ]);
});

test("the Makefile reader joins continued recipe lines and sees -m modules", () => {
  const targets = makeTargets(`test: a b

a:
\tpython3 -W error \\
\t\t-m coverage run -m unittest discover
\t@rm -f x
`);
  assert.deepEqual(targets.get("test").deps, ["a", "b"]);
  assert.deepEqual(targets.get("a").recipe, [
    "python3 -W error -m coverage run -m unittest discover",
    "rm -f x",
  ]);
});
