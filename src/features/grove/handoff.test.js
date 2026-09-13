// docs/TERMINAL_HANDOFF.md is the one file the data workspace reads after
// pulling this repository. A handoff that names a file which has moved is
// worse than no handoff: it sends someone looking for instructions that are
// not there, and it looks as authoritative as a correct one.
//
// So every path it names has to exist, and the two claims in it that the code
// can check are checked.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { IDENTIFIERS } from "./pressIdentity.js";

const root = new URL("../../../", import.meta.url);
const read = (rel) => readFileSync(new URL(rel, root), "utf8");
const HANDOFF = "docs/TERMINAL_HANDOFF.md";
const handoff = read(HANDOFF);

test("every repository path the handoff names exists", () => {
  // Backticked paths that look like files in this repo: a slash or a known
  // extension, and not a shell command or a column name.
  const candidates = new Set(
    [...handoff.matchAll(/`([^`\s]+\.(?:md|js|json|jsonl|py|yml|csv))`/g)].map((m) => m[1]),
  );
  assert.ok(candidates.size >= 10, `expected the handoff to name paths, found ${candidates.size}`);
  const missing = [...candidates].filter((rel) => !existsSync(fileURLToPath(new URL(rel, root))));
  assert.deepEqual(missing, [], `the handoff names ${missing.length} path(s) that do not exist`);
});

test("the handoff's other documents exist and point back", () => {
  for (const doc of ["docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md", "docs/CEDAR_PRESS_SITE_2026-09-13.md"]) {
    assert.ok(existsSync(fileURLToPath(new URL(doc, root))), `${doc} is gone`);
  }
  // And the two entry points a terminal actually opens have to route to it,
  // or the handoff is a file nobody is told to read.
  for (const entry of ["README.md", "START_HERE.md"]) {
    assert.match(read(entry), /docs\/TERMINAL_HANDOFF\.md/, `${entry} no longer routes to the handoff`);
  }
});

test("the handoff's liveness claim matches the code", () => {
  // Item 1 says the business register is not minted and tells the reader to
  // flip a flag. If someone flips the flag and leaves the handoff saying to,
  // the next session does the work twice.
  const business = IDENTIFIERS.find((item) => item.id === "business");
  const saysPending = /`live: false` → `true`/.test(handoff);
  assert.equal(
    saysPending,
    business.live === false,
    business.live
      ? "the business register is live; item 1 of the handoff is done and should be removed"
      : "the handoff no longer tells the terminal to flip `live` when CB- is minted",
  );
});

test("the handoff stays a list, not a journal", () => {
  // It is rewritten in place on purpose. The failure mode for every other doc
  // in this repo is that it grows until nobody reads it, and this is the one
  // that has to be read on every pull.
  const lines = handoff.split("\n").length;
  assert.ok(lines < 200, `the handoff is ${lines} lines; it is meant to be a table, not a journal`);
  assert.match(handoff, /Rewritten in place, never\s*\n?appended to/, "the handoff dropped its own rule");
});
