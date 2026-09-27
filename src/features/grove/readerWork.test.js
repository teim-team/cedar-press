/**
 * "Your work": the landing audiences as the offered list, and every answer a
 * reader has already given kept exactly as they gave it.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  OFFERED_WORK_KINDS,
  WORK_KINDS,
  loadWork,
  normalizeWork,
  saveWork,
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

/**
 * Landing audience id to the work id a reader in that audience picks. The
 * landing ids are the band's own (`pressJobs.js` once it lands on this base,
 * `pressAudiences.js` and `pressAnnounced.js` before that); the work ids are
 * stored answers and never change.
 */
const LANDING_TO_WORK = Object.freeze({
  "tribal-nations": "tribal_government",
  "ancs-nhos": "anc_nho",
  "native-enterprises": "tribal_enterprise",
  "banks-lenders": "lender_investor",
  "native-nonprofits": "native_nonprofit",
  "foundations-philanthropy": "foundation",
  businesses: "business",
  "universities-researchers": "academic",
  journalists: "media",
  advisors: "advisor",
  "economic-development": "economic_development",
});

test("the offered list is the eleven landing audiences, in landing order", () => {
  assert.deepEqual(
    OFFERED_WORK_KINDS.map((kind) => kind.label),
    [
      "Tribal Nation or tribal government",
      "ANC or NHO",
      "Native enterprise",
      "Bank, lender or investor (CDFIs included)",
      "Native nonprofit",
      "Foundation or philanthropy",
      "Business working in Indian Country",
      "University or research institution",
      "Newsroom or journalist",
      "Advisor or professional services firm",
      "Economic development organization or outside partner",
    ],
  );
  assert.deepEqual(OFFERED_WORK_KINDS.map((kind) => kind.id), Object.values(LANDING_TO_WORK));
});

test("every legacy id is still known, and round-trips unchanged", () => {
  for (const id of Object.keys(LEGACY)) {
    assert.equal(normalizeWork(id), id, id);
    assert.ok(workLabel(id), `${id} has no label`);
  }
  assert.equal(normalizeWork("astronaut"), null);
  assert.equal(normalizeWork(undefined), null);
  assert.equal(normalizeWork(42), null);
  assert.equal(workLabel("astronaut"), null);
});

test("the two retired answers keep their original labels and are not remapped", () => {
  assert.equal(workLabel("federal"), LEGACY.federal);
  assert.equal(workLabel("state_local"), LEGACY.state_local);
  const retired = WORK_KINDS.filter((kind) => kind.retired).map((kind) => kind.id);
  assert.deepEqual(retired, ["federal", "state_local"]);
  for (const id of retired) {
    assert.ok(!OFFERED_WORK_KINDS.some((kind) => kind.id === id), `${id} is offered to new readers`);
  }
});

test("a retired answer appears in the select only for the reader who holds it", () => {
  assert.equal(workOptions(null), OFFERED_WORK_KINDS);
  assert.equal(workOptions("media"), OFFERED_WORK_KINDS);
  assert.equal(workOptions("astronaut"), OFFERED_WORK_KINDS);
  const federal = workOptions("federal");
  assert.equal(federal.length, OFFERED_WORK_KINDS.length + 1);
  assert.deepEqual(federal[0], { id: "federal", label: "Federal agency", retired: true });
  assert.ok(!federal.slice(1).some((kind) => kind.id === "state_local"));
  assert.equal(workOptions("state_local")[0].label, "State or local government");
});

test("every label follows the copy rules", () => {
  for (const { label } of WORK_KINDS) {
    assert.doesNotMatch(label, /&|—/, label);
    assert.equal(label[0], label[0].toUpperCase(), label);
  }
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
    for (const id of Object.keys(LEGACY)) {
      assert.equal(await saveWork(id), id);
      assert.equal(await loadWork(), id, id);
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
});

/** Import a sibling module that may not exist on this base yet; any other failure is real. */
async function optional(path) {
  try {
    return await import(path);
  } catch (error) {
    if (error?.code === "ERR_MODULE_NOT_FOUND" && String(error.message).includes(path.slice(2))) return null;
    throw error;
  }
}

/** The landing's audiences, in order, with announced ones back in their place. */
async function landingIds() {
  const jobs = await optional("./pressJobs.js");
  const audiences = jobs?.AUDIENCE_JOBS ?? (await import("./pressAudiences.js")).PRESS_AUDIENCES;
  const ids = audiences.map((audience) => audience.id);
  const announced = (await optional("./pressAnnounced.js"))?.ANNOUNCED_AUDIENCES ?? [];
  for (const { after, audience } of announced) {
    if (ids.includes(audience.id)) continue;
    const at = ids.indexOf(after);
    ids.splice(at < 0 ? ids.length : at + 1, 0, audience.id);
  }
  return { ids, fromJobs: Boolean(jobs) };
}

test("the offered list stays aligned with the landing page's audiences", async () => {
  const { ids, fromJobs } = await landingIds();
  for (const id of ids) {
    assert.ok(id in LANDING_TO_WORK, `landing audience ${id} has no "Your work" answer: add one`);
  }
  const mapped = ids.map((id) => LANDING_TO_WORK[id]);
  const offered = OFFERED_WORK_KINDS.map((kind) => kind.id);
  assert.deepEqual(offered.filter((id) => mapped.includes(id)), mapped, "same order as the landing");
  const missing = offered.filter((id) => !mapped.includes(id));
  if (fromJobs) {
    assert.deepEqual(missing, [], "every offered answer is a landing audience");
  } else {
    // Before `pressJobs.js` reaches this base, the band has no economic
    // development audience yet; it is the eleventh in that file.
    assert.deepEqual(missing, ["economic_development"]);
  }
});
