import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { parseCsv, universalRows } from "./explore.js";
import { LANDING_EXAMPLES, landingSample } from "./landingExamples.js";
import { EXCLUDED_EXAMPLES } from "./showcase.js";

const download = (id) => parseCsv(readFileSync(new URL(`../../../public/data/cedar/downloads/${id}.csv`, import.meta.url), "utf8"));
const GARBLED = /Ã|Â|â€|&NBSP;|&nbsp;/;

test("every collection has curated landing examples, each copied from a recorded origin onto the download's own columns", () => {
  assert.equal(Object.keys(LANDING_EXAMPLES).length, 14);
  for (const [id, set] of Object.entries(LANDING_EXAMPLES)) {
    const { columns } = download(id);
    assert.ok(set.rows.length >= 3, id);
    for (const row of set.rows) {
      assert.match(row._origin ?? "", /\S+:\S+/, `${id}: a row with no origin`);
      for (const key of Object.keys(row)) assert.ok(key === "_origin" || columns.includes(key), `${id}: ${key} is not a column of the download`);
      for (const [key, value] of Object.entries(row)) assert.ok(!GARBLED.test(String(value)), `${id}.${key}: garbled text`);
    }
    for (const column of set.columns ?? []) assert.ok(columns.includes(column), `${id}: shown column ${column}`);
  }
});

test("the landing examples name a Native entity, carry no $0 or negative amount and leave out the known wrong records", () => {
  for (const [id, set] of Object.entries(LANDING_EXAMPLES)) {
    const parsed = landingSample(id, download(id));
    const key = `${id}/${id}`;
    const items = universalRows(key, parsed.rows);
    for (const item of items) {
      if (item.amount != null) assert.ok(item.amount > 0, `${id}: ${item.recordId} amount ${item.amount}`);
      assert.ok(!Object.hasOwn(EXCLUDED_EXAMPLES[id] ?? {}, item.recordId), `${id}: ${item.recordId} is a known wrong record`);
    }
    if (!["federal-register", "plot", "nonprofits", "owned", "foundation-corporate-giving"].includes(id)) {
      assert.ok(items.every((item) => item.entity.uid || item.entity.name), `${id}: a record names no Native entity`);
    }
    assert.ok(set.rows.length >= 3, id);
  }
});

test("NEED's landing examples span tribes and Alaska Native corporations, each with its ultimate parent and federal identifiers", () => {
  const rows = LANDING_EXAMPLES.need.rows;
  const owners = new Set(rows.map((row) => row.native_owner));
  for (const owner of ["The Chickasaw Nation", "The Choctaw Nation of Oklahoma", "Arctic Slope Regional Corporation", "NANA Regional Corporation, Inc.", "Koniag, Incorporated"]) {
    assert.ok(owners.has(owner), owner);
  }
  for (const row of rows) {
    assert.match(row.native_owner_cedar_uid, /^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$/, row.enterprise_name);
    assert.match(row.uei, /^[0-9A-Z]{12}$/, row.enterprise_name);
    assert.match(row.cage_code, /^[0-9A-Z]{5}$/, row.enterprise_name);
  }
  // A tribe-owned enterprise leads.
  assert.equal(rows[0].native_owner, "The Chickasaw Nation");
});

test("the landing sample keeps the download's columns and leaves a collection with no curated set unchanged", () => {
  const parsed = download("funding");
  const shown = landingSample("funding", parsed);
  assert.deepEqual(shown.columns, parsed.columns);
  assert.equal(shown.rows.length, LANDING_EXAMPLES.funding.rows.length);
  assert.equal(landingSample("gaming", parsed), parsed);
});
