import test from "node:test";
import assert from "node:assert/strict";
import { spreadsheetContract } from "../../../scripts/derive-explore.mjs";
import { observationOf } from "./explore.js";

const columns = ["record_type", "record_key", "record_grain", "enterprise_name",
  "owner_name", "related_entity_name", "ownership_extent", "relationship_type",
  "uei", "cage_code", "evidence_pins"];
const contract = spreadsheetContract(columns);
const base = Object.freeze({
  record_type: "reviewed_public_base", record_key: '["synthetic-enterprise"]',
  record_grain: "One reviewed enterprise observation", enterprise_name: "Synthetic enterprise",
  owner_name: "", related_entity_name: "", ownership_extent: "", relationship_type: "",
  uei: "SYNTHETIC001", cage_code: "SYN01", evidence_pins: "[]",
});

test("an identity-only NEED observation names its published identifiers without inventing ownership", () => {
  const before = JSON.stringify(base);
  assert.equal(observationOf(base, contract, "need"), "UEI: SYNTHETIC001 · CAGE: SYN01");
  assert.equal(JSON.stringify(base), before);
  assert.doesNotMatch(observationOf(base, contract, "need"), /own|affiliat/i);
});

test("an affiliation observation uses the reviewed counterpart without calling it an owner", () => {
  const row = { ...base, related_entity_name: "Synthetic alliance", relationship_type: "affiliated_with" };
  const value = observationOf(row, contract, "need");
  assert.match(value, /Synthetic alliance/);
  assert.match(value, /Affiliated with/);
  assert.doesNotMatch(value, /owned|owner/i);
});

test("a wholly-owned NEED observation does not repeat an identical related-entity name", () => {
  const row = { ...base, owner_name: "Synthetic owner", related_entity_name: "Synthetic owner",
    relationship_type: "owned_by", ownership_extent: "wholly_owned", owner_scope: "immediate" };
  assert.equal(observationOf(row, contract, "need"), "Wholly owned by Synthetic owner (immediate owner)");
});

test("a NEED name-only observation describes exactly the published name", () => {
  assert.equal(observationOf({ ...base, uei: "", cage_code: "" }, contract, "need"),
    "Enterprise name: Synthetic enterprise");
});

test("NEED fallback does not change other collections or add an unreported relationship", () => {
  const row = { ...base, uei: "", cage_code: "", enterprise_name: "" };
  assert.equal(observationOf(row, contract, "need"), "");
  assert.equal(observationOf(base, contract, "owned"), "");
});
