import assert from "node:assert/strict";
import test from "node:test";

import { readFileSync } from "node:fs";

import manifest from "../../../data/cedar/collections.manifest.json" with { type: "json" };
import { spreadsheetContract, spreadsheetDefaultColumns } from "../../../scripts/derive-explore.mjs";
import { downloadRecord } from "./customerTables.js";
import { CONTRACTS, SOURCE_LINK_COLUMN, labelFor, meaningFor, parseCsv, rowDate, rowSource } from "./explore.js";
import { DISPLAY_DEFAULTS } from "./showcase.js";
import { columnPlan } from "./recordColumns.js";
import { loadCodebook } from "./codebook.js";
// The codebook loads on demand in the browser (codebook.js); the readers
// under test read it synchronously once it has.
await loadCodebook();

const contractor = {
  mapping_kind: "producer_spreadsheet",
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
  assert.deepEqual(plan.defaults, ["enterprise_name", "native_owner", "related_entity_name", "relationship_type", "uei", "cage_code"]);
  assert.ok(plan.all.includes("source_urls"));
  // The retired enterprise scheme is not a column a reader can open.
  assert.ok(!header.includes("enterprise_id"));
});

test("Federal Register keeps separate component dates and sources within the curated view", () => {
  // The served table is the flat federal-action table: one date, one source.
  const served = CONTRACTS["federal-register/federal-register"];
  assert.equal(served.row_type_contracts ?? null, null);
  assert.equal(served.date, "publication_date");
  assert.equal(served.source, "source_url");
  // The producer preview it is rendered from is a union of two components;
  // its contract (derive-explore spreadsheetContract) still dispatches each
  // row's date and source by record type.
  const table = manifest.collections.find((c) => c.id === "federal-register").tables
    .find((t) => t.table === "federal-register.csv");
  const raw = parseCsv(readFileSync(new URL("../../.." + table.sample_path, import.meta.url), "utf8"));
  const contract = spreadsheetContract(raw.columns, raw.rows, { collection: "federal-register", record_type_fields: table.record_type_fields });
  assert.ok(contract?.row_type_contracts);
  assert.ok(contract.default_columns.length <= 8);
  assert.ok(contract.default_columns.includes("record_type"));
  assert.equal(contract.row_type_contracts.consultation_participants.label, "Consultation participant");
  assert.equal(contract.row_type_contracts.federal_actions.label, "Federal action");
  for (const column of [
    "notice_date", "publication_date",
    "consultation_participants__source_url", "federal_actions__source_url",
  ]) assert.ok(contract.default_columns.includes(column), column);
  assert.ok(!contract.default_columns.includes("html_url"));
  const plan = columnPlan("federal-register/federal-register", contract, [
    ...contract.default_columns, "html_url",
  ]);
  assert.equal(plan.defaults.length, 7);
  assert.equal(plan.defaults.filter((column) => column === SOURCE_LINK_COLUMN).length, 1);
  for (const column of ["record_type", "notice_date", "publication_date"]) {
    assert.ok(plan.defaults.includes(column), column);
  }
  for (const column of [
    "consultation_participants__source_url", "federal_actions__source_url", "html_url",
  ]) {
    assert.ok(!plan.defaults.includes(column), column + ": sparse source column remains in opening view");
    assert.ok(plan.all.includes(column), column + ": raw source column lost");
  }
  assert.ok(plan.all.includes(SOURCE_LINK_COLUMN));
  const participant = {
    record_type: "consultation_participants",
    notice_date: "2024-01-02", publication_date: "1999-01-01",
    consultation_participants__source_url: "https://www.federalregister.gov/documents/2024/01/02/2024-00001/example",
    federal_actions__source_url: "https://www.govinfo.gov/content/pkg/FR-1999-01-01/pdf/example.pdf",
  };
  assert.equal(rowDate(participant, contract), participant.notice_date);
  assert.equal(rowSource(participant, contract), participant.consultation_participants__source_url);
  const action = { ...participant, record_type: "federal_actions" };
  assert.equal(rowDate(action, contract), action.publication_date);
  assert.equal(rowSource(action, contract), action.federal_actions__source_url);
  action.federal_actions__source_url = "";
  action.html_url = "https://www.federalregister.gov/documents/1999/01/01/1999-00001/example";
  assert.equal(rowSource(action, contract), action.html_url);
  // The one displayed source follows each row's own component contract.
  // Federal-action HTML fallback must not become a consultation source.
  assert.equal(rowSource({
    ...participant, consultation_participants__source_url: "", html_url: action.html_url,
  }, contract), null);
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
  const union = spreadsheetDefaultColumns({
    row_type_contracts: {
      first: { date: "absent_date", year: "source_year", source: "first_source" },
      second: { date: "notice_date", year: "unused_year", source: "second_source" },
    },
  }, ["source_year", "notice_date", "unused_year", "first_source", "second_source"]);
  assert.deepEqual(union, ["source_year", "notice_date", "first_source", "second_source"]);
});
