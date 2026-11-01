import test from "node:test";
import assert from "node:assert/strict";
import { spreadsheetDownloadUrl } from "../../api.js";
import { researchComponents, spreadsheetRecordCount } from "./releaseResearch.js";

const pin = "a".repeat(64);

test("component and native requests preserve exact pins without treating a held count as available", () => {
  assert.equal(researchComponents({ release: { kind: "full", table_id: "prime_contracts", release_id: pin, record_count: 20 } })[0].component, null);
  const parts = researchComponents({ release: [
    { kind: "full", component: "facts", release_id: pin, record_count: 20 },
    { kind: "full", table_id: "holds", status: "unavailable", record_count: 999 },
  ] });
  assert.equal(parts[0].component, "facts");
  assert.equal(parts[1].available, false);
});

test("the record count is shown only when the spreadsheet and its parts agree", () => {
  const spreadsheet = { kind: "spreadsheet", format: "csv", release_id: pin, record_count: 30 };
  const release = [
    { kind: "full", component: "facts", release_id: pin, record_count: 20 },
    { kind: "full", component: "events", release_id: pin, record_count: 10 },
  ];
  assert.equal(spreadsheetRecordCount({ release, spreadsheet }), 30);
  assert.equal(spreadsheetRecordCount({ release, spreadsheet: { ...spreadsheet, record_count: 31 } }), null);
  assert.equal(spreadsheetRecordCount({ release: [{ ...release[0], release_id: "b".repeat(64) }], spreadsheet }), null);
  assert.equal(spreadsheetRecordCount({ release: null, spreadsheet }), null);
});

test("the spreadsheet download requires matching verified metadata", () => {
  const meta = { kind: "spreadsheet", format: "csv", release_id: pin };
  const parts = [{ available: true, releaseId: pin }];
  assert.equal(spreadsheetDownloadUrl("plot", meta, parts), `/press/collections/plot/spreadsheet-download?release_id=${pin}`);
  assert.equal(spreadsheetDownloadUrl("plot", { ...meta, release_id: "b".repeat(64) }, parts), null);
  assert.equal(spreadsheetDownloadUrl("plot", meta, []), null);
  assert.equal(spreadsheetDownloadUrl("gaming", meta, parts), null);
  assert.equal(spreadsheetDownloadUrl("../plot", meta, parts), null);
});
