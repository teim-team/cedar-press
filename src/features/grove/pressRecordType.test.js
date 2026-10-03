import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { CONTRACTS, universalRows } from "./explore.js";
import { findRecord, neighbours, readRecordParams, recordHref } from "./pressRecord.js";

function componentRows() {
  const declared = Object.entries(CONTRACTS).find(([, contract]) =>
    contract.record_id && contract.record_type);
  assert.ok(declared, "the combined spreadsheet must declare its record id and record type");
  const [key, contract] = declared;
  const types = ["first-component", "second-component", "third-component"];
  const rows = types.map((recordType) => ({
    [contract.record_id]: "SHARED-001",
    [contract.record_type]: recordType,
  }));
  return universalRows(key, rows);
}

function asked(href) {
  return readRecordParams(new URL(href, "https://cedarpress.ai").search);
}

test("three components can share a table and record id without sharing a record address", () => {
  const items = componentRows();
  assert.equal(new Set(items.map((item) => item.key)).size, 1);
  assert.equal(new Set(items.map((item) => item.recordId)).size, 1);
  assert.equal(new Set(items.map((item) => item.id)).size, 3);
  assert.deepEqual(items.map((item) => item.recordType),
    ["first-component", "second-component", "third-component"]);
  const hrefs = items.map((item) => recordHref({ ...item, from: "c=funding&q=shared" }));
  assert.equal(new Set(hrefs).size, 3);
  hrefs.forEach((href, index) => {
    const query = asked(href);
    assert.equal(query.recordType, items[index].recordType);
    assert.equal(query.from, "c=funding&q=shared");
    assert.strictEqual(findRecord(items, query), items[index]);
  });
});

test("an ambiguous legacy id is refused instead of opening the first component", () => {
  const items = componentRows();
  const query = asked(recordHref({ key: items[0].key, recordId: "SHARED-001" }));
  assert.equal(query.recordType, null);
  assert.equal(findRecord(items, query), null);
  assert.equal(findRecord(items, { ...query, index: 2 }), null);
  assert.equal(findRecord([...items].reverse(), query), null);
});

test("a typed lookup refuses an absent or duplicate pair without an index fallback", () => {
  const items = componentRows();
  assert.equal(findRecord(items, {
    recordId: "SHARED-001", recordType: "absent-component", index: 0,
  }), null);
  assert.equal(findRecord(items, {
    recordId: "absent-id", recordType: items[0].recordType, index: 0,
  }), null);
  assert.equal(findRecord([items[0], { ...items[0] }], {
    recordId: items[0].recordId, recordType: items[0].recordType,
  }), null);
});

test("a unique legacy record id still resolves without a type", () => {
  const item = { id: "legacy:U-1", key: "legacy/table", recordId: "U-1", index: 0 };
  assert.strictEqual(findRecord([item], asked(recordHref(item))), item);
  const typed = { ...item, recordType: "one-component" };
  assert.strictEqual(findRecord([typed], { recordId: "U-1" }), typed);
});

test("previous and next retain the selected component and the original cut", () => {
  const items = componentRows();
  const ordered = [items[2], items[0], items[1]];
  const place = neighbours(ordered, items[0].id);
  assert.equal(place.at, 1);
  for (const item of [place.previous, place.next]) {
    const query = asked(recordHref({ ...item, from: "q=SHARED-001&s=date" }));
    assert.equal(query.recordType, item.recordType);
    assert.equal(query.from, "q=SHARED-001&s=date");
    assert.strictEqual(findRecord(items, query), item);
  }
});

test("record types round-trip as exact URL values, including a declared blank", () => {
  for (const recordType of ["permits / amendments & x=1", "annonce é", ""]) {
    const item = { key: "plot/spreadsheet", recordId: "R / 1", recordType, index: 0 };
    const href = recordHref(item);
    assert.ok(new URL(href, "https://cedarpress.ai").searchParams.has("rt"));
    assert.equal(asked(href).recordType, recordType);
    assert.strictEqual(findRecord([item], asked(href)), item);
  }
});

test("positional legacy records remain addressable and an explicit wrong type is refused", () => {
  const items = [
    { id: "legacy#0", recordId: null, index: 0 },
    { id: "legacy#1", recordId: null, recordType: "second", index: 1 },
  ];
  assert.strictEqual(findRecord(items, asked(recordHref({ key: "legacy/table", index: 1 }))), items[1]);
  assert.strictEqual(findRecord(items, { index: 1, recordType: "second" }), items[1]);
  assert.equal(findRecord(items, { index: 1, recordType: "first" }), null);
  assert.equal(findRecord(items, { index: -1 }), null);
});

test("all maintained record-link surfaces forward the row's record type", () => {
  // Unit link/lookup tests alone would miss a caller dropping this identity part.
  for (const path of [
    "../../pages/grove/PressExplore.jsx",
    "../../pages/grove/CedarPressEntity.jsx",
    "../../pages/grove/CedarPressRecord.jsx",
  ]) {
    const source = readFileSync(new URL(path, import.meta.url), "utf8");
    const calls = [...source.matchAll(/recordHref\(\{([^}]+)\}\)/g)];
    assert.ok(calls.length, path);
    for (const call of calls) {
      assert.match(call[1], /\brecordType:\s*item\.recordType\b/, path);
    }
  }
});
