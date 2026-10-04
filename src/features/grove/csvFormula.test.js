// Every CSV the client writes neutralizes a cell a spreadsheet would run.
//
// The cases are the server's (`server/tests/fixtures/csv_formula_cases.json`)
// so the browser and the API enforce one rule rather than two that drift.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { collectionCsv, LAUNCH_COLLECTION, hasSample, samplePath } from "./collection.js";
import { csvCell, parseCsv, spreadsheetSafe } from "./csv.js";
import { csvFor } from "./pressDownload.js";
import { loadCodebook } from "./codebook.js";
// The codebook loads on demand in the browser (codebook.js); the readers
// under test read it synchronously once it has.
await loadCodebook();

const { cases: CASES } = JSON.parse(
  readFileSync(new URL("../../../server/tests/fixtures/csv_formula_cases.json", import.meta.url), "utf8"),
);
const expected = ({ value, neutralized }) => (neutralized ? `'${value}` : value);

test("the shared rule", () => {
  for (const item of CASES) assert.equal(spreadsheetSafe(item.value), expected(item), JSON.stringify(item.value));
});

test("csvCell applies it and still round-trips through a CSV reader", () => {
  for (const item of CASES) {
    const { rows } = parseCsv(`h,x\n${csvCell(item.value)},y\n`);
    assert.equal(rows[0]?.h ?? "", expected(item), JSON.stringify(item.value));
  }
});

test("the collection description download applies it", async () => {
  const hostile = "=HYPERLINK(\"https://example.org\",\"open\")";
  const { csv } = await csvFor({ id: "not-a-real-collection", name: hostile, blurb: "\t=1+1" });
  const values = parseCsv(csv).rows.map((row) => row.value);
  assert.ok(values.includes(`'${hostile}`), csv);
  assert.ok(values.includes("'\t=1+1"), csv);
});

// A real shipped sample with one cell made hostile, written back with plain
// quoting so nothing but `collectionCsv` can neutralize it.
const quoted = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;

test("the preview download applies it", () => {
  let checked = 0;
  for (const { id } of LAUNCH_COLLECTION) {
    if (!hasSample(id)) continue;
    const text = readFileSync(new URL(`../../../public${samplePath(id)}`, import.meta.url), "utf8");
    const { columns, rows } = parseCsv(text);
    if (!rows.length) continue;
    rows[0][columns[0]] = "=1+1";
    const hostile = [columns, ...rows.map((row) => columns.map((name) => row[name]))]
      .map((row) => row.map(quoted).join(",")).join("\n");
    const out = collectionCsv(id, hostile);
    if (out == null) continue;
    assert.equal(parseCsv(out).rows[0][columns[0]], "'=1+1", id);
    checked += 1;
  }
  assert.ok(checked > 0, "at least one shipped preview was checked");
});
