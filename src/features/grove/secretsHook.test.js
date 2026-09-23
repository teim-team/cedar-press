// The credential hook has to fire, and has to let the template through.
//
// `no-secrets-committed` in .pre-commit-config.yaml is a custom gate, and a
// custom gate proves nothing until a fixture shows it firing: a quoting slip
// or a changed `case` pattern turns it into a hook that passes everything,
// and a hook that passes everything looks exactly like one that works.
// Codex, on PR #105. So each forbidden shape is fed to the script and must
// exit 1 naming the file; the template and ordinary files must exit 0.
//
// The script is run directly because it is what the hook runs: the first
// test pins that, so a config that stops calling it fails here rather than
// leaving these fixtures testing a file nothing executes.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const SCRIPT = "scripts/no-secrets-staged.sh";

const hook = (...names) => {
  const result = spawnSync("bash", [join(ROOT, SCRIPT), ...names], { encoding: "utf8" });
  return { status: result.status, out: result.stdout + result.stderr };
};

/** The `no-secrets-committed` hook's lines, out of the pre-commit config. */
function hookBlock(config) {
  const lines = config.split("\n");
  const start = lines.findIndex((line) => /-\s+id:\s+no-secrets-committed\s*$/.test(line));
  if (start === -1) return null;
  const block = [lines[start]];
  for (const line of lines.slice(start + 1)) {
    if (/^\s*-\s+id:/.test(line)) break;
    block.push(line);
  }
  return block.join("\n");
}

test("the hook runs this script, so these fixtures test what executes", () => {
  const block = hookBlock(readFileSync(join(ROOT, ".pre-commit-config.yaml"), "utf8"));
  assert.ok(block, "the no-secrets-committed hook is gone from .pre-commit-config.yaml");
  assert.match(block, new RegExp(`^\\s+entry:\\s+${SCRIPT.replace(/[.]/g, "\\.")}\\s*$`, "m"));
});

const SECRETS = [".env", ".env.local", ".env.production", "server/.env", "server/.env.local"];
const CREDENTIALS = ["private.key", "certs/site.pem", "gcp-credentials.json", "config/aws-credentials.json"];

for (const name of SECRETS) {
  test(`a staged ${name} is refused, by name`, () => {
    const { status, out } = hook(name);
    assert.equal(status, 1, `${name} passed the hook`);
    assert.equal(out.trim(), `${name} holds secrets; it belongs outside Git`);
  });
}

for (const name of CREDENTIALS) {
  test(`a staged ${name} is refused, by name`, () => {
    const { status, out } = hook(name);
    assert.equal(status, 1, `${name} passed the hook`);
    assert.equal(out.trim(), `${name} looks like a credential; it belongs outside Git`);
  });
}

for (const name of [".env.example", "server/.env.example", "src/app.js", "docs/credentials.md", ".envrc"]) {
  test(`${name} is allowed through`, () => {
    assert.deepEqual(hook(name), { status: 0, out: "" });
  });
}

test("one secret among ordinary files fails the batch and names only the secret", () => {
  const { status, out } = hook("src/app.js", ".env.example", "server/.env", "README.md");
  assert.equal(status, 1);
  assert.equal(out.trim(), "server/.env holds secrets; it belongs outside Git");
});

test("a name with a space is one file, not two", () => {
  const { status, out } = hook("my keys/private.key");
  assert.equal(status, 1);
  assert.equal(out.trim(), "my keys/private.key looks like a credential; it belongs outside Git");
});

// ── Through pre-commit itself, where it is installed ────────────────────────
// CI does not install pre-commit (it runs the gates, not the hooks), so this
// one skips there; the fixtures above are what CI holds the script to.

const havePreCommit = spawnSync("pre-commit", ["--version"]).status === 0;

test("pre-commit refuses a staged .env and passes the staged template", { skip: !havePreCommit }, () => {
  const dir = mkdtempSync(join(tmpdir(), "cedar-secrets-hook-"));
  try {
    const git = (...args) => {
      const result = spawnSync("git", args, { cwd: dir, encoding: "utf8" });
      assert.equal(result.status, 0, `git ${args.join(" ")}: ${result.stderr}`);
    };
    git("init", "--quiet");
    mkdirSync(join(dir, "scripts"));
    copyFileSync(join(ROOT, ".pre-commit-config.yaml"), join(dir, ".pre-commit-config.yaml"));
    copyFileSync(join(ROOT, SCRIPT), join(dir, SCRIPT));
    writeFileSync(join(dir, ".env"), "DATABASE_URL=postgresql://example\n");
    writeFileSync(join(dir, ".env.example"), "DATABASE_URL=\n");
    git("add", ".pre-commit-config.yaml", SCRIPT);
    const preCommit = () =>
      spawnSync("pre-commit", ["run", "no-secrets-committed"], { cwd: dir, encoding: "utf8" });

    git("add", ".env");
    const refused = preCommit();
    assert.equal(refused.status, 1, refused.stdout);
    assert.match(refused.stdout, /\.env holds secrets; it belongs outside Git/);

    git("rm", "--cached", "--quiet", ".env");
    git("add", ".env.example");
    const allowed = preCommit();
    assert.equal(allowed.status, 0, allowed.stdout);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
