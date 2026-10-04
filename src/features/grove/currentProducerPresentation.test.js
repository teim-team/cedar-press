import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import manifest from "../../../data/cedar/collections.manifest.json" with { type: "json" };
import { parseCsv, codebookFor, contractFor, exploreTables, SOURCE_LINK_COLUMN } from "./explore.js";
import { columnPlan } from "./recordColumns.js";
import { codebookTables, loadCodebook } from "./codebook.js";
// The codebook loads on demand in the browser (codebook.js); the readers
// under test read it synchronously once it has.
await loadCodebook();

// Two layers since 2026-10-04. The producer preview (data/cedar/samples/,
// not served) is the INPUT, and its dictionary is data/cedar/codebook.json,
// exactly. The customer table rendered from it (public/data/cedar/downloads/)
// is what every reader sees, and its dictionary is `codebookFor`.
const raw = (path) => parseCsv(readFileSync(new URL("../../.." + path, import.meta.url), "utf8"));
const served = (path) => parseCsv(readFileSync(new URL("../../../public" + path, import.meta.url), "utf8"));

test("all fourteen producer previews have an exact raw codebook, and each customer table a valid opening view", () => {
  assert.equal(manifest.collections.length, 14);
  for (const collection of manifest.collections) {
    for (const table of collection.tables.filter(value => value.sample_path)) {
      const key = collection.id + "/" + table.table.replace(/\.csv$/, "");
      // The input: the producer's own dictionary, column for column.
      const { columns: rawColumns } = raw(table.sample_path);
      assert.deepEqual(codebookTables()[key]?.fields.map(field => field.column), rawColumns, key);
      for (const field of codebookTables()[key].fields) {
        assert.ok(field.label?.trim() && field.meaning?.trim(), key + ":" + field.column);
      }
      // What a reader opens: the customer table, through its own contract.
      const [opened] = exploreTables(collection.id);
      assert.equal(opened?.key, key, key);
      const { columns } = served(opened.path);
      const contract = contractFor(key);
      assert.equal(contract?.mapping_kind, "customer_table", key);
      for (const packaging of ["record_type", "record_key", "record_grain"]) {
        assert.ok(!columns.includes(packaging), `${key} still carries ${packaging}`);
      }
      assert.deepEqual(codebookFor(key).fields.map(field => field.column), columns, key);
      for (const field of codebookFor(key).fields) {
        assert.ok(field.label?.trim() && field.meaning?.trim(), key + ": customer column " + field.column);
      }
      const plan = columnPlan(key, contract, columns);
      assert.ok(plan.defaults.length > 0, key + " must have an opening view");
      assert.ok(plan.defaults.some(column => column !== SOURCE_LINK_COLUMN), key + " must show a meaningful record value");
      for (const column of plan.defaults) {
        assert.ok(columns.includes(column) || column === SOURCE_LINK_COLUMN, key + ":" + column);
      }
    }
  }
});

test("Giving and PLOT keep their verified per-type field maps as inputs, and open as one flat table", () => {
  for (const id of ["foundation-corporate-giving", "plot"]) {
    const collection = manifest.collections.find(value => value.id === id);
    assert.ok(collection, id);
    for (const table of collection.tables.filter(value => value.sample_path)) {
      const key = id + "/" + table.table.replace(/\.csv$/, "");
      // The producer's per-type maps still describe the preview the customer
      // table is rendered from.
      assert.deepEqual(Object.keys(table.record_type_fields).sort(), Object.keys(table.record_types).sort(), key);
      const { columns } = served(exploreTables(id)[0].path);
      const contract = contractFor(key);
      // One table, one grain: nothing to dispatch by record type.
      assert.equal(contract.row_type_contracts ?? null, null, key);
      assert.equal(contract.record_type, null, key);
      for (const column of [contract.source, contract.source_fallback, contract.date, contract.year,
        contract.amount, contract.amount_basis, contract.record_id, ...(contract.subject_candidates ?? []),
        ...(contract.observation ?? [])].filter(Boolean)) {
        assert.ok(columns.includes(column), key + ": customer field " + column);
      }
      const plan = columnPlan(key, contract, columns);
      // One source, the table's own: no dispatched link column is needed.
      assert.ok(contract.source, key);
      assert.deepEqual(plan.defaults.filter(column => column === SOURCE_LINK_COLUMN || column === contract.source), [contract.source], key);
      for (const column of columns) assert.ok(plan.all.includes(column), key + ": customer field retained " + column);
    }
  }
});
