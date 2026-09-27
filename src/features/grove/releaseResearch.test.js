import test from "node:test";
import assert from "node:assert/strict";
import { researchComponents, researchFields, researchValue } from "./releaseResearch.js";

test("component and native requests preserve exact pins without treating a held count as available", () => {
  const pin = "a".repeat(64);
  assert.equal(researchComponents({ release: { kind: "full", table_id: "prime_contracts", release_id: pin, record_count: 20 } })[0].component, null);
  const parts = researchComponents({ release: [
    { kind: "full", component: "facts", release_id: pin, record_count: 20 },
    { kind: "full", table_id: "holds", status: "unavailable", record_count: 999 },
  ] });
  assert.equal(parts[0].component, "facts");
  assert.equal(parts[1].available, false);
});

test("both maintained internal display dispositions remain hidden", () => {
  const names = ["show", "internal", "remove", "keep_internal", "keep_internally"];
  const packet = { display_order: names, codebook: { fields: names.map((name) => ({
    name, display_disposition: name === "show" ? "keep" : name,
  })) } };
  assert.deepEqual(researchFields(packet).map((field) => field.name), ["show"]);
});

test("display labels and order do not rename exports or collapse money meanings", () => {
  const packet = { display_order: ["cedar_uid", "obligations", "ceiling", "secret"], codebook: { fields: [
    { name: "ceiling", label: "Award ceiling" }, { name: "cedar_uid", label: "Cedar entity ID" },
    { name: "obligations", label: "Transaction obligations" }, { name: "secret", display_disposition: "internal" },
  ] } };
  assert.deepEqual(researchFields(packet).map((field) => field.name), ["cedar_uid", "obligations", "ceiling"]);
  assert.equal(researchValue(null), "Not recorded");
  assert.equal(researchValue("9007199254740993.01"), "9007199254740993.01");
  assert.equal(researchValue(0), "0");
});
