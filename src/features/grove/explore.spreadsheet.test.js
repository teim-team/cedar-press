import assert from "node:assert/strict";
import test from "node:test";
import { customerTableContract } from "../../../scripts/derive-explore.mjs";
import { observationOf, rowDate, rowYear, rowEntities, rowEntity, entityVectors, publicRow } from "./explore.js";
import { loadCodebook } from "./codebook.js";
// The codebook loads on demand in the browser (codebook.js); the readers
// under test read it synchronously once it has.
await loadCodebook();

// The reader rules every customer table shares, on synthetic columns:
// entity roles, withheld names, amounts and time bases.

test("unattributed resource revenue keeps its own description without inventing a recipient", () => {
  const columns = ["canonical_name", "cedar_uid", "commodity", "resource_type", "revenue_type"];
  const contract = customerTableContract(columns);
  const row = { commodity: "Other royalties", resource_type: "mixed", revenue_type: "royalty", canonical_name: "", cedar_uid: "" };
  assert.match(observationOf(row, contract), /Other royalties/);
  assert.deepEqual(rowEntities(row, contract), []);
});

test("reviewed NEED business and owner names never manufacture a CE association", () => {
  const c = customerTableContract(["enterprise_id", "enterprise_name", "owner_name", "uei", "cage_code", "evidence_pins"]);
  const row = { enterprise_id: "CEDAR-NEST-1", enterprise_name: "Example Company", owner_name: "Example Owner", uei: "ABC123DEF456" };
  assert.equal(c.entity_uid, null);
  assert.equal(c.entity_name, null);
  assert.equal(c.subject, "enterprise_name");
  assert.deepEqual(rowEntities(row, c), []);
});

test("plural entities retain each source role despite blank or repeated IDs", () => {
  const c = customerTableContract(["cedar_uids", "canonical_names", "entity_classes", "entity_roles"]);
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

test("role values survive register name resolution", () => {
  const c = customerTableContract(["cedar_uid", "canonical_name", "entity_class", "cedar_entity_role"]);
  const register = { byUid: new Map([["CE-AAA00-AA", { name: "Governed name", type: "Governed class", withheld: false }]]) };
  const e = rowEntity({ cedar_uid: "CE-AAA00-AA", canonical_name: "Original", cedar_entity_role: "certifying_authority" }, c, register);
  assert.equal(e.name, "Governed name");
  assert.equal(e.role, "certifying_authority");
  assert.equal(entityVectors(e, c).roles, "certifying_authority");
});

test("plural withheld names are masked at their source positions without altering identifiers", () => {
  const c = customerTableContract(["cedar_uids", "canonical_names", "entity_classes", "entity_roles"]);
  const row = { cedar_uids: '["CE-AAA00-AA","CE-BBB00-BB"]', canonical_names: '["Allowed","Secret"]', entity_roles: '["recipient","recipient"]' };
  const register = { byUid: new Map([["CE-BBB00-BB", { name: null, type: "Individually Native-owned business", withheld: true }]]) };
  const masked = publicRow(row, c, rowEntity(row, c, register));
  assert.deepEqual(JSON.parse(masked.canonical_names), ["Allowed", "[name withheld]"]);
  assert.equal(masked.cedar_uids, row.cedar_uids);
  assert.equal(row.canonical_names, '["Allowed","Secret"]');
});

test("reported lobbying and subaward measures retain their own value and time basis", () => {
  const lobbying = customerTableContract(["reported_amount_usd", "income_usd", "expenses_usd", "amount_basis", "reporting_year"]);
  assert.equal(lobbying.amount, "reported_amount_usd");
  assert.equal(lobbying.amount_basis, "amount_basis");
  assert.equal(lobbying.year, "reporting_year");
  const sub = customerTableContract(["subaward_amount_usd", "prime_award_amount_usd", "subcontractor_name"]);
  assert.equal(sub.amount, "subaward_amount_usd");
  assert.equal(sub.subject, "subcontractor_name");
  const resources = customerTableContract(["amount_usd", "measurement_status", "period_start"]);
  assert.equal(resources.amount_basis, "measurement_status");
  assert.equal(resources.date, "period_start");
  const need = customerTableContract(["reviewed_on", "source_release_id", "ownership_percent"]);
  assert.equal(need.date, null);
  assert.equal(need.amount, null);
});

test("subaward party associations remain independently filterable without asserting ownership", () => {
  const c = customerTableContract(["cedar_uid", "canonical_name", "entity_class", "cedar_entity_role", "sub_cedar_uid", "prime_cedar_uid"]);
  const entities = rowEntities({ cedar_uid: "CE-AAA00-AA", canonical_name: "First", cedar_entity_role: "source-based affiliation", sub_cedar_uid: "CE-AAA00-AA", prime_cedar_uid: "CE-BBB00-BB" }, c);
  assert.equal(entities.length, 2);
  assert.equal(entities[1].role, "prime-contractor-side Native attribution");
  assert.deepEqual(entities[0].roles, ["subcontractor-side Native attribution"]);
  assert.doesNotMatch(entityVectors({ entities }, c).roles, /owner/i);
});

test("resource reporting periods do not become missing or invented payment dates", () => {
  const c = customerTableContract(["payment_date", "period_start", "period_end", "period_type", "measurement_status"]);
  const row = { payment_date: "", period_start: "2022-01-01", period_end: "2022-12-31", period_type: "calendar_year" };
  assert.equal(rowDate(row, c), "2022-01-01");
  assert.equal(rowYear(row, c), 2022);
  assert.equal(c.year_basis, "calendar year in which the reported period starts");
  assert.equal(rowDate({ ...row, period_start: "", payment_date: "2023-03-04" }, c), null);
});
