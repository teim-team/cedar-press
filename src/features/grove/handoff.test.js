// The active handoff is short, links to the preserved historical checkpoint,
// and states the current consumer status. Every local reference must resolve.
import assert from "node:assert/strict";
import { existsSync, readFileSync, statSync } from "node:fs";
import { isAbsolute, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { IDENTIFIERS } from "./pressIdentity.js";

const root = new URL("../../../", import.meta.url);
const read = (rel) => readFileSync(new URL(rel, root), "utf8");
const HANDOFF = "docs/TERMINAL_HANDOFF.md";
const handoff = read(HANDOFF);

function repositoryReferences(text) {
  const references = new Set();
  const add = (target, base) => {
    if (!target || target.startsWith("#") || /^(?:https?:|mailto:)/i.test(target)) return;
    assert.ok(!/^[a-z][a-z0-9+.-]*:/i.test(target),
      "the handoff must use repository-relative local references");
    const url = new URL(target, base);
    const local = fileURLToPath(url);
    const path = relative(fileURLToPath(root), local);
    assert.ok(!isAbsolute(path) && path !== ".." && !path.startsWith(".." + sep),
      "the handoff references a file outside the repository: " + target);
    references.add(path.split(sep).join("/"));
  };
  // Inline code paths are repository-relative; normal Markdown links are
  // relative to the handoff document, as they are on GitHub.
  for (const match of text.matchAll(/`([^`\s]+)`/g)) {
    if (/^(?:Makefile|[A-Za-z0-9_./-]+\.(?:md|mjs|cjs|jsx|js|json|jsonl|py|yml|yaml|csv|toml))$/.test(match[1])) {
      add(match[1], root);
    }
  }
  for (const match of text.matchAll(/\[[^\]\n]+\]\((?:<([^>\n]+)>|([^\s)]+))(?:\s+"[^"]*")?\)/g)) {
    add(match[1] ?? match[2], new URL(HANDOFF, root));
  }
  return references;
}

test("every repository path the handoff names exists", () => {
  const candidates = repositoryReferences(handoff);
  // These are the active workflow and archived evidence destinations, not an
  // arbitrary minimum number of backticks in an intentionally concise page.
  for (const path of [
    "README.md",
    "docs/PRESENTATION_DATA_FLOW.md",
    "AGENTS.md",
    "server/README.md",
    "docs/handoffs/2026-10-01-terminal-history.md",
    "START_HERE.md",
    "Makefile",
  ]) {
    assert.ok(candidates.has(path), "the handoff dropped its reference to " + path);
  }
  const missing = [...candidates].filter((path) => {
    const local = fileURLToPath(new URL(path, root));
    return !existsSync(local) || !statSync(local).isFile();
  });
  assert.deepEqual(missing, [], "the handoff names missing or non-file repository paths");
});

test("the handoff's other documents exist and point back", () => {
  for (const doc of ["docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md", "docs/CEDAR_PRESS_SITE_2026-09-13.md"]) {
    assert.ok(existsSync(fileURLToPath(new URL(doc, root))), doc + " is gone");
  }
  for (const entry of ["README.md", "START_HERE.md"]) {
    assert.match(read(entry), /docs\/TERMINAL_HANDOFF\.md/, entry + " no longer routes to the handoff");
  }
});

test("the handoff's liveness claim matches the code", () => {
  const business = IDENTIFIERS.find((item) => item.id === "business");
  assert.ok(business, "the consumer has no business identifier descriptor");
  const declaration = handoff.match(/Business register state:\s*`live: (true|false)`/);
  assert.ok(declaration, "the active handoff must state the consumer's business-register liveness");
  assert.equal(declaration[1] === "true", business.live,
    "the handoff's business-register liveness disagrees with the consumer");
  if (!business.live) {
    assert.match(handoff, /`live: false` → `true`/);
    assert.match(handoff, /approved register is imported and its product integration is verified/);
  }
});

test("the handoff stays a list, not a journal", () => {
  const lines = handoff.split("\n").length;
  assert.ok(lines < 200, "the handoff is " + lines + " lines; historical checkpoints belong in the archive");
  assert.match(handoff, /Rewritten in place, never\s*\n?appended to/,
    "the handoff dropped its own maintenance rule");
});
