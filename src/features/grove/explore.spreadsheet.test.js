import { columnPlan } from "./recordColumns.js";
import { rowDate, rowYear, SOURCE_LINK_COLUMN } from "./explore.js";
import { observationOf } from "./explore.js";
import assert from "node:assert/strict";
import test from "node:test";
import { spreadsheetContract } from "../../../scripts/derive-explore.mjs";
import { universalRows, rowEntities, rowEntity, rowRecordId, rowAmount, rowSource, entityVectors, publicRow } from "./explore.js";
import { loadCodebook } from "./codebook.js";
// The codebook loads on demand in the browser (codebook.js); the readers
// under test read it synchronously once it has.
await loadCodebook();

const base = ["record_type", "record_key", "record_grain"];

test("unattributed resource revenue keeps its own description without inventing a recipient", () => {
  const columns = [...base, "canonical_name", "cedar_uid", "commodity", "resource_type", "revenue_type"];
  const contract = spreadsheetContract(columns);
  const row = { record_type: "records", commodity: "Other royalties", resource_type: "mixed", revenue_type: "royalty", canonical_name: "", cedar_uid: "" };
  assert.match(observationOf(row, contract), /Other royalties/);
  assert.deepEqual(rowEntities(row, contract), []);
  assert.ok(!contract.default_columns.includes("record_key"));
});

test("producer keys preserve component grain even when other source IDs repeat", () => {
  const c = spreadsheetContract([...base, "transaction_id", "obligations_usd", "source_url"]);
  const row = { record_key: '["transaction","1"]', transaction_id: "1", obligations_usd: "-7.25", source_url: "https://example.org/source" };
  assert.equal(rowRecordId(row, c), row.record_key);
  assert.equal(rowAmount(row, c), -7.25);
  assert.equal(rowSource(row, c), row.source_url);
  const plan = columnPlan(null, c, [...base, "transaction_id", "obligations_usd", "source_url"]);
  assert.ok(plan.all.includes("record_grain"));
  assert.ok(plan.all.includes("record_key"));
  assert.throws(() => spreadsheetContract(["record_key"]), /record_type/);
});

test("reviewed NEED business and owner names never manufacture a CE association", () => {
  const c = spreadsheetContract([...base, "enterprise_id", "enterprise_name", "owner_name", "uei", "cage_code", "evidence_pins"]);
  const row = { enterprise_id: "CEDAR-NEST-1", enterprise_name: "Example Company", owner_name: "Example Owner", uei: "ABC123DEF456" };
  assert.equal(c.entity_uid, null);
  assert.equal(c.entity_name, null);
  assert.equal(c.subject, "enterprise_name");
  assert.deepEqual(rowEntities(row, c), []);
});

test("plural producer entities retain each source role despite blank or repeated IDs", () => {
  const c = spreadsheetContract([...base, "cedar_uids", "canonical_names", "entity_classes", "entity_roles"]);
  const row = {
    cedar_uids: '["CE-AAA00-AA",null,"CE-BBB00-BB","CE-AAA00-AA"]',
    canonical_names: '["First","Unresolved","Second","First"]',
    entity_classes: '["First class",null,"Second class","First class"]',
    entity_roles: '["recipient","unresolved","consulted","beneficiary"]',
  };
  const entities = rowEntities(row, c);
  assert.deepEqual(entities.map(e => [e.uid, e.name, e.type, e.role]), [
    ["CE-AAA00-AA", "First", "First class", "recipient"],
    ["CE-BBB00-BB", "Second", "Second class", "consulted"],
  ]);
  assert.deepEqual(entities[0].roles, ["beneficiary"]);
  assert.equal(entityVectors({ entities }, c).roles, "recipient; beneficiary|consulted");
});

test("producer role values survive register name resolution", () => {
  const c = spreadsheetContract([...base, "cedar_uid", "canonical_name", "entity_class", "cedar_entity_role"]);
  const register = { byUid: new Map([["CE-AAA00-AA", { name: "Governed name", type: "Governed class", withheld: false }]]) };
  const e = rowEntity({ cedar_uid: "CE-AAA00-AA", canonical_name: "Original", cedar_entity_role: "certifying_authority" }, c, register);
  assert.equal(e.name, "Governed name");
  assert.equal(e.role, "certifying_authority");
  assert.equal(entityVectors(e, c).roles, "certifying_authority");
});

test("plural withheld names are masked at their source positions without altering identifiers", () => {
  const c = spreadsheetContract([...base, "cedar_uids", "canonical_names", "entity_classes", "entity_roles"]);
  const row = { cedar_uids: '["CE-AAA00-AA","CE-BBB00-BB"]', canonical_names: '["Allowed","Secret"]', entity_roles: '["recipient","recipient"]' };
  const register = { byUid: new Map([["CE-BBB00-BB", { name: null, type: "Individually Native-owned business", withheld: true }]]) };
  const masked = publicRow(row, c, rowEntity(row, c, register));
  assert.deepEqual(JSON.parse(masked.canonical_names), ["Allowed", "[name withheld]"]);
  assert.equal(masked.cedar_uids, row.cedar_uids);
  assert.equal(row.canonical_names, '["Allowed","Secret"]');
});

test("mixed record types cannot collide when their original key tuples match", () => {
  const c = spreadsheetContract(base);
  const rows = [{ record_type: "actions", record_key: '["1"]', record_grain: "One action" }, { record_type: "participants", record_key: '["1"]', record_grain: "One participant" }];
  const items = universalRows("federal-register/federal-register", rows, undefined, c);
  assert.notEqual(items[0].id, items[1].id);
  assert.deepEqual(items.map(i => i.recordId), ['["1"]', '["1"]']);
});

test("reported lobbying and subaward measures retain their own value and time basis", () => {
  const lobbying = spreadsheetContract([...base, "reported_amount_usd", "income_usd", "expenses_usd", "amount_basis", "reporting_year"]);
  assert.equal(lobbying.amount, "reported_amount_usd");
  assert.equal(lobbying.amount_basis, "amount_basis");
  assert.equal(lobbying.year, "reporting_year");
  const sub = spreadsheetContract([...base, "subaward_amount_usd", "prime_award_amount_usd", "subcontractor_name"]);
  assert.equal(sub.amount, "subaward_amount_usd");
  assert.equal(sub.subject, "subcontractor_name");
  const resources = spreadsheetContract([...base, "amount_usd", "measurement_status", "period_start"]);
  assert.equal(resources.amount_basis, "measurement_status");
  assert.equal(resources.date, "period_start");
  const need = spreadsheetContract([...base, "reviewed_on", "source_release_id", "ownership_percent"]);
  assert.equal(need.date, null);
  assert.equal(need.amount, null);
});

test("subaward party associations remain independently filterable without asserting ownership", () => {
  const c = spreadsheetContract([...base, "cedar_uid", "canonical_name", "entity_class", "cedar_entity_role", "sub_cedar_uid", "prime_cedar_uid"]);
  const entities = rowEntities({ cedar_uid: "CE-AAA00-AA", canonical_name: "First", cedar_entity_role: "source-based affiliation", sub_cedar_uid: "CE-AAA00-AA", prime_cedar_uid: "CE-BBB00-BB" }, c);
  assert.equal(entities.length, 2);
  assert.equal(entities[1].role, "prime-contractor-side Native attribution");
  assert.deepEqual(entities[0].roles, ["subcontractor-side Native attribution"]);
  assert.doesNotMatch(entityVectors({ entities }, c).roles, /owner/i);
});

test("resource reporting periods do not become missing or invented payment dates", () => {
  const c = spreadsheetContract([...base, "payment_date", "period_start", "period_end", "period_type", "measurement_status"]);
  const row = { payment_date: "", period_start: "2022-01-01", period_end: "2022-12-31", period_type: "calendar_year" };
  assert.equal(rowDate(row, c), "2022-01-01");
  assert.equal(rowYear(row, c), 2022);
  assert.match(c.year_basis, /reported period/);
  assert.equal(rowDate({ ...row, period_start: "", payment_date: "2023-03-04" }, c), null);
});

test("reviewed NEED defaults display qualified owner facts without inventing an entity link", () => {
  const c = spreadsheetContract([...base, "enterprise_name", "owner_name", "ownership_extent", "relationship_type", "uei", "cage_code", "evidence_pins"]);
  assert.deepEqual(c.default_columns, ["enterprise_name", "owner_name", "relationship_type", "ownership_extent", "uei", "cage_code", "record_grain"]);
  assert.equal(c.entity_uid, null);
  assert.equal(c.entity_name, null);
  assert.ok(c.observation.includes("ownership_extent"));
});

test("mixed Federal Register sources and dates follow their own component only", () => {
  const columns = [...base, "consultation_participants__source_url", "federal_actions__source_url", "notice_date", "publication_date", "html_url"];
  const c = spreadsheetContract(columns);
  const row = {
    record_type: "consultation_participants",
    consultation_participants__source_url: "https://agency.example/consultation",
    federal_actions__source_url: "https://register.example/action",
    html_url: "https://register.example/html",
    notice_date: "2024-02-03", publication_date: "2019-06-10",
  };
  assert.equal(rowSource(row, c), "https://agency.example/consultation");
  assert.equal(rowDate(row, c), "2024-02-03");
  assert.equal(rowYear(row, c), 2024);
  assert.equal(rowSource({ ...row, consultation_participants__source_url: "" }, c), null);
  assert.equal(rowSource({ ...row, record_type: "federal_actions" }, c), "https://register.example/action");
  assert.equal(rowDate({ ...row, record_type: "federal_actions" }, c), "2019-06-10");
  assert.equal(rowYear({ ...row, record_type: "federal_actions" }, c), 2019);
  assert.equal(rowSource({ ...row, record_type: "federal_actions", federal_actions__source_url: "not a URL" }, c), row.html_url);
  assert.equal(rowSource({ ...row, record_type: "unknown" }, c), null);
  assert.equal(rowDate({ ...row, record_type: "unknown" }, c), null);
  const plan = columnPlan("federal-register/federal-register", c, columns);
  assert.ok(plan.defaults.includes(SOURCE_LINK_COLUMN));
  assert.ok(plan.all.includes(SOURCE_LINK_COLUMN));
});
