import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import manifest from "../../../data/cedar/collections.manifest.json" with { type: "json" };
import { parseCsv, codebookFor, contractFor, SOURCE_LINK_COLUMN } from "./explore.js";
import { columnPlan } from "./recordColumns.js";
import { PRESENTATION_COLUMNS } from "./mixedSpreadsheet.js";
import { loadCodebook } from "./codebook.js";
// The codebook loads on demand in the browser (codebook.js); the readers
// under test read it synchronously once it has.
await loadCodebook();

test("all fourteen current producer spreadsheets have an exact raw codebook and a valid opening view", () => {
  assert.equal(manifest.collections.length, 14);
  for (const collection of manifest.collections) {
    for (const table of collection.tables.filter(value => value.sample_path)) {
      const key = collection.id + "/" + table.table.replace(/\.csv$/, "");
      const text = readFileSync(new URL("../../../public" + table.sample_path, import.meta.url), "utf8");
      const { columns } = parseCsv(text);
      const contract = contractFor(key);
      assert.equal(contract?.mapping_kind, "producer_spreadsheet", key);
      assert.deepEqual(codebookFor(key)?.fields.map(field => field.column), columns, key);
      for (const field of codebookFor(key).fields) {
        assert.ok(field.label?.trim() && field.meaning?.trim(), key + ":" + field.column);
      }
      const plan = columnPlan(key, contract, columns);
      assert.ok(plan.defaults.length > 0, key + " must have an opening view");
      assert.ok(plan.defaults.some(column => column !== SOURCE_LINK_COLUMN && column !== "record_type"),
        key + " must show a meaningful record value");
      for (const column of plan.defaults) {
        assert.ok(columns.includes(column) || column === SOURCE_LINK_COLUMN ||
          Object.hasOwn(PRESENTATION_COLUMNS, column), key + ":" + column);
      }
    }
  }
});

test("Giving and PLOT retain their verified per-type field maps and one dispatched source", () => {
  for (const id of ["foundation-corporate-giving", "plot"]) {
    const collection = manifest.collections.find(value => value.id === id);
    assert.ok(collection, id);
    for (const table of collection.tables.filter(value => value.sample_path)) {
      const key = id + "/" + table.table.replace(/\.csv$/, "");
      const { columns } = parseCsv(readFileSync(
        new URL("../../../public" + table.sample_path, import.meta.url), "utf8"));
      const contract = contractFor(key);
      assert.deepEqual(Object.keys(table.record_type_fields).sort(), Object.keys(table.record_types).sort(), key);
      assert.deepEqual(Object.keys(contract.row_type_contracts).sort(), Object.keys(table.record_types).sort(), key);
      for (const child of Object.values(contract.row_type_contracts)) {
        for (const column of [child.source, child.source_fallback, child.date, child.year,
          child.amount, child.amount_basis, ...(child.subject_candidates ?? []),
          ...(child.observation ?? [])].filter(Boolean)) {
          assert.ok(columns.includes(column), key + ": raw component field " + column);
        }
        for (const column of Object.values(child.source_fields ?? {})) {
          assert.ok(columns.includes(column), key + ": raw source mapping " + column);
        }
      }
      const plan = columnPlan(key, contract, columns);
      assert.equal(plan.defaults.filter(column => column === SOURCE_LINK_COLUMN).length, 1, key);
      for (const column of columns) assert.ok(plan.all.includes(column), key + ": raw field retained " + column);
    }
  }
});
