import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { parseCsv, universalRows } from "./explore.js";
import { enrichSample } from "./exampleEnrichment.js";
import { EXCLUDED_EXAMPLES, showcaseItems } from "./showcase.js";
import { readableCode, repairMojibake } from "./readerPresentation.js";
import { viewerItems } from "./useSamples.js";

const sample = (id) => parseCsv(readFileSync(new URL(`../../../public/data/cedar/downloads/${id}.csv`, import.meta.url), "utf8"));
const items = (id, parsed = sample(id)) => universalRows(`${id}/${id}`, parsed.rows);

test("every excluded example names a record the pinned sample actually holds", () => {
  for (const [id, records] of Object.entries(EXCLUDED_EXAMPLES)) {
    const ids = new Set(items(id).map((item) => item.recordId));
    for (const recordId of Object.keys(records)) assert.ok(ids.has(recordId), `${id}: ${recordId} is not in the sample`);
  }
});

test("the landing showcase leaves out the records the audit found misleading, and never abandons a rule for a minimum count", () => {
  const shown = showcaseItems("legislation", items("legislation"));
  assert.ok(!shown.some((item) => item.recordId === "100-hr-2642"));
  // Prime Contracting shows only records with a Native entity and a positive
  // obligation, however few.
  const contracts = showcaseItems("contractors", items("contractors"));
  assert.ok(contracts.every((item) => (item.entity.name || item.entity.uid) && item.amount > 0));
  assert.equal(contracts.length, items("contractors").filter((item) => (item.entity.name || item.entity.uid) && item.amount > 0).length);
  // Legislation shows only bills that name a Native entity.
  assert.ok(shown.length && shown.every((item) => item.entity.name || item.entity.uid));
  // The door's first screen shows no $0 or negative obligation.
  assert.ok(showcaseItems("funding", items("funding")).every((item) => item.amount > 0));
});

test("monthly subaward reports are distinct observations: the showcase reorders them and drops none", () => {
  const all = items("subcontracting");
  const attributed = all.filter((item) => item.entity.name || item.entity.uid);
  const subs = showcaseItems("subcontracting", all);
  assert.equal(subs.length, attributed.length);
  // Each report carries its own source report id, so none is a duplicate.
  const reports = all.map((item) => item.row.report_id);
  assert.equal(new Set(reports).size, reports.length);
  // Different subawards come before a repeat of the same one.
  const key = (item) => [item.row.subaward_number, item.row.subcontractor_name, item.row.prime_name].join("|");
  const firstRepeat = subs.findIndex((item, index) => subs.slice(0, index).some((other) => key(other) === key(item)));
  const distinct = new Set(subs.map(key)).size;
  assert.equal(firstRepeat, distinct);
});

test("the analytical viewer shows exactly the downloaded records, deobligations and repeats included", () => {
  for (const id of ["contractors", "deals", "federal-register", "foundation-corporate-giving", "funding", "legislation", "lobbying", "nagpra", "natural-resources", "need", "nonprofits", "owned", "plot", "subcontracting"]) {
    const downloaded = sample(id);
    const viewed = viewerItems(`${id}/${id}`, downloaded);
    assert.equal(viewed.length, downloaded.rows.length, id);
    // Same records, same order, same values as the file the reader downloads.
    viewed.forEach((item, index) => {
      for (const [column, value] of Object.entries(downloaded.rows[index])) {
        assert.equal(item.row[column], value, `${id} row ${index} ${column}`);
      }
    });
  }
  const funding = viewerItems("funding/funding", sample("funding"));
  assert.ok(funding.some((item) => Number(item.row.obligations_usd) < 0), "the deobligation is kept");
  assert.ok(funding.some((item) => Number(item.row.obligations_usd) === 0), "the $0 action is kept");
});

test("every NEED example names its ultimate Native owner in the download itself, with a basis and a public source", () => {
  const parsed = sample("need");
  for (const column of ["native_owner", "native_owner_cedar_uid", "native_owner_basis", "native_owner_source"]) {
    assert.ok(parsed.columns.includes(column), column);
  }
  for (const row of parsed.rows) {
    assert.ok(row.native_owner, `${row.enterprise_name}: no Native owner`);
    assert.match(row.native_owner_cedar_uid, /^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$/);
    assert.ok(row.native_owner_basis.length > 10, `${row.enterprise_name}: no basis`);
    assert.match(row.native_owner_source, /^https:\/\//);
    assert.ok(!row.native_owner_source.includes("github.com/teim-team"), `${row.enterprise_name}: private source`);
  }
  // The viewer adds no NEED record or owner of its own.
  assert.equal(enrichSample("need", parsed), parsed);
  // Each record links to that owner.
  for (const item of viewerItems("need/need", parsed)) assert.equal(item.entity.uid, item.row.native_owner_cedar_uid);
});

test("an individually owned business shows the tribe its registry lists, not only the certifier", () => {
  const parsed = enrichSample("owned", sample("owned"));
  assert.ok(parsed.columns.includes("stated_tribe"));
  assert.ok(parsed.rows.every((row) => row.stated_tribe));
  assert.ok(parsed.rows.some((row) => row.stated_tribe === "Three Affiliated Tribes"));
});

test("source codes and garbled characters read as text", () => {
  assert.equal(readableCode("NOT_EVALUATED"), "Not evaluated");
  assert.equal(readableCode("b_native_as_subawardee"), "B native as subawardee");
  assert.equal(readableCode("Ho-Chunk"), "Ho-Chunk");
  assert.equal(readableCode("Cherokee Nation"), "Cherokee Nation");
  assert.equal(repairMojibake("CNSPÃ¢Â‚Â¬Â„Â¢S"), "CNSP’S");
  assert.equal(repairMojibake("Tribeâ€™s"), "Tribe’s");
  assert.equal(repairMojibake("Iñupiat"), "Iñupiat");
});

// Bindings an audit of 2026-10-06 found wrong. The correction belongs to the
// producer (docs/handoffs/CODEX_LANDING_FOLLOWUPS_2026-10-06.md); until it
// lands, the door leaves each record out. When a re-pinned release fixes a
// binding, this test fails on purpose: delete the entry here and the
// matching exclusion in showcase.js in the same change.
const KNOWN_WRONG_BINDINGS = [
  // Pub. L. 100-585 settles the Southern Ute and Ute Mountain Ute claims.
  { collection: "legislation", record: "100-hr-2642", wrongUid: "CE-001BW-3N" },
  // The notice names the Duckwater Shoshone Tribe, not the BIE school.
  { collection: "nagpra", record: "00-11378", wrongUid: "CE-000E9-W1" },
];

test("known wrong bindings are still in the pinned data and kept off the door", () => {
  for (const { collection, record, wrongUid } of KNOWN_WRONG_BINDINGS) {
    const all = items(collection);
    const row = all.find((item) => item.recordId === record);
    assert.ok(row, `${collection} ${record} is no longer pinned: remove it from KNOWN_WRONG_BINDINGS and EXCLUDED_EXAMPLES`);
    assert.ok(JSON.stringify(row.row).includes(wrongUid), `${collection} ${record} no longer carries ${wrongUid}: the producer fixed it`);
    assert.ok(!showcaseItems(collection, all).some((item) => item.recordId === record), `${collection} ${record} reached the door`);
  }
  // The giving record keeps the recipient as the report printed it and is
  // not bound to the NB3 Foundation without the report saying so.
  const gift = items("foundation-corporate-giving").find((item) => item.recordId === "FF-03B9C4E5A6CA00E15034");
  assert.equal(gift.row.recipient_name_reported, "Notah Begay");
  assert.equal(gift.row.cedar_uid ?? "", "");
});
