import assert from "node:assert/strict";
import test from "node:test";

import { spreadsheetDefaultColumns } from "../../../scripts/derive-explore.mjs";
import { CONTRACTS, SOURCE_LINK_COLUMN, labelFor, meaningFor, rowDate, rowSource } from "./explore.js";
import { columnPlan } from "./recordColumns.js";

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

test("installed producer contracts open on their curated columns and retain raw row context", () => {
  const current = Object.entries(CONTRACTS).filter(([, contract]) => contract.mapping_kind === "producer_spreadsheet");
  assert.ok(current.length > 0, "no current producer spreadsheets");
  for (const [key, contract] of current) {
    const columns = [...new Set([
      ...contract.default_columns, ...(contract.observation ?? []),
      contract.entity_uid, contract.entity_name, contract.entity_type,
      "record_type", "record_key", "record_grain",
    ].filter(Boolean))];
    const plan = columnPlan(key, contract, columns);
    const componentSources = new Set([
      "consultation_participants__source_url", "federal_actions__source_url", "html_url",
    ]);
    const expected = contract.row_type_contracts
      ? [...contract.default_columns.filter((column) => !componentSources.has(column)), SOURCE_LINK_COLUMN]
      : contract.default_columns;
    assert.deepEqual(plan.defaults, expected, key);
    assert.ok(plan.defaults.length <= 8, key + ": opening view exceeds eight columns");
    for (const column of ["record_type", "record_key", "record_grain"]) {
      assert.ok(plan.all.includes(column), key + ": raw row context lost");
    }
    if (key !== "need/need") {
      if (!contract.row_type_contracts) assert.ok(!plan.defaults.includes("record_type"), key);
      assert.ok(!plan.defaults.includes("record_key"), key);
      assert.ok(!plan.defaults.includes("record_grain"), key);
    }
  }
});

test("NEED keeps its seven reviewed enterprise and relationship columns", () => {
  const contract = CONTRACTS["need/need"];
  assert.ok(contract);
  assert.deepEqual(contract.default_columns, ["enterprise_name", "related_entity_name", "relationship_type", "ownership_extent", "uei", "cage_code", "record_grain"]);
  const plan = columnPlan("need/need", contract, [
    ...contract.default_columns, "record_type", "record_key", "evidence_pins",
  ]);
  assert.deepEqual(plan.defaults, contract.default_columns);
  assert.ok(plan.all.includes("evidence_pins"));
});

test("Federal Register keeps separate component dates and sources within the curated view", () => {
  const contract = CONTRACTS["federal-register/federal-register"];
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
