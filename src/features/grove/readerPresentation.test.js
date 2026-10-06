import assert from "node:assert/strict";
import test from "node:test";
import { isRetiredIdentifierColumn, readerValueLabel, recordTypeLabel, sampleRecordCount, unlinkedRecordSubject } from "./readerPresentation.js";
import { universalRows } from "./explore.js";
import { columnPlan } from "./recordColumns.js";
import { researchComponents, researchFields, spreadsheetRecordCount } from "./releaseResearch.js";

test("phone record subjects preserve the named business without asserting an entity link", () => {
  const row = { enterprise_name: "Example subsidiary", owner_name: "Example immediate owner", owner_scope: "immediate", ownership_extent: "wholly_owned", relationship_type: "owned_by" };
  const contract = { subject: "enterprise_name", observation: ["owner_name", "ownership_extent", "relationship_type"] };
  const [item] = universalRows("need/need", [row], undefined, contract);
  assert.equal(unlinkedRecordSubject(item), "Example subsidiary");
  assert.equal(item.entity.entities.length, 0);
  assert.equal(item.observation, "Wholly owned by Example immediate owner (immediate owner)");
  assert.equal(item.row.ownership_extent, "wholly_owned");
  const [unresolved] = universalRows("need/need", [{ ...row, relationship_type: "candidate_relation" }], undefined, contract);
  assert.equal(unresolved.observation, "Example immediate owner · Wholly owned · candidate_relation");
  assert.equal(unlinkedRecordSubject({ ...item, linkStatus: "withheld" }), null);
  assert.equal(unlinkedRecordSubject({ ...item, entity: { withheld: true } }), null);
});

test("only explicit national aggregates get that subject; missing identity is not an inferred aggregate", () => {
  const item = { collection: "natural-resources", row: { aggregation_level: "national_aggregate" } };
  assert.equal(unlinkedRecordSubject(item), "National aggregate");
  assert.equal(unlinkedRecordSubject({ ...item, row: {} }), null);
  assert.equal(unlinkedRecordSubject({ ...item, collection: "owned" }), null);
});

test("reviewed labels preserve value semantics and never rewrite identifiers or unknown values", () => {
  assert.equal(readerValueLabel("lobbying", "amount_basis", "none_reported"), "No amount reported");
  assert.equal(readerValueLabel("natural-resources", "measurement_status", "appropriated_amount"), "Appropriated amount");
  assert.equal(readerValueLabel("owned", "cedar_entity_role", "certifying_authority"), "Certifying authority");
  assert.equal(readerValueLabel("owned", "record_key", "certifying_authority"), "certifying_authority");
  assert.equal(readerValueLabel("need", "relationship_type", "candidate_relation"), "candidate_relation");
  assert.equal(readerValueLabel("need", "relationship_type", null), null);
});

test("both preview column selectors omit retired entity schemes but preserve event IDs", () => {
  const retired = ["CICD_ID", "same_as_legacy_cicd", "tribe_id", "tribe_id_scheme", "tribe_id_neid", "handle", "owner_hub_handle"];
  const retained = ["cedar_uid", "canonical_name", "award_id", "filing_uuid", "document_number", "source_url", "handler_name"];
  for (const name of retired) assert.equal(isRetiredIdentifierColumn(name), true, name);
  for (const name of retained) assert.equal(isRetiredIdentifierColumn(name), false, name);
  const columns = [...retired, ...retained];
  const plan = columnPlan(null, {
    entity_uid: "tribe_id_neid", entity_name: "canonical_name",
    observation: ["handle", "document_number"], default_columns: columns,
  }, columns);
  assert.deepEqual(plan.all, ["canonical_name", ...retained.filter((name) => name !== "canonical_name")]);
  for (const name of retired) {
    assert.equal(plan.defaults.includes(name), false, name);
    assert.equal(plan.lead.includes(name), false, name);
  }
  const fields = columns.map((name) => ({ name, display_disposition: "keep" }));
  assert.deepEqual(researchFields({ display_order: columns, codebook: { fields } }).map((field) => field.name), retained);
});

test("record type labels use maintained names without exposing storage spellings", () => {
  assert.equal(recordTypeLabel({ component: "environmental_permits" }), "Environmental permits");
  assert.equal(recordTypeLabel({ table_id: "fr_nagpra_title_index" }), "FR NAGPRA title index");
  assert.equal(recordTypeLabel({ component: "facts", label: "Permit decisions" }), "Permit decisions");
  assert.equal(recordTypeLabel(null, "Federal funding"), "Federal funding");
  const [part] = researchComponents({ name: "PLOT", release: [
    { component: "environmental_events", kind: "full", release_id: "a".repeat(64), record_count: 10 },
  ] });
  assert.equal(part.label, "Environmental events");
  assert.equal(part.component, "environmental_events");
});

test("a connected spreadsheet count comes from matching permitted release metadata", () => {
  const pin = "a".repeat(64);
  const first = { kind: "full", component: "permits", release_id: pin, record_count: 12 };
  const second = { ...first, component: "events", record_count: 8 };
  const target = { release: [first, second], spreadsheet: {
    kind: "spreadsheet", format: "csv", release_id: pin, record_count: 20,
  } };
  assert.equal(spreadsheetRecordCount(target), 20);
  assert.equal(spreadsheetRecordCount({ ...target, release: [first, second, {
    kind: "full", status: "unavailable", component: "held", record_count: 999,
  }] }), 20);
  for (const change of [
    { spreadsheet: null },
    { spreadsheet: { ...target.spreadsheet, record_count: 21 } },
    { spreadsheet: { ...target.spreadsheet, record_count: "20" } },
    { spreadsheet: { ...target.spreadsheet, record_count: -1 } },
    { spreadsheet: { ...target.spreadsheet, release_id: "b".repeat(64) } },
    { release: [first, { ...second, release_id: "b".repeat(64) }] },
    { release: [] },
  ]) assert.equal(spreadsheetRecordCount({ ...target, ...change }), null);
  assert.equal(spreadsheetRecordCount({ release: first, spreadsheet: {
    ...target.spreadsheet, record_count: 12,
  } }), 12);
});

test("sample counts accept measured zero and refuse absent or coerced values", () => {
  assert.equal(sampleRecordCount(0), 0);
  assert.equal(sampleRecordCount(10), 10);
  for (const value of [null, undefined, "10", -1, 1.5, NaN, Infinity]) {
    assert.equal(sampleRecordCount(value), null);
  }
});
