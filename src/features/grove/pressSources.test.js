// The door names ~forty source systems. Every one of them has to be a system
// a collection descriptor actually names, and no descriptor may quietly drop
// one the door still advertises. These two assertions are the whole contract.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { LAUNCH_COLLECTION } from "./collection.js";
import {
  PRESS_SOURCES,
  SOURCE_COUNT,
  SOURCE_GROUPS,
  SOURCE_PROSE,
  evidenceFor,
  isEvidenced,
} from "./pressSources.js";

test("every descriptor-evidenced source is named by a collection descriptor", () => {
  for (const source of PRESS_SOURCES.filter((s) => !s.registry)) {
    assert.ok(
      isEvidenced(source),
      `"${source.name}" claims ${source.collections.join(", ")}, but no descriptor's sources ` +
        `prose contains "${evidenceFor(source)}". Either the workspace renamed it, or the door ` +
        `is advertising a system Cedar does not read.`,
    );
  }
});

test("every registry-evidenced source is a kind the registry actually holds", () => {
  // The registry is repository data, not bundled: the test reads it, the
  // door ships only the counted summary.
  const path = new URL("../../../cedar_source_registry/sources.jsonl", import.meta.url);
  const rows = readFileSync(path, "utf8").trim().split("\n").map((line) => JSON.parse(line));
  const kinds = rows.map((row) => String(row.source_type ?? "").toLowerCase());
  for (const source of PRESS_SOURCES.filter((s) => s.registry)) {
    const needle = evidenceFor(source);
    const hits = kinds.filter((kind) => kind === needle).length;
    assert.ok(hits > 0, `"${source.name}" claims registry source_type "${needle}", which the registry does not hold`);
    assert.equal(
      hits,
      source.programs,
      `"${source.name}" declares ${source.programs} programs; the registry holds ${hits}`,
    );
  }
});

test("the registry entries do not restate a descriptor entry", () => {
  // The TERO registries are already named by the Owned descriptor, so the
  // registry group must not name them again. Near-duplicates were the
  // reason this file was rewritten.
  const registryNames = PRESS_SOURCES.filter((s) => s.registry).map((s) => s.name.toLowerCase());
  for (const name of registryNames) {
    assert.ok(!name.includes("tero"), `the registry group restates the TERO offices the Owned descriptor names ("${name}")`);
  }
});

test("every collection a source claims is a real storefront collection", () => {
  const known = new Set(LAUNCH_COLLECTION.map((entry) => entry.id));
  for (const source of PRESS_SOURCES.filter((s) => !s.registry)) {
    assert.ok(source.collections.length > 0, `${source.name} names no collection`);
    for (const id of source.collections) {
      assert.ok(known.has(id), `${source.name} claims unknown collection "${id}"`);
    }
  }
});

test("every collection with sources prose contributes at least one named system", () => {
  // The other direction: a collection whose prose names systems but which no
  // entry here claims is a collection the door silently under-credits.
  const claimed = new Set(PRESS_SOURCES.flatMap((source) => source.collections ?? []));
  for (const [id, prose] of Object.entries(SOURCE_PROSE)) {
    if (!prose) continue;
    assert.ok(claimed.has(id), `${id} declares sources and no entry in pressSources.js reads them`);
  }
});

test("the count is derived, and the groups are non-empty", () => {
  assert.equal(SOURCE_COUNT, PRESS_SOURCES.length);
  assert.ok(SOURCE_COUNT > 30, `expected the door to name more than thirty systems, got ${SOURCE_COUNT}`);
  for (const group of SOURCE_GROUPS) {
    assert.ok(group.sources.length > 0, `${group.id} is an empty group`);
    assert.ok(group.label, `${group.id} has no label`);
  }
});

test("no source is listed twice under the same name", () => {
  const seen = new Map();
  for (const source of PRESS_SOURCES) {
    assert.ok(!seen.has(source.name), `"${source.name}" is listed twice`);
    seen.set(source.name, true);
  }
});
