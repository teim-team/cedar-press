// The Gaming consumer job's trust boundary, read from ci.yml rather than
// trusted to a comment.
//
// `gaming-release-consumer` is the one place a pull request of this
// repository reaches into another, private repository (teim-team/Lumecon-data)
// with a credential. What it must never become: a job that installs whatever a
// branch points at today, a job that prints or persists the read token, a job
// that silently passes when the token is missing, or a job that a fork's code
// can run with the secret in scope. Each of those is one plausible edit away,
// so each is pinned here, and each rule is shown catching its own mutation.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (name) =>
  readFileSync(new URL(`../../../.github/workflows/${name}`, import.meta.url), "utf8");
const CI = read("ci.yml");
const JOB = "gaming-release-consumer";

// Small readers of our own rather than imports from the other workflow tests:
// importing a *.test.js file registers (and reruns) every test in it.

/** One job's lines, from its `  <name>:` key to the next job or top-level key. */
function jobSource(source, name) {
  const lines = source.split("\n");
  const start = lines.findIndex((line) => line === `  ${name}:`);
  if (start === -1) return "";
  const body = [lines[start]];
  for (const line of lines.slice(start + 1)) {
    if (/^ {2}[A-Za-z0-9_-]+:\s*$/.test(line) || /^\S/.test(line)) break;
    body.push(line);
  }
  return body.join("\n");
}

/** Every `permissions:` block in a source, as its entries. */
function permissionBlocks(source) {
  const lines = source.split("\n");
  const blocks = [];
  lines.forEach((line, i) => {
    const opener = line.match(/^(\s*)permissions:\s*$/);
    if (!opener) return;
    const entries = [];
    for (const next of lines.slice(i + 1)) {
      const deeper = next.match(/^(\s*)(\S.*)$/);
      if (!deeper || deeper[1].length <= opener[1].length) break;
      entries.push(deeper[2].trim());
    }
    blocks.push(entries);
  });
  return blocks;
}

/** The job's first step: its text up to the next list item at step depth. */
function firstStep(job) {
  const lines = job.split("\n");
  const at = lines.findIndex((line) => /^\s+steps:\s*$/.test(line));
  if (at === -1) return "";
  const step = [];
  for (const line of lines.slice(at + 1)) {
    if (/^ {6}- /.test(line) && step.length) break;
    step.push(line);
  }
  return step.join("\n");
}

/** The source minus comments: prose may name what the YAML must not do. */
const code = (source) =>
  source
    .split("\n")
    .filter((line) => !/^\s*#/.test(line))
    .map((line) => line.replace(/\s+#\s.*$/, ""))
    .join("\n");

/** Action references, `owner/name@ref`, in order. */
const actions = (source) =>
  [...code(source).matchAll(/uses:\s*([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+)@(\S+)/g)].map((m) => ({
    action: m[1],
    ref: m[2],
  }));

/** Each `uses: actions/checkout` step's `with:` block. */
const checkouts = (body) =>
  body
    .split(/\n(?= {6}- )/)
    .filter((step) => /uses: actions\/checkout@/.test(step));

/** Every trust-boundary violation in a workflow's consumer job (empty = holds). */
export function trustBoundaryViolations(workflow, jobName = JOB) {
  const problems = [];
  const job = jobSource(workflow, jobName);
  if (!job) return [`no ${jobName} job`];
  const body = code(job);

  if (/pull_request_target/.test(code(workflow))) problems.push("pull_request_target trigger");

  const perms = permissionBlocks(body);
  if (perms.length !== 1 || perms[0].join("|") !== "contents: read") {
    problems.push("job permissions must be exactly contents: read");
  }

  const pin = body.match(/^\s+LUMECON_DATA_SHA:\s*(\S+)\s*$/m)?.[1];
  if (!pin || !/^[0-9a-f]{40}$/.test(pin)) problems.push("LUMECON_DATA_SHA is not a full commit SHA");

  // The Lumecon checkout: actions/checkout, the exact pin, the scoped secret,
  // no persisted credentials.
  const lumecon = checkouts(body).filter((step) =>
    /repository:\s*teim-team\/Lumecon-data\s*$/m.test(step),
  );
  if (lumecon.length !== 1) {
    problems.push("Lumecon-data is not checked out exactly once with actions/checkout");
  } else {
    const [step] = lumecon;
    if (!/^\s+ref:\s*\$\{\{\s*env\.LUMECON_DATA_SHA\s*\}\}\s*$/m.test(step)) {
      problems.push("Lumecon checkout ref is not the pinned SHA");
    }
    if (!/^\s+token:\s*\$\{\{\s*secrets\.LUMECON_DATA_READ_TOKEN\s*\}\}\s*$/m.test(step)) {
      problems.push("Lumecon checkout does not use LUMECON_DATA_READ_TOKEN");
    }
    if (!/^\s+persist-credentials:\s*false\s*$/m.test(step)) {
      problems.push("Lumecon checkout persists credentials");
    }
  }
  for (const step of checkouts(body)) {
    if (!/^\s+persist-credentials:\s*false\s*$/m.test(step)) {
      problems.push("a checkout in this job persists credentials");
    }
  }

  // After checkout: HEAD must equal the pin, or the job fails.
  if (!/git -C \S+ rev-parse HEAD/.test(body) || !/!= "\$LUMECON_DATA_SHA"/.test(body)) {
    problems.push("no post-checkout rev-parse HEAD check against the pin");
  }

  // Installed from the verified local checkout; never a URL, branch or `current`.
  if (!/pip install\s+'\.\/\.lumecon-data\[api\]'/.test(body)) {
    problems.push("Lumecon is not installed from the verified local checkout");
  }
  if (/git\+https?:|x-access-token|@github\.com/.test(body)) {
    problems.push("Lumecon is fetched by URL, or a credential appears in a URL");
  }
  const refs = body.split("\n").filter((line) => /^\s+ref:/.test(line));
  if (refs.some((line) => !/^\s+ref:\s*\$\{\{\s*env\.LUMECON_DATA_SHA\s*\}\}\s*$/.test(line))) {
    problems.push("a ref other than the pinned SHA");
  }

  // The token: only a checkout `token:` input or a presence test, never a run
  // step's environment value, a URL or an echo.
  for (const line of body.split("\n").filter((l) => l.includes("secrets.LUMECON_DATA_READ_TOKEN"))) {
    const checkoutInput = /^\s+token:\s*\$\{\{\s*secrets\.LUMECON_DATA_READ_TOKEN\s*\}\}\s*$/.test(line);
    const presence = /\$\{\{\s*secrets\.LUMECON_DATA_READ_TOKEN\s*!=\s*''\s*\}\}\s*$/.test(line);
    if (!checkoutInput && !presence) problems.push(`the token is used beyond checkout: ${line.trim()}`);
  }
  // Its raw value never reaches a shell: no $LUMECON_DATA_READ_TOKEN anywhere.
  if (/\$\{?LUMECON_DATA_READ_TOKEN\b/.test(body)) problems.push("the token value reaches a shell");

  // Fail closed on a missing secret: the FIRST step names it and exits
  // non-zero, and nothing can skip the job, a step, or swallow a failure.
  const first = firstStep(body);
  if (!/secrets\.LUMECON_DATA_READ_TOKEN\s*!=\s*''/.test(first) || !/^\s+exit 1\s*$/m.test(first)) {
    problems.push("the first step does not fail when the secret is absent");
  }
  if (!/::error[^\n]*LUMECON_DATA_READ_TOKEN/.test(first)) {
    problems.push("the missing-secret failure does not name LUMECON_DATA_READ_TOKEN");
  }
  if (/^\s+(- )?if:/m.test(body)) problems.push("an if: condition could skip the job or a step");
  if (/continue-on-error:\s*true/.test(body)) problems.push("continue-on-error lets a failure pass");
  if (!/CEDAR_REQUIRE_LUMECON_GAMING:\s*"1"/.test(body)) {
    problems.push("consumer tests may skip without Lumecon");
  }
  return problems;
}

test("the Gaming consumer job holds the Lumecon trust boundary", () => {
  assert.deepEqual(trustBoundaryViolations(CI), []);
});

test("every action in the job is pinned to the SHA the other workflows use", () => {
  const job = jobSource(CI, JOB);
  const elsewhere = new Map();
  for (const source of [CI.replace(job, ""), read("deploy.yml")]) {
    for (const { action, ref } of actions(source)) {
      elsewhere.set(action, [...(elsewhere.get(action) ?? []), ref]);
    }
  }
  const used = actions(job);
  assert.ok(used.length >= 3, "expected two checkouts and setup-python");
  for (const { action, ref } of used) {
    assert.match(ref, /^[0-9a-f]{40}$/, `${action} is not pinned to a commit SHA`);
    assert.ok(
      (elsewhere.get(action) ?? []).includes(ref),
      `${action}@${ref} differs from the pin the other workflows use`,
    );
  }
});

// ── Each rule catches the edit it exists to stop ────────────────────────────

const mutations = {
  "a branch ref": (s) =>
    s.replace("ref: ${{ env.LUMECON_DATA_SHA }}", "ref: claude/gaming-grove-release"),
  "a short SHA": (s) =>
    s.replace(/(LUMECON_DATA_SHA: )([0-9a-f]{40})/, (_, key, sha) => key + sha.slice(0, 7)),
  "a persisted credential": (s) =>
    s.replace("persist-credentials: false\n          path: .lumecon-data", "path: .lumecon-data"),
  "a token in an install URL": (s) =>
    s.replace(
      "pip install './.lumecon-data[api]'",
      'pip install "lumecon-data @ git+https://x-access-token:${LUMECON_DATA_READ_TOKEN}@github.com/teim-team/Lumecon-data@main"',
    ),
  "the token in a run step's env": (s) =>
    s.replace(
      "      - name: Install Lumecon-data from the verified checkout\n",
      "      - name: Install Lumecon-data from the verified checkout\n        env:\n          T: ${{ secrets.LUMECON_DATA_READ_TOKEN }}\n",
    ),
  "no HEAD check": (s) => s.replace("git -C .lumecon-data rev-parse HEAD", "echo skipped"),
  "a silent pass on a missing secret": (s) =>
    s.replace(
      "            exit 1\n          fi\n      - uses: actions/checkout",
      "            exit 0\n          fi\n      - uses: actions/checkout",
    ),
  "an if: guard on the job": (s) =>
    s.replace(
      "  gaming-release-consumer:\n",
      "  gaming-release-consumer:\n    if: github.event.pull_request.head.repo.fork == false\n",
    ),
  "a write permission": (s) =>
    s.replace(
      "    permissions:\n      contents: read\n    env:\n      LUMECON_DATA_SHA",
      "    permissions:\n      contents: read\n      pull-requests: write\n    env:\n      LUMECON_DATA_SHA",
    ),
  "pull_request_target": (s) => s.replace("  pull_request:\n", "  pull_request_target:\n"),
};

for (const [label, mutate] of Object.entries(mutations)) {
  test(`the lint rejects ${label}`, () => {
    const mutated = mutate(CI);
    assert.notEqual(mutated, CI, `the ${label} mutation no longer applies to ci.yml`);
    assert.notDeepEqual(trustBoundaryViolations(mutated), [], `${label} passed the lint`);
  });
}
