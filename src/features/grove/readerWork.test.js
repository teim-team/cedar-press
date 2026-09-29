/**
 * "Your work": the landing audiences as the offered list (same set, same
 * order, same labels), and every answer a reader has already given kept
 * exactly as they gave it.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { AUDIENCE_JOBS, visibleAudiences } from "./pressJobs.js";
import {
  OFFERED_WORK_KINDS,
  WORK_KINDS,
  loadWork,
  normalizeWork,
  saveWork,
  workAudience,
  workLabel,
  workOptions,
} from "./readerWork.js";

/** Every id a reader could have stored before 2026-09-26, with its label then. */
const LEGACY = Object.freeze({
  tribal_government: "Tribal government",
  tribal_enterprise: "Tribal enterprise or corporation",
  anc_nho: "ANC or NHO",
  native_nonprofit: "Native nonprofit or association",
  federal: "Federal agency",
  state_local: "State or local government",
  lender_investor: "Lender, investor or fund",
  advisor: "Law, accounting or consulting firm",
  media: "Newsroom or media",
  academic: "University or research institute",
});

/** The ids added since, which a reader may also hold. */
const CURRENT = Object.freeze(["foundation", "business", "economic_development", "government"]);

test("the offered list is the landing's audiences: same set, same order, same labels", () => {
  const landing = visibleAudiences().map((audience) => audience.audience);
  assert.deepEqual(OFFERED_WORK_KINDS.map((kind) => kind.label), landing);
  assert.equal(OFFERED_WORK_KINDS.length, landing.length, "one answer per landing audience");
  assert.equal(new Set(OFFERED_WORK_KINDS.map((kind) => kind.id)).size, OFFERED_WORK_KINDS.length, "ids are distinct");
});

test("every declared landing audience has a stored id, so none can go missing from Settings", () => {
  const known = WORK_KINDS.filter((kind) => !kind.retired);
  assert.deepEqual(known.map((kind) => kind.label), AUDIENCE_JOBS.map((audience) => audience.audience));
});

test("the renamed and the new audience keep the ids the owner named", () => {
  const byLabel = Object.fromEntries(OFFERED_WORK_KINDS.map((kind) => [kind.label, kind.id]));
  assert.equal(byLabel["Consultants and advisors"], "advisor");
  assert.equal(byLabel["Government and public agency officials"], "government");
  assert.equal(byLabel["Tribal Nations"], "tribal_government", "Tribal Nations stays its own answer");
});

test("every legacy and current id is still known, and normalizes to itself", () => {
  for (const id of [...Object.keys(LEGACY), ...CURRENT]) {
    assert.equal(normalizeWork(id), id, id);
    assert.ok(workLabel(id), `${id} has no label`);
  }
  assert.equal(normalizeWork("astronaut"), null);
  assert.equal(normalizeWork(undefined), null);
  assert.equal(normalizeWork(42), null);
  assert.equal(workLabel("astronaut"), null);
});

test("federal and state_local are preserved under the government audience, with their level", () => {
  assert.equal(workLabel("federal"), "Government and public agency officials (federal)");
  assert.equal(workLabel("state_local"), "Government and public agency officials (state or local)");
  const preserved = WORK_KINDS.filter((kind) => kind.retired).map((kind) => kind.id);
  assert.deepEqual(preserved, ["federal", "state_local"]);
  for (const id of preserved) {
    assert.ok(!OFFERED_WORK_KINDS.some((kind) => kind.id === id), `${id} is offered to new readers`);
    assert.doesNotMatch(workLabel(id), /economic development|outside partner/i, `${id} is not an outside partner`);
  }
});

test("workAudience groups the preserved answers with government, and changes nothing else", () => {
  for (const id of ["federal", "state_local", "government"]) assert.equal(workAudience(id), "government", id);
  for (const id of ["advisor", "media", "economic_development", "tribal_government"]) assert.equal(workAudience(id), id);
  assert.equal(workAudience("astronaut"), null);
  assert.equal(workAudience(null), null);
});

test("a preserved answer appears in the select only for the reader who holds it, under its audience", () => {
  assert.equal(workOptions(null), OFFERED_WORK_KINDS);
  assert.equal(workOptions("media"), OFFERED_WORK_KINDS);
  assert.equal(workOptions("government"), OFFERED_WORK_KINDS);
  assert.equal(workOptions("astronaut"), OFFERED_WORK_KINDS);
  for (const id of ["federal", "state_local"]) {
    const options = workOptions(id).map((kind) => kind.id);
    assert.equal(options.length, OFFERED_WORK_KINDS.length + 1, id);
    assert.equal(options[options.indexOf("government") + 1], id, `${id} sits under the government audience`);
    const other = id === "federal" ? "state_local" : "federal";
    assert.ok(!options.includes(other), `${other} is shown to a reader who does not hold it`);
  }
});

test("every label follows the copy rules", () => {
  for (const { label } of WORK_KINDS) {
    assert.doesNotMatch(label, /&|—/, label);
    assert.equal(label[0], label[0].toUpperCase(), label);
  }
  assert.ok(!WORK_KINDS.some((kind) => /professional services/i.test(kind.label)), "the old advisor label is gone");
});

test("standalone mode stores and reads back every legacy id verbatim", async () => {
  const store = new Map();
  const previous = globalThis.localStorage;
  globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  };
  try {
    for (const id of [...Object.keys(LEGACY), ...CURRENT]) {
      assert.equal(await saveWork(id), id);
      assert.equal(store.get("cedar-press-work"), id, `${id} is stored as given`);
      assert.equal(await loadWork(), id, id);
    }
    // Written before this build, read by it: never rewritten on read.
    for (const id of ["federal", "state_local"]) {
      store.set("cedar-press-work", id);
      assert.equal(await loadWork(), id);
      assert.equal(store.get("cedar-press-work"), id);
    }
    assert.equal(await saveWork(""), null);
    assert.equal(await loadWork(), null);
  } finally {
    globalThis.localStorage = previous;
  }
});

test("the service accepts exactly the ids this module knows", () => {
  const dumped = JSON.parse(
    readFileSync(new URL("../../../server/cedar_press/_press_data.json", import.meta.url), "utf8"),
  ).workKinds;
  assert.deepEqual(dumped, JSON.parse(JSON.stringify(WORK_KINDS)), "regenerate with scripts/dump-press.mjs");
  for (const id of Object.keys(LEGACY)) assert.ok(dumped.some((kind) => kind.id === id), `the service would refuse ${id}`);
});
