// The method sections carry claims about the product and a policy that
// decides who gets a tribe's records, so the things that would be quietly
// wrong if a list were edited are pinned here rather than only proofread.

import assert from "node:assert/strict";
import test from "node:test";

import {
  CONSTRUCTION_STEPS,
  DISCOVERY_MOVES,
  ECOSYSTEM_EXAMPLES,
  EXPERTISE_DOMAINS,
  EXPERTISE_STRIP,
  MAINTENANCE_TRACKED,
  REPLICATION_CALLOUTS,
  SOURCE_KINDS,
  TRIBAL_REQUEST,
  expertiseSentence,
} from "./pressMethod.js";

const ALL_STRINGS = [
  ...EXPERTISE_DOMAINS,
  ...EXPERTISE_STRIP.map((d) => d.label),
  ...SOURCE_KINDS,
  ...CONSTRUCTION_STEPS.flatMap((s) => [s.label, s.note]),
  ...DISCOVERY_MOVES,
  ...MAINTENANCE_TRACKED,
  ...ECOSYSTEM_EXAMPLES,
  ...REPLICATION_CALLOUTS,
  TRIBAL_REQUEST.policy,
  ...TRIBAL_REQUEST.eligibility,
  ...TRIBAL_REQUEST.verification,
  ...TRIBAL_REQUEST.included,
  ...TRIBAL_REQUEST.excluded,
  ...TRIBAL_REQUEST.purposes,
  ...TRIBAL_REQUEST.steps.flatMap((s) => [s.step, s.body]),
];

// The brand lock in CLAUDE.md, applied to displayed copy.
test("no em dashes anywhere in the method copy", () => {
  for (const line of ALL_STRINGS) {
    assert.ok(!line.includes("—"), line);
  }
});

test("no antithesis constructions in the method copy", () => {
  // "not X, it is Y" and "not X but Y" used as a rhetorical beat.
  const beats = [/\bis not\b[^.]*\.\s*(It|That)\s+is\b/i, /\bnot\b[^.,]{1,60},\s*(it'?s|it is)\b/i];
  for (const line of ALL_STRINGS) {
    for (const beat of beats) {
      assert.ok(!beat.test(line), line);
    }
  }
});

test("the pipeline starts at discovery and ends at maintenance", () => {
  assert.equal(CONSTRUCTION_STEPS[0].id, "discover");
  assert.equal(CONSTRUCTION_STEPS.at(-1).id, "maintain");
  assert.equal(new Set(CONSTRUCTION_STEPS.map((s) => s.id)).size, CONSTRUCTION_STEPS.length);
  for (const step of CONSTRUCTION_STEPS) assert.ok(step.label && step.note, step.id);
});

// The strip is a summary of the domain list, so it must not claim expertise
// the list does not name, and it must not quietly drop a domain either.
test("every strip icon covers domains the long list actually names", () => {
  for (const domain of EXPERTISE_STRIP) {
    assert.ok(domain.covers.length > 0, domain.label);
    for (const covered of domain.covers) {
      assert.ok(EXPERTISE_DOMAINS.includes(covered), `${domain.label}: ${covered}`);
    }
  }
});

test("every domain is covered by one of the strip icons", () => {
  const covered = new Set(EXPERTISE_STRIP.flatMap((domain) => domain.covers));
  for (const domain of EXPERTISE_DOMAINS) {
    assert.ok(covered.has(domain), domain);
  }
});

// The Methods page names the domains in one sentence, read from the strip.
// The sentence used to be typed into the page and named gaming for a week
// after the shelf stopped selling it.
test("the expertise sentence names every strip label and nothing else", () => {
  const sentence = expertiseSentence();
  for (const [index, domain] of EXPERTISE_STRIP.entries()) {
    const expected = index === 0 ? domain.label : domain.label[0].toLowerCase() + domain.label.slice(1);
    assert.ok(sentence.includes(expected), `${domain.label} is not in "${sentence}"`);
  }
  assert.match(sentence, / and [^,]+$/);
  assert.doesNotMatch(sentence, /gaming/i);
});

// The scope split is the part of the policy that stops one tribe's package
// from carrying another tribe's records, so it must not overlap.
test("the tribal request scope does not both include and exclude anything", () => {
  const included = new Set(TRIBAL_REQUEST.included.map((s) => s.toLowerCase()));
  for (const excluded of TRIBAL_REQUEST.excluded) {
    assert.ok(!included.has(excluded.toLowerCase()), excluded);
  }
});

test("the tribal request policy withholds other tribes and the entity graph", () => {
  const excluded = TRIBAL_REQUEST.excluded.join(" ").toLowerCase();
  assert.match(excluded, /other tribes/);
  assert.match(excluded, /entity graph/);
  assert.match(excluded, /crosswalk/);
});

// The whole point of the rewrite: claimed affiliation is not sufficient.
test("the policy requires the tribal government, not a claim of affiliation", () => {
  const policy = TRIBAL_REQUEST.policy.toLowerCase();
  assert.match(policy, /will not release/);
  assert.match(policy, /claims affiliation/);
  assert.match(policy, /federally recognized tribal government/);
  assert.match(policy, /independently verify/);
});

test("verification can reach the tribal government directly", () => {
  const verification = TRIBAL_REQUEST.verification.join(" ").toLowerCase();
  assert.match(verification, /official tribal government email/);
  assert.match(verification, /signed authorization letter/);
});

// The request policy names what a package covers, and it may only name what
// the storefront publishes: a promise about records the product does not yet
// carry is one the desk cannot keep on the day a request arrives.
test("the request policy covers nothing the storefront does not sell", () => {
  const included = TRIBAL_REQUEST.included.join(" ").toLowerCase();
  assert.doesNotMatch(included, /gaming/);
  assert.equal(TRIBAL_REQUEST.steps.length, 5);
  assert.equal(TRIBAL_REQUEST.steps[0].step, "Request");
  assert.equal(TRIBAL_REQUEST.steps.at(-1).step, "Correct");
});

// ── The maintenance story and Cedar NEED's enrichments (owner, 2026-09-27) ─

import { MAINTENANCE, NEED_ENRICHMENTS } from "./pressMethod.js";
import { STOREFRONT_CATALOG } from "./pressCatalog.js";
import { DECLARED_CADENCE } from "./pressReleases.js";

test("the maintenance story says weekly, human review, wider coverage and new collections", () => {
  assert.match(MAINTENANCE.sentence, /weekly with human review/);
  assert.match(MAINTENANCE.sentence, /expands their source coverage and useful fields over time/);
  assert.match(MAINTENANCE.sentence, /develops new collections/);
  assert.match(MAINTENANCE.goal, /exceptionally useful, well-documented data and tools for Indian Country/);
  for (const line of Object.values(MAINTENANCE)) {
    assert.doesNotMatch(line, /[—&]|\bimpact\b/i, line);
  }
  // No surface promises a different cadence.
  for (const [id, cadence] of Object.entries(DECLARED_CADENCE)) assert.equal(cadence, "Updated weekly", id);
});

test("public NEED describes its reviewed cohort while restricted enrichments retain their subject and date", () => {
  assert.equal(STOREFRONT_CATALOG.length, 14);
  assert.ok(!STOREFRONT_CATALOG.some((entry) => /patent|rating/i.test(`${entry.id} ${entry.name}`)), "no standalone collection");
  const need = STOREFRONT_CATALOG.find((entry) => entry.id === "need");
  // Owner, 2026-10-06: the paragraph says what NEED stands for and carries no
  // draft wording; it still never claims the register is complete.
  assert.match(need.blurb, /Native Entity Enterprise Dataset \(NEED\)/);
  assert.doesNotMatch(need.blurb, /under review|cohort|preview|pending/i);
  assert.doesNotMatch(need.blurb, /complete enterprise register|all enterprises verified/i);
  const plot = STOREFRONT_CATALOG.find((entry) => entry.id === "plot");
  assert.match(plot.blurb, /PLOT \(Parcel-Level Ownership and Transfers\)/);
  const all = Object.values(NEED_ENRICHMENTS).join(" ");
  assert.match(all, /where records are available/i);
  assert.match(all, /acquired patent is shown as acquired rather than as the entity's own invention/);
  assert.match(all, /issuer, instrument, agency and date/);
  assert.match(all, /rather than as a current rating/);
  assert.match(all, /never presented as its parent's/);
  assert.doesNotMatch(`${all} ${need.blurb}`, /[—&]|\bimpact\b/i);
});
