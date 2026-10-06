import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { parseCsv, universalRows } from "./explore.js";
import { enrichSample, NEED_EXAMPLE_EVIDENCE } from "./exampleEnrichment.js";
import { EXCLUDED_EXAMPLES, showcaseItems } from "./showcase.js";
import { readableCode, repairMojibake } from "./readerPresentation.js";

const sample = (id) => parseCsv(readFileSync(new URL(`../../../public/data/cedar/downloads/${id}.csv`, import.meta.url), "utf8"));
const items = (id, parsed = sample(id)) => universalRows(`${id}/${id}`, parsed.rows);

test("every excluded example names a record the pinned sample actually holds", () => {
  for (const [id, records] of Object.entries(EXCLUDED_EXAMPLES)) {
    const ids = new Set(items(id).map((item) => item.recordId));
    for (const recordId of Object.keys(records)) assert.ok(ids.has(recordId), `${id}: ${recordId} is not in the sample`);
  }
});

test("the showcase leaves out the records the audit found misleading, and keeps at least three", () => {
  const shown = showcaseItems("legislation", items("legislation"));
  assert.ok(!shown.some((item) => item.recordId === "100-hr-2642"));
  for (const id of ["contractors", "subcontracting", "funding", "nagpra", "foundation-corporate-giving"]) {
    assert.ok(showcaseItems(id, items(id)).length >= 3, id);
  }
  // Prime Contracting shows only records with a Native entity.
  assert.ok(showcaseItems("contractors", items("contractors")).every((item) => item.entity.name || item.entity.uid));
  // One subaward re-filed monthly shows once.
  const subs = showcaseItems("subcontracting", items("subcontracting"));
  const keys = subs.map((item) => [item.row.subaward_number, item.row.subcontractor_name, item.row.prime_name].join("|"));
  assert.equal(new Set(keys).size, keys.length);
  // Funding shows no $0 or negative obligation.
  assert.ok(showcaseItems("funding", items("funding")).every((item) => item.amount > 0));
});

test("NEED examples name their top-level Native owner, with evidence, and include tribe-owned enterprises", () => {
  const parsed = enrichSample("need", sample("need"));
  assert.ok(parsed.columns.includes("native_owner"));
  for (const row of parsed.rows) {
    assert.ok(row.native_owner, `${row.enterprise_name}: no Native owner`);
    assert.ok(row.native_owner_basis.length > 30, `${row.enterprise_name}: no evidence`);
    assert.match(row.native_owner_cedar_uid, /^CE-[0-9A-Z]{5}-[0-9A-Z]{2}$/);
  }
  const owners = new Set(parsed.rows.map((row) => row.native_owner));
  for (const owner of ["Arctic Slope Regional Corporation", "Ahtna, Incorporated", "The Chickasaw Nation", "The Choctaw Nation of Oklahoma"]) {
    assert.ok(owners.has(owner), owner);
  }
  // A tribe-owned enterprise is the first record a reader sees.
  assert.equal(parsed.rows[0].native_owner, "The Chickasaw Nation");
  // Every tribal example carries the federal identifiers its ruling is keyed by.
  for (const example of NEED_EXAMPLE_EVIDENCE.tribal) {
    assert.match(example.uei, /^[0-9A-Z]{12}$/);
    assert.match(example.cage_code, /^[0-9A-Z]{5}$/);
  }
  // Every other collection is untouched.
  const funding = sample("funding");
  assert.equal(enrichSample("funding", funding), funding);
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
