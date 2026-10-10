import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { contractFor, parseCsv, universalRows } from "./explore.js";
import { LANDING_EXAMPLES, landingSample } from "./landingExamples.js";
import { EXCLUDED_EXAMPLES, showcaseItems } from "./showcase.js";

const download = (id) => parseCsv(readFileSync(new URL(`../../../public/data/cedar/downloads/${id}.csv`, import.meta.url), "utf8"));
const GARBLED = /Ã|Â|â€|&NBSP;|&nbsp;/;

test("every landing example is a served download record, shown exactly as served", () => {
  assert.equal(Object.keys(LANDING_EXAMPLES).length, 14);
  for (const [id, set] of Object.entries(LANDING_EXAMPLES)) {
    const parsed = download(id);
    const idColumn = contractFor(`${id}/${id}`)?.record_id;
    const extra = set.extra_columns ?? [];
    assert.ok(set.rows.length === 0 || set.rows.length >= 2, `${id}: a set chooses none or at least two records`);
    for (const ref of set.rows) {
      for (const key of Object.keys(ref)) assert.ok(key === "id" || extra.includes(key), `${id}: ${key} is neither the record ID nor a declared extra column`);
      assert.equal(parsed.rows.filter((row) => row[idColumn] === ref.id).length, 1, `${id}: ${ref.id} is not exactly one record of the download`);
    }
    for (const column of extra) assert.ok(!parsed.columns.includes(column), `${id}: extra column ${column} would overwrite a download column`);
    for (const column of set.columns ?? []) assert.ok(parsed.columns.includes(column) || extra.includes(column), `${id}: shown column ${column}`);
    const shown = landingSample(id, parsed);
    assert.equal(shown.rows.length, set.rows.length || parsed.rows.length, id);
    for (const [index, row] of shown.rows.entries()) {
      const served = set.rows.length ? parsed.rows.find((candidate) => candidate[idColumn] === row[idColumn]) : parsed.rows[index];
      for (const column of parsed.columns) assert.equal(row[column], served[column], `${id}.${column}: not as served`);
      for (const value of Object.values(row)) assert.ok(!GARBLED.test(String(value)), `${id}: garbled text`);
    }
  }
});

test("the landing examples name a Native entity, carry no $0 or negative amount and leave out the known wrong records", () => {
  for (const id of Object.keys(LANDING_EXAMPLES)) {
    const parsed = landingSample(id, download(id));
    const key = `${id}/${id}`;
    const items = showcaseItems(id, universalRows(key, parsed.rows));
    for (const item of items) {
      if (item.amount != null) assert.ok(item.amount > 0, `${id}: ${item.recordId} amount ${item.amount}`);
      assert.ok(!Object.hasOwn(EXCLUDED_EXAMPLES[id] ?? {}, item.recordId), `${id}: ${item.recordId} is a known wrong record`);
    }
    // Federal Register documents and the Natural Resources sample name no Native entity as served.
    if (!["federal-register", "natural-resources", "nonprofits", "owned", "foundation-corporate-giving"].includes(id)) {
      assert.ok(items.every((item) => item.entity.uid || item.entity.name), `${id}: a record names no Native entity`);
    }
    assert.ok(items.length >= 2, id);
  }
});

test("the landing sample keeps the download's columns and leaves a collection that chooses no records unchanged", () => {
  const parsed = download("funding");
  const shown = landingSample("funding", parsed);
  assert.deepEqual(shown.columns, parsed.columns);
  assert.equal(shown.rows.length, LANDING_EXAMPLES.funding.rows.length);
  assert.equal(landingSample("gaming", parsed), parsed);
  assert.equal(LANDING_EXAMPLES.need.rows.length, 0);
  const need = download("need");
  assert.equal(landingSample("need", need), need);
});

test("every PLOT landing parcel is tied to the tribe its recorded owner names", () => {
  const items = universalRows("plot/plot", landingSample("plot", download("plot")).rows);
  assert.ok(items.length >= 2);
  for (const item of items) {
    assert.match(item.entity.uid ?? "", /^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$/);
    const tribeWord = item.entity.name.split(/[ ,]/).find((word) => word.length > 4).toUpperCase();
    assert.ok(item.row.owner_name_raw.toUpperCase().includes(tribeWord), `${item.row.owner_name_raw} vs ${item.entity.name}`);
  }
});
