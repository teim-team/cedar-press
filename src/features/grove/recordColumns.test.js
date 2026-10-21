import assert from "node:assert/strict";
import test from "node:test";

import { spreadsheetDefaultColumns } from "../../../scripts/derive-explore.mjs";
import { downloadRecord } from "./customerTables.js";
import { CONTRACTS, SOURCE_LINK_COLUMN, labelFor, meaningFor } from "./explore.js";
import { DISPLAY_DEFAULTS } from "./showcase.js";
import { columnPlan } from "./recordColumns.js";
import { loadCodebook } from "./codebook.js";
// The codebook loads on demand in the browser (codebook.js); the readers
// under test read it synchronously once it has.
await loadCodebook();

const contractor = {
  mapping_kind: "customer_table",
  entity_name: "canonical_name",
  entity_uid: "cedar_uid",
  entity_role_column: "cedar_entity_role",
  subject: "award_description",
  amount: "obligations_usd",
  amount_basis: "amount_basis",
  date: "action_date",
  source: "source_url",
  observation: ["record_type", "award_description", "agency_name", "program_name", "record_grain"],
};
const contractorColumns = [
  "record_type", "record_key", "record_grain", "cedar_uid", "canonical_name",
  "cedar_entity_role", "award_description", "agency_name", "program_name",
  "obligations_usd", "amount_basis", "action_date", "source_url",
];

test("the opening spreadsheet keeps amount and its qualification before extra observations", () => {
  const contract = structuredClone(contractor);
  const before = structuredClone(contract);
  contract.default_columns = spreadsheetDefaultColumns(contract, contractorColumns);
  assert.deepEqual(contract.default_columns, [
    "award_description", "canonical_name", "cedar_entity_role", "obligations_usd",
    "amount_basis", "action_date", "agency_name", "source_url",
  ]);
  const { defaults, all } = columnPlan(null, contract, contractorColumns);
  assert.deepEqual(defaults, contract.default_columns);
  assert.equal(defaults.length, 8);
  assert.ok(defaults.indexOf("obligations_usd") < 6, "amount disappeared from the visible opening columns");
  for (const column of contractorColumns) assert.ok(all.includes(column), column);
  for (const column of ["record_type", "record_key", "record_grain", "program_name"]) {
    assert.ok(!defaults.includes(column), column);
  }
  delete contract.default_columns;
  assert.deepEqual(contract, before, "presentation selection changed the entity or amount contract");
});

test("the individual business leads the business spreadsheet, with its certifier separately qualified", () => {
  const c = CONTRACTS["owned/owned"];
  assert.equal(c.subject, "business_name");
  assert.equal(c.default_columns[0], "business_name");
  assert.ok(c.default_columns.indexOf("canonical_name") > 0);
  assert.ok(c.default_columns.includes("cedar_entity_role"));
});

test("the resource codebook retains measurement qualifications instead of implying every row is a payment", () => {
  const key = "natural-resources/natural-resources";
  assert.equal(labelFor(key, "measurement_status"), "Measurement basis");
  assert.equal(labelFor(key, "resource_revenue_event_id"), "Observation ID");
  assert.match(meaningFor(key, "amount_usd"), /appropriation, allocation/);
  assert.match(meaningFor(key, "recipient_name"), /not automatically a canonical Cedar entity/);
});

test("currency displaces a descriptive column instead of an amount qualification or source", () => {
  const columns = [...contractorColumns, "currency"];
  const defaults = spreadsheetDefaultColumns(contractor, columns);
  assert.equal(defaults.length, 8);
  assert.ok(defaults.includes("obligations_usd"));
  assert.ok(defaults.includes("amount_basis"));
  assert.ok(defaults.includes("currency"));
  assert.ok(defaults.includes("source_url"));
  assert.ok(!defaults.includes("agency_name"));
});

test("too many mandatory meanings fail for a reviewed choice instead of silently losing a qualification", () => {
  const contract = { ...contractor, currency: "stated_currency" };
  assert.throws(
    () => spreadsheetDefaultColumns(contract, [...contractorColumns, "currency", "stated_currency"]),
    /reviewed choice/,
  );
});

test("a default declaration does not expand again from an overlapping observation list", () => {
  const contract = {
    ...contractor,
    default_columns: ["canonical_name", "award_description", "obligations_usd", "amount_basis", "action_date", "source_url"],
  };
  const plan = columnPlan(null, contract, contractorColumns);
  assert.deepEqual(plan.defaults, contract.default_columns);
  assert.ok(plan.all.includes("agency_name"));
  assert.ok(plan.all.includes("cedar_entity_role"));
});

test("legacy tables keep their role-first source-link behavior", () => {
  const legacy = {
    entity_name: "recipient",
    observation: ["program"],
    amount: "amount",
    date: "date",
    default_columns: ["award_id"],
    source_builder: { kind: "usaspending_award", column: "award_id" },
  };
  const plan = columnPlan(null, legacy, ["recipient", "program", "amount", "date", "award_id"]);
  assert.deepEqual(plan.defaults, ["recipient", "program", "amount", "date", SOURCE_LINK_COLUMN, "award_id"]);
  assert.ok(plan.all.includes(SOURCE_LINK_COLUMN));
});

test("installed customer contracts open on their declared columns and carry no packaging column", () => {
  const current = Object.entries(CONTRACTS);
  assert.equal(current.length, 14);
  for (const [key, contract] of current) {
    assert.equal(contract.mapping_kind, "customer_table", key);
    const header = downloadRecord(key.split("/")[0])?.header;
    assert.ok(header?.length, key + ": no rendered customer table");
    const plan = columnPlan(key, contract, header);
    // The declared view, or the showcase's display defaults where the
    // declared one opened on blank or misleading columns (showcase.js,
    // owner audit 2026-10-06); either way every column is one the table has.
    const collection = key.split("/")[0];
    const expected = DISPLAY_DEFAULTS[collection]?.filter((column) => header.includes(column)) ?? contract.default_columns;
    assert.deepEqual(plan.defaults, expected.length >= 3 ? expected : contract.default_columns, key);
    for (const column of plan.defaults) assert.ok(header.includes(column), key + ": opens on " + column);
    assert.ok(plan.defaults.length <= 8, key + ": opening view exceeds eight columns");
    for (const column of header) assert.ok(plan.all.includes(column), key + ": customer column lost " + column);
    for (const column of ["record_type", "record_key", "record_grain"]) {
      assert.ok(!plan.all.includes(column), key + ": packaging column " + column);
    }
  }
});

test("NEED keeps its reviewed enterprise and relationship columns, and opens on the Native owner", () => {
  const contract = CONTRACTS["need/need"];
  assert.ok(contract);
  assert.deepEqual(contract.default_columns, ["enterprise_name", "related_entity_name", "relationship_type", "ownership_extent", "uei", "cage_code"]);
  const header = downloadRecord("need").header;
  // The pinned file has no owner column; the viewer adds the evidenced one
  // (exampleEnrichment.js) and opens on it.
  const plan = columnPlan("need/need", contract, [...header, "native_owner", "native_owner_basis"]);
  // Owner, 2026-10-07: Cedar's column (the Native owner) leads.
  assert.deepEqual(plan.defaults, ["native_owner", "enterprise_name", "related_entity_name", "relationship_type", "uei", "cage_code"]);
  assert.ok(plan.all.includes("source_urls"));
  // The retired enterprise scheme is not a column a reader can open.
  assert.ok(!header.includes("enterprise_id"));
});

test("the served Federal Register table has one date and one source", () => {
  const served = CONTRACTS["federal-register/federal-register"];
  assert.equal(served.row_type_contracts ?? null, null);
  assert.equal(served.date, "publication_date");
  assert.equal(served.source, "source_url");
});

test("resource amounts keep measurement and sign qualifications together", () => {
  const contract = {
    ...contractor, amount: "amount_usd", amount_basis: "measurement_status",
  };
  const columns = [
    ...contractorColumns, "amount_usd", "measurement_status", "amount_sign_meaning",
  ];
  const defaults = spreadsheetDefaultColumns(contract, columns);
  assert.equal(defaults.length, 8);
  for (const column of ["amount_usd", "measurement_status", "amount_sign_meaning", "source_url"]) {
    assert.ok(defaults.includes(column), column);
  }
  assert.ok(!defaults.includes("agency_name"));
});

test("a missing declared date still permits the existing declared year", () => {
  const defaults = spreadsheetDefaultColumns({
    date: "absent_date", year: "fiscal_year", source: "source_url",
  }, ["fiscal_year", "source_url"]);
  assert.deepEqual(defaults, ["fiscal_year", "source_url"]);
});
